"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
from __future__ import annotations

import inspect
import logging
import sys
import typing
from itertools import dropwhile
from pathlib import Path
from typing import Any, Callable

import IPython
from IPython.core.magic import needs_local_scope, register_line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

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


@typing.no_type_check
@magic_arguments()
@argument(
    "node",
    type=str,
    help=("Name of the Node."),
    nargs="?",
    default=None,
)
def magic_load_node(node: str) -> None:
    """The line magic %load_node <node_name>
    Currently it only support Jupyter Notebook (>7.0) and Jupyter Lab. This line magic
    will generate code in multiple cells to load dataest from Data Catalog, import
    relevant functions and modules, and the function body.
    """
    cells = _load_node(node, pipelines)
    from ipylab import JupyterFrontEnd

    app = JupyterFrontEnd()

    def _create_cell_with_text(text: str) -> None:
        # Noted this only works with Notebook >7.0 or Jupyter Lab. It doesn't work with
        # VS Code Notebook due to imcompatible backends.
        app.commands.execute("notebook:insert-cell-below")
        app.commands.execute("notebook:replace-selection", {"text": text})

    for cell in cells:
        _create_cell_with_text(cell)


def _load_node(node_name: str, pipelines: _ProjectPipelines) -> list[str]:
    """Prepare the code to load dataset from catalog, import statements and function body.

    Args:
        node_name (str): The name of the node.

    Returns:
        list[str]: A list of string which is the generated code, each string represent a
        notebook cell.
    """
    node = _find_node(node_name, pipelines)
    node_func = node.func

    node_inputs = _prepare_node_inputs(node)
    imports = _prepare_imports(node_func)
    raw_function_text = _prepare_function_body(node_func)
    function_text = "# Function Body\n" + raw_function_text

    cells: list[str] = []
    cells.append(node_inputs)
    cells.append(imports)
    cells.append(function_text)
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
        "#  All debugging inputs must be specified in your project catalog",
        ]

    for node_input, func_param in zip(node_inputs, func_params):
        statements.append(f'{func_param} = catalog.load("{node_input}")')

    input_statements = "\n".join(statements)
    return input_statements


def _prepare_function_body(func: Callable) -> str:
    # https://stackoverflow.com/questions/38050649/getting-a-python-functions-source-code-without-the-definition-lines
    all_source_lines = inspect.getsourcelines(func)[0]
    # Remove any decorators
    raw_func_lines = dropwhile(lambda x: x.startswith("@"), all_source_lines)
    line: str = next(raw_func_lines).strip()
    if not line.startswith("def "):
        return line.rsplit(",")[0].strip()
    # Handle functions that are not one-liners
    first_line = next(raw_func_lines)

    # Convert return statements into print statements
    func_lines = []
    for line in raw_func_lines:
        if line.lstrip().startswith("return"):
            return_statement = line.lstrip()
            line_indentation = len(line) - len(return_statement)
            commented_return = line[:line_indentation] + "# " + return_statement
            printed_return = (
                line[:line_indentation]
                + "display("
                + return_statement[len("return") :].strip()
                + ")\n"
            )
            func_lines.append(commented_return)
            func_lines.append(printed_return)
        else:
            func_lines.append(line)

    # Find the indentation of the first line
    indentation = len(first_line) - len(first_line.lstrip())
    body = "".join(
        [first_line[indentation:]] + [line[indentation:] for line in func_lines]
    )
    body = body.strip().strip("\n")
    return body
