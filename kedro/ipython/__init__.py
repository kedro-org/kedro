"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""

from __future__ import annotations

import ast
import importlib
import inspect
import logging
import os
import sys
import typing
import warnings
from pathlib import Path
from types import MappingProxyType
from typing import TYPE_CHECKING, Any, Final

from kedro.framework.session.session import KedroSession

if TYPE_CHECKING:
    from collections import OrderedDict
    from collections.abc import Callable

    from IPython.core.interactiveshell import InteractiveShell

from IPython.core.getipython import get_ipython
from IPython.core.magic import needs_local_scope, register_line_magic
from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

try:
    import rich.console as rich_console
    import rich.syntax as rich_syntax
except ImportError:  # pragma: no cover
    pass

from kedro.framework.cli import load_entry_points
from kedro.framework.cli.project import CONF_SOURCE_HELP, PARAMS_ARG_HELP
from kedro.framework.cli.utils import ENV_HELP, _split_params
from kedro.framework.project import (
    LOGGING,  # noqa: F401
    _ProjectPipelines,
    configure_project,
    pipelines,
    settings,
)
from kedro.framework.startup import bootstrap_project
from kedro.pipeline.node import Node
from kedro.utils import _is_databricks, find_kedro_project

logger = logging.getLogger(__name__)

FunctionParameters = MappingProxyType

RICH_INSTALLED: Final = importlib.util.find_spec("rich") is not None


