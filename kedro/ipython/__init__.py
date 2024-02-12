"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
from __future__ import annotations

import inspect
import logging
import os
import sys
import typing
import warnings
from pathlib import Path
from typing import Any, Callable

import IPython
from IPython.core.magic import needs_local_scope, register_line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring
from rich.console import Console
from rich.syntax import Syntax

from kedro.framework.cli import load_entry_points
from kedro.framework.cli.project import CONF_SOURCE_HELP, PARAMS_ARG_HELP
from kedro.framework.cli.utils import ENV_HELP, _split_params
from kedro.framework.project import (
    LOGGING,  # noqa: F401
    _ProjectPipelines,
    configure_project,
    pipelines,
)
from kedro.framework.session import KedroSession
from kedro.framework.startup import _is_project, bootstrap_project
from kedro.pipeline.node import Node
from kedro.utils import _is_databricks

logger = logging.getLogger(__name__)


def load_ipython_extension(ipython: Any) -> None:
    """
    Main entry point when %load_ext kedro.ipython is executed, either manually or
    automatically through `kedro ipython` or `kedro jupyter lab/notebook`.
    IPython will look for this function specifically.
    See https://ipython.readthedocs.io/en/stable/config/extensions/index.html
    """
    ipython.register_magic_function(magic_reload_kedro, magic_name="reload_kedro")
    logger.info("Registered line magic 'reload_kedro'")
    ipython.register_magic_function(magic_load_node, magic_name="load_node")
    logger.info("Registered line magic 'load_node'")

    if _find_kedro_project(Path.cwd()) is None:
        logger.warning(
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        return

    reload_kedro()


@typing.no_type_check
@needs_local_scope
@magic_arguments()
@argument(
    "path",
    type=str,
    help=(
        "Path to the project root directory. If not given, use the previously set"
        "project root."
    ),
    nargs="?",
    default=None,
)
@argument("-e", "--env", type=str, default=None, help=ENV_HELP)
@argument(
    "--params",
    type=lambda value: _split_params(None, None, value),
    default=None,
    help=PARAMS_ARG_HELP,
)
@argument("--conf-source", type=str, default=None, help=CONF_SOURCE_HELP)
def magic_reload_kedro(
    line: str,
    local_ns: dict[str, Any] | None = None,
    conf_source: str | None = None,
) -> None:
    """
    The `%reload_kedro` IPython line magic.
    See https://kedro.readthedocs.io/en/stable/notebooks_and_ipython/kedro_and_notebooks.html#reload-kedro-line-magic
    for more.
    """
    args = parse_argstring(magic_reload_kedro, line)
    reload_kedro(args.path, args.env, args.params, local_ns, args.conf_source)


def reload_kedro(
    path: str | None = None,
    env: str | None = None,
    extra_params: dict[str, Any] | None = None,
    local_namespace: dict[str, Any] | None = None,
    conf_source: str | None = None,
) -> None:  # pragma: no cover
    """Function that underlies the %reload_kedro Line magic. This should not be imported
    or run directly but instead invoked through %reload_kedro."""

    project_path = _resolve_project_path(path, local_namespace)

    metadata = bootstrap_project(project_path)
    _remove_cached_modules(metadata.package_name)
    configure_project(metadata.package_name)

    session = KedroSession.create(
        project_path,
        env=env,
        extra_params=extra_params,
        conf_source=conf_source,
    )
    context = session.load_context()
    catalog = context.catalog

    IPython.get_ipython().push(  # type: ignore[attr-defined, no-untyped-call]
        variables={
            "context": context,
            "catalog": catalog,
            "session": session,
            "pipelines": pipelines,
        }
    )

    logger.info("Kedro project %s", str(metadata.project_name))
    logger.info(
        "Defined global variable 'context', 'session', 'catalog' and 'pipelines'"
    )

    for line_magic in load_entry_points("line_magic"):
        register_line_magic(needs_local_scope(line_magic))  # type: ignore[no-untyped-call]
        logger.info("Registered line magic '%s'", line_magic.__name__)  # type: ignore[attr-defined]


def _resolve_project_path(
    path: str | None = None, local_namespace: dict[str, Any] | None = None
) -> Path:
    """
    Resolve the project path to use with reload_kedro, updating or adding it
    (in-place) to the local ipython Namespace (``local_namespace``) if necessary.

    Arguments:
        path: the path to use as a string object
        local_namespace: Namespace with local variables of the scope where the line
            magic is invoked in a dict.
    """
    if path:
        project_path = Path(path).expanduser().resolve()
    else:
        if local_namespace and "context" in local_namespace:
            project_path = local_namespace["context"].project_path
        else:
            project_path = _find_kedro_project(Path.cwd())
        if project_path:
            logger.info(
                "Resolved project path as: %s.\nTo set a different path, run "
                "'%%reload_kedro <project_root>'",
                project_path,
            )

    if (
        project_path
        and local_namespace
        and "context" in local_namespace
        and project_path != local_namespace["context"].project_path
    ):
        logger.info("Updating path to Kedro project: %s...", project_path)

    return project_path


def _remove_cached_modules(package_name: str) -> None:  # pragma: no cover
    to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
    # `del` is used instead of `reload()` because: If the new version of a module does not
    # define a name that was defined by the old version, the old definition remains.
    for module in to_remove:
        del sys.modules[module]


def _find_kedro_project(current_dir: Path) -> Any:  # pragma: no cover
    while current_dir != current_dir.parent:
        if _is_project(current_dir):
            return current_dir
        current_dir = current_dir.parent

    return None


def _guess_run_environment() -> str:
    """Best effort to guess the IPython/Jupyter environment"""
    # https://github.com/microsoft/vscode-jupyter/issues/7380
    if os.environ.get("VSCODE_PID"):
        return "vscode"
    elif _is_databricks():
        return "databricks"
    elif hasattr(IPython.get_ipython(), "kernel"):
        # IPython terminal does not have this attribute
        return "jupyter"
    else:
        return "ipython"


@typing.no_type_check
@magic_arguments()
@argument(
    "node",
    type=str,
    help=("Name of the Node."),
    nargs="?",
    default=None,
)
@argument("-p", "--print", help="Prints the content of the Node", action="store_true")
@argument(
    # "-p", cannot use -p unless we remove print
    "--platform",
    help="The running platforms, it can be one of ('jupyter','vscode','ipython','databricks')",
    default=None,
)
def magic_load_node(args: str) -> None:
    """The line magic %load_node <node_name>
    Currently it only supports Jupyter Notebook (>7.0) and Jupyter Lab. This line magic
    will generate code in multiple cells to load datasets from `DataCatalog`, import
    relevant functions and modules, node function definition and a function call.
    """

    def _create_cell_with_text(text: str, is_jupyter=True) -> None:
        if is_jupyter:
            from ipylab import JupyterFrontEnd

            app = JupyterFrontEnd()
            # Noted this only works with Notebook >7.0 or Jupyter Lab. It doesn't work with
            # VS Code Notebook due to imcompatible backends.
            app.commands.execute("notebook:insert-cell-below")
            app.commands.execute("notebook:replace-selection", {"text": text})
        else:
            IPython.get_ipython().set_next_input(text)

    def _print_cells(cell):
        for cell in cells:
            Console().print("")
            IPython.get_ipython().set_next_input(
                Console().print(
                    Syntax(cell, "python", theme="monokai", line_numbers=True)
                )
            )

    parameters = parse_argstring(magic_load_node, args)
    cells = _load_node(parameters.node, pipelines)

    run_environment = (
        _guess_run_environment() if not parameters.platform else parameters.platform
    )

    if run_environment == "jupyter":
        # Only create cells if it is jupyter
        for cell in cells:
            _create_cell_with_text(cell, is_jupyter=True)
    elif run_environment in ("ipython", "vscode"):
        # Combine multiple cells into one
        combined_cell = "\n\n".join(cells)
        _create_cell_with_text(combined_cell, is_jupyter=False)
    else:
        _print_cells(cells)

    # TODO: Should we remove this?
    if parameters.print:
        _print_cells(cells)


def _load_node(node_name: str, pipelines: _ProjectPipelines) -> list[str]:
    """Prepare the code to load dataset from catalog, import statements and function body.

    Args:
        node_name (str): The name of the node.

    Returns:
        list[str]: A list of string which is the generated code, each string represent a
        notebook cell.
    """
    warnings.warn(
        "This is an experimental feature, only Jupyter Notebook (>7.0) & Jupyter Lab "
        "are supported. If you encounter unexpected behaviour or would like to suggest "
        "feature enhancements, add it under this github issue https://github.com/kedro-org/kedro/issues/3580"
    )
    node = _find_node(node_name, pipelines)
    node_func = node.func

    node_inputs = _prepare_node_inputs(node)
    imports = _prepare_imports(node_func)
    function_definition = _prepare_function_body(node_func)
    function_call = _prepare_function_call(node_func)

    cells: list[str] = []
    cells.append(node_inputs)
    cells.append(imports)
    cells.append(function_definition)
    cells.append(function_call)
    return cells


def _find_node(node_name: str, pipelines: _ProjectPipelines) -> Node:
    for pipeline in pipelines.values():
        try:
            found_node: Node = pipeline.filter(node_names=[node_name]).nodes[0]
            return found_node
        except ValueError:
            continue
    # If reached the node was not found in the project
    raise ValueError(
        f"Node with name='{node_name}' not found in any pipelines. Remember to specify the node name, not the node function."
    )


def _prepare_imports(node_func: Callable) -> str:
    """Prepare the import statements for loading a node."""
    python_file = inspect.getsourcefile(node_func)
    logger.info(f"Loading node definition from {python_file}")

    # Confirm source file was found
    if python_file:
        import_statement = []
        with open(python_file) as file:
            # Parse any line start with from or import statement
            for line in file.readlines():
                if line.startswith("from") or line.startswith("import"):
                    import_statement.append(line.strip())

        clean_imports = "\n".join(import_statement).strip()
        return clean_imports
    else:
        raise FileNotFoundError(f"Could not find {node_func.__name__}")


def _prepare_node_inputs(node: Node) -> str:
    node_func = node.func
    signature = inspect.signature(node_func)

    node_inputs = node.inputs
    func_params = list(signature.parameters)

    statements = [
        "# Prepare necessary inputs for debugging",
        "# All debugging inputs must be defined in your project catalog",
    ]

    for node_input, func_param in zip(node_inputs, func_params):
        statements.append(f'{func_param} = catalog.load("{node_input}")')

    input_statements = "\n".join(statements)
    return input_statements


def _prepare_function_body(func: Callable) -> str:
    source_lines, _ = inspect.getsourcelines(func)
    body = "".join(source_lines)
    return body


def _prepare_function_call(node_func: Callable) -> str:
    """Prepare the text for the function call."""
    func_name = node_func.__name__
    signature = inspect.signature(node_func)
    func_params = list(signature.parameters)

    # Construct the statement of func_name(a=1,b=2,c=3)
    func_args = ", ".join(func_params)
    body = f"""{func_name}({func_args})"""
    return body