def load_ipython_extension(ipython: InteractiveShell) -> None:
    """
    Main entry point when %load_ext kedro.ipython is executed, either manually or
    automatically through `kedro ipython` or `kedro jupyter lab/notebook`.
    IPython will look for this function specifically.
    See https://ipython.readthedocs.io/en/stable/config/extensions/index.html
    """
    ipython.register_magic_function(func=magic_reload_kedro, magic_name="reload_kedro")  # type: ignore[call-arg]
    logger.info("Registered line magic '%reload_kedro'")
    ipython.register_magic_function(func=magic_load_node, magic_name="load_node")  # type: ignore[call-arg]
    logger.info("Registered line magic '%load_node'")

    if find_kedro_project(Path.cwd()) is None:
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
    See https://docs.kedro.org/en/stable/integrations-and-plugins/notebooks_and_ipython/kedro_and_notebooks/#reload_kedro-line-magic
    for more.
    """
    args = parse_argstring(magic_reload_kedro, line)
    reload_kedro(args.path, args.env, args.params, local_ns, args.conf_source)


def reload_kedro(
    path: str | None = None,
    env: str | None = None,
    runtime_params: dict[str, Any] | None = None,
    local_namespace: dict[str, Any] | None = None,
    conf_source: str | None = None,
) -> None:  # pragma: no cover
    """Function that underlies the %reload_kedro Line magic. This should not be imported
    or run directly but instead invoked through %reload_kedro."""

    project_path = _resolve_project_path(path, local_namespace)

    metadata = bootstrap_project(project_path)
    _remove_cached_modules(metadata.package_name)
    configure_project(metadata.package_name)
    is_kedrosession = issubclass(settings.SESSION_CLASS, KedroSession)
    create_args: dict[str, Any] = {
        "project_path": project_path,
        "env": env,
        "conf_source": conf_source,
    }
    # This conditioning is needed because KedroSession accepts runtime_params in create() method,
    # while KedroServiceSession accepts them in run() method. This is temporary solution until
    # KedroSession is removed in favor of KedroServiceSession.
    if is_kedrosession:
        create_args["runtime_params"] = runtime_params

    session = settings.SESSION_CLASS.create(**create_args)
    if is_kedrosession:
        context = session.load_context()
    else:
        context = session.load_context(runtime_params=runtime_params)
    catalog = context.catalog

    get_ipython().push(  # type: ignore[no-untyped-call]
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
        if (
            local_namespace
            and local_namespace.get("context")
            and hasattr(local_namespace["context"], "project_path")
        ):
            project_path = local_namespace["context"].project_path
        else:
            project_path = find_kedro_project(Path.cwd())
        if project_path:
            logger.info(
                "Resolved project path as: %s.\nTo set a different path, run "
                "'%%reload_kedro <project_root>'",
                project_path,
            )

    if (
        project_path
        and local_namespace
        and local_namespace.get("context")
        and hasattr(local_namespace["context"], "project_path")  # Avoid name collision
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


def _guess_run_environment() -> str:  # pragma: no cover
    """Best effort to guess the IPython/Jupyter environment"""
    # https://github.com/microsoft/vscode-jupyter/issues/7380
    if os.environ.get("VSCODE_PID") or os.environ.get("VSCODE_CWD"):
        return "vscode"
    elif _is_databricks():
        return "databricks"
    elif hasattr(get_ipython(), "kernel"):  # type: ignore[no-untyped-call]
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
def magic_load_node(args: str) -> None:
    """The line magic %load_node <node_name>.
    Currently, this feature is only available for Jupyter Notebook (>7.0), Jupyter Lab, IPython,
    and VSCode Notebook. This line magic will generate code in multiple cells to load
    datasets from `DataCatalog`, import relevant functions and modules, node function
    definition and a function call. If generating code is not possible, it will print
    the code instead.
    """
    parameters = parse_argstring(magic_load_node, args)
    node_name = parameters.node

    cells = _load_node(node_name, pipelines)

    run_environment = _guess_run_environment()

    if run_environment in ("ipython", "vscode", "jupyter"):
        # Combine multiple cells into one for IPython or VSCode or Jupyter
        combined_cell = "\n\n".join(cells)
        _create_cell_with_text(combined_cell)
    else:
        # For other environments or if detection fails, just print the cells
        _print_cells(cells)


class _NodeBoundArguments(inspect.BoundArguments):
    """Similar to inspect.BoundArguments"""

    def __init__(
        self, signature: inspect.Signature, arguments: OrderedDict[str, Any]
    ) -> None:
        super().__init__(signature, arguments)

    @property
    def input_params_dict(self) -> dict[str, str] | None:
        """A mapping of {variable name: dataset_name}"""
        var_positional_arg_name = self._find_var_positional_arg()
        inputs_params_dict = {}
        for param, dataset_name in self.arguments.items():
            if param == var_positional_arg_name:
                # If the argument is *args, use the dataset name instead
                for arg in dataset_name:
                    inputs_params_dict[arg] = arg
            else:
                inputs_params_dict[param] = dataset_name
        return inputs_params_dict

    def _find_var_positional_arg(self) -> str | None:
        """Find the name of the VAR_POSITIONAL argument( *args), if any."""
        for k, v in self.signature.parameters.items():
            if v.kind == inspect.Parameter.VAR_POSITIONAL:
                return k
        return None


def _create_cell_with_text(text: str) -> None:
    """Create a new cell with the provided text content."""
    get_ipython().set_next_input(text)  # type: ignore[no-untyped-call]


def _print_cells(cells: list[str]) -> None:
    for cell in cells:
        if RICH_INSTALLED:
            rich_console.Console().print("")
            rich_console.Console().print(
                rich_syntax.Syntax(cell, "python", theme="monokai", line_numbers=False)
            )
        else:
            print("")  # noqa: T201
            print(cell)  # noqa: T201


def _load_node(node_name: str, pipelines: _ProjectPipelines) -> list[str]:
    """Prepare the code to load dataset from catalog, import statements and function body.

    Args:
        node_name (str): The name of the node.

    Returns:
        list[str]: A list of string which is the generated code, each string represent a
        notebook cell.
    """
    warnings.warn(
        "This is an experimental feature, only Jupyter Notebook (>7.0), Jupyter Lab, IPython, and VSCode Notebook "
        "are supported. If you encounter unexpected behaviour or would like to suggest "
        "feature enhancements, add it under this github issue https://github.com/kedro-org/kedro/issues/3580"
    )
    node = _find_node(node_name, pipelines)
    node_func = node.func

    imports_cell = _prepare_imports(node_func)
    function_definition_cell = _prepare_function_body(node_func)

    node_bound_arguments = _get_node_bound_arguments(node)
    inputs_params_mapping = _prepare_node_inputs(node_bound_arguments)
    node_inputs_cell = _format_node_inputs_text(inputs_params_mapping)
    function_call_cell = _prepare_function_call(node_func, node_bound_arguments)

    cells: list[str] = []
    if node_inputs_cell:
        cells.append(node_inputs_cell)
    cells.append(imports_cell)
    cells.append(function_definition_cell)
    cells.append(function_call_cell)
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
            # Handle multiline imports, i.e.
            # from lib import (
            # a,
            # b,
            # c
            # )
            # This will not work with all edge cases but good enough with common cases that
            # are formatted automatically by black, ruff etc.
            inside_bracket = False
            # Parse any line start with from or import statement

            for _ in file.readlines():
                line = _.strip()
                if not inside_bracket:
                    # The common case
                    if line.startswith("from") or line.startswith("import"):
                        import_statement.append(line)
                        if line.endswith("("):
                            inside_bracket = True
                # Inside multi-lines import, append everything.
                else:
                    import_statement.append(line)
                    if line.endswith(")"):
                        inside_bracket = False

        clean_imports = "\n".join(import_statement).strip()
        return clean_imports
    else:
        raise FileNotFoundError(f"Could not find {node_func.__name__}")


def _get_node_bound_arguments(node: Node) -> _NodeBoundArguments:
    node_func = node.func
    node_inputs = node.inputs

    args, kwargs = Node._process_inputs_for_bind(node_inputs)
    signature = inspect.signature(node_func)
    bound_arguments = signature.bind(*args, **kwargs)
    return _NodeBoundArguments(bound_arguments.signature, bound_arguments.arguments)


def _prepare_node_inputs(
    node_bound_arguments: _NodeBoundArguments,
) -> dict[str, str] | None:
    # Remove the *args. For example {'first_arg':'a', 'args': ('b','c')}
    # will be loaded as follow:
    # first_arg = catalog.load("a")
    # b = catalog.load("b") # It doesn't have an arg name, so use the dataset name instead.
    # c = catalog.load("c")
    return node_bound_arguments.input_params_dict


def _format_node_inputs_text(input_params_dict: dict[str, str] | None) -> str | None:
    statements = [
        "# Prepare necessary inputs for debugging",
        "# All debugging inputs must be defined in your project catalog",
    ]
    if not input_params_dict:
        return None

    for func_param, dataset_name in input_params_dict.items():
        statements.append(f'{func_param} = catalog.load("{dataset_name}")')

    input_statements = "\n".join(statements)
    return input_statements


def _prepare_function_body(func: Callable) -> str:
    """Build a standalone function cell for ``%load_node``.

    Resolution order:
    1) Try AST-based extraction first and include the target function plus
       referenced same-module top-level symbols (for example helper functions,
       classes, and constants).
    2) If AST extraction cannot be performed safely, fall back to the original
       ``inspect.getsourcelines()`` output for the target function only.
    """
    source_lines, _ = inspect.getsourcelines(func)
    fallback_body = "".join(source_lines)
    python_file = inspect.getsourcefile(func)
    if not python_file:
        logger.warning(
            "Falling back to basic source extraction for '%s': "
            "could not resolve source file. Same-module dependencies may be missing.",
            func.__name__,
        )
        return fallback_body

    try:
        module_source = Path(python_file).read_text()
        module_tree = ast.parse(module_source)
        symbols = _build_module_symbol_table(module_tree)
        # Root AST node for the selected Kedro node function.
        function_node = _resolve_function_node(module_tree, func)
    except (OSError, SyntaxError, ValueError) as exc:
        logger.warning(
            "Falling back to basic source extraction for '%s': "
            "AST dependency extraction failed (%s). "
            "Same-module dependencies may be missing.",
            func.__name__,
            exc,
        )
        return fallback_body

    # Resolve transitive same-module dependencies starting from function_node,
    # e.g. node_fn -> helper_a -> helper_b.
    nodes_to_emit = _resolve_symbol_dependencies(symbols, function_node.name)
    if not nodes_to_emit:
        logger.warning(
            "Falling back to basic source extraction for '%s': "
            "no dependency nodes were resolved from AST extraction.",
            func.__name__,
        )
        return fallback_body

    # Convert resolved AST nodes back to source text in file order so generated
    # code can run standalone in the notebook cell.
    rendered_source = _build_dependency_source_block(nodes_to_emit, module_source)
    if not rendered_source:
        logger.warning(
            "Falling back to basic source extraction for '%s': "
            "could not render extracted AST nodes back to source.",
            func.__name__,
        )
        return fallback_body

    return rendered_source


def _build_module_symbol_table(module_tree: ast.Module) -> dict[str, ast.AST]:
    """Map top-level symbol names to their defining AST node.

    Example:
        Source:
            x = 1
            a = b = 10
            def helper(): ...

        ``module_tree.body`` contains top-level ``node`` entries:
            - node: Assign(targets=[Name(id="x")], ...)
              -> target.id == "x"
            - node: Assign(targets=[Name(id="a"), Name(id="b")], ...)
              -> target.id == "a", then "b"
            - node: FunctionDef(name="helper", ...)
    """
    symbol_table: dict[str, ast.AST] = {}
    for node in module_tree.body:
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef):
            symbol_table[node.name] = node
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    symbol_table[target.id] = node
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            symbol_table[node.target.id] = node
    return symbol_table


def _resolve_function_node(
    module_tree: ast.Module, func: Callable
) -> ast.FunctionDef | ast.AsyncFunctionDef:
    """Resolve the top-level AST node that corresponds to ``func``."""
    _, source_line = inspect.getsourcelines(func)
    candidates = [
        node
        for node in module_tree.body
        if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef)
        and node.name == func.__name__
    ]
    if not candidates:
        raise ValueError(f"Unable to locate node function '{func.__name__}'")

    exact_match = next(
        (node for node in candidates if node.lineno == source_line), None
    )
    return exact_match or candidates[0]


def _collect_required_symbols(node: ast.AST, known_symbols: set[str]) -> set[str]:
    """Collect loaded symbol names that are available in ``known_symbols``."""
    return {
        candidate.id
        for candidate in ast.walk(node)
        if isinstance(candidate, ast.Name)
        and isinstance(candidate.ctx, ast.Load)
        and candidate.id in known_symbols
    }


def _resolve_symbol_dependencies(
    symbols: dict[str, ast.AST], root_symbol: str
) -> list[ast.AST]:
    """Return the transitive closure of same-module symbol dependencies.

    This models top-level module symbols as a dependency graph:
    - Graph nodes: top-level symbols in ``symbols`` (functions, classes, constants).
    - Graph edges: ``A -> B`` when symbol ``A`` references ``B`` via
      ``Name(..., Load())`` in its AST subtree.

    The walk starts from ``root_symbol`` and traverses reachable edges until no
    unseen symbols remain. The traversal is recursive in effect (it resolves
    dependencies of dependencies), implemented iteratively with a worklist:
    when a newly discovered symbol is visited, its referenced symbols are added
    to the worklist and explored in subsequent iterations.
    """
    visited_symbols: set[str] = set()
    symbols_to_visit = [root_symbol]
    nodes_to_emit: list[ast.AST] = []
    candidate_symbols = set(symbols)

    while symbols_to_visit:
        symbol_name = symbols_to_visit.pop()
        if symbol_name in visited_symbols:
            continue

        symbol_node = symbols.get(symbol_name)
        if symbol_node is None:
            continue

        visited_symbols.add(symbol_name)
        nodes_to_emit.append(symbol_node)
        required = _collect_required_symbols(symbol_node, candidate_symbols)
        symbols_to_visit.extend(required)

    return nodes_to_emit


def _build_dependency_source_block(
    nodes: list[ast.AST], module_source: str
) -> str | None:
    """Render AST nodes back to source ordered by their original position."""
    emitted_segments: list[str] = []
    segment: str | None = None
    ordered_nodes = sorted(nodes, key=lambda item: getattr(item, "lineno", 0))
    for node in ordered_nodes:
        try:
            if (
                isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef | ast.ClassDef)
                and node.decorator_list
                and getattr(node, "end_lineno", None) is not None
            ):
                # AST source segments start at the def/class line; slice from the
                # first decorator to preserve behavior from inspect.getsourcelines().
                source_lines = module_source.splitlines(keepends=True)
                start_line = min(decorator.lineno for decorator in node.decorator_list)
                segment = "".join(source_lines[start_line - 1 : node.end_lineno])
            else:
                segment = ast.get_source_segment(module_source, node)
        except IndexError:
            # Guard against stale/mismatched AST location metadata and source text.
            segment = None
        if segment:
            emitted_segments.append(segment.rstrip())

    if not emitted_segments:
        return None

    return "\n\n".join(emitted_segments) + "\n"


def _prepare_function_call(
    node_func: Callable, node_bound_arguments: _NodeBoundArguments
) -> str:
    """Prepare the text for the function call."""
    func_name = node_func.__name__
    args = node_bound_arguments.input_params_dict
    kwargs = node_bound_arguments.kwargs

    # Construct the statement of func_name(a=1,b=2,c=3)
    args_str_literal = [f"{node_input}" for node_input in args] if args else []
    kwargs_str_literal = [
        f"{node_input}={dataset_name}" for node_input, dataset_name in kwargs.items()
    ]
    func_params = ", ".join(args_str_literal + kwargs_str_literal)
    body = f"""{func_name}({func_params})"""
    return body
