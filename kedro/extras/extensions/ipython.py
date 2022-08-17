# pylint: disable=import-outside-toplevel,global-statement,invalid-name,too-many-locals
"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)
default_project_path = Path.cwd()


def _remove_cached_modules(package_name):
    to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
    # `del` is used instead of `reload()` because: If the new version of a module does not
    # define a name that was defined by the old version, the old definition remains.
    for module in to_remove:
        del sys.modules[module]  # pragma: no cover


def _find_kedro_project(current_dir: Path):  # pragma: no cover
    from kedro.framework.startup import _is_project

    while current_dir != current_dir.parent:
        if _is_project(current_dir):
            return current_dir
        current_dir = current_dir.parent

    return None


def reload_kedro(
    path: str = None, env: str = None, extra_params: Dict[str, Any] = None
):
    """Line magic which reloads all Kedro default variables.
    Setting the path will also make it default for subsequent calls.
    """
    from IPython import get_ipython
    from IPython.core.magic import needs_local_scope, register_line_magic

    from kedro.framework.cli import load_entry_points
    from kedro.framework.project import LOGGING  # noqa # pylint:disable=unused-import
    from kedro.framework.project import configure_project, pipelines
    from kedro.framework.session import KedroSession
    from kedro.framework.startup import bootstrap_project

    # If a path is provided, set it as default for subsequent calls
    global default_project_path
    if path:
        default_project_path = Path(path).expanduser().resolve()
        logger.info("Updated path to Kedro project: %s", default_project_path)
    else:
        logger.info("No path argument was provided. Using: %s", default_project_path)

    metadata = bootstrap_project(default_project_path)
    _remove_cached_modules(metadata.package_name)
    configure_project(metadata.package_name)

    session = KedroSession.create(
        metadata.package_name, default_project_path, env=env, extra_params=extra_params
    )
    context = session.load_context()
    catalog = context.catalog

    get_ipython().push(
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
        register_line_magic(needs_local_scope(line_magic))
        logger.info("Registered line magic '%s'", line_magic.__name__)  # type: ignore


def load_ipython_extension(ipython):
    """
    Main entry point when %load_ext is executed.
    IPython will look for this function specificially.
    See https://ipython.readthedocs.io/en/stable/config/extensions/index.html

    This function is called when users do `%load_ext kedro.extras.extensions.ipython`.
    When user use `kedro jupyter notebook` or `jupyter ipython`, this extension is
    loaded automatically.
    """

    from IPython.core.magic import register_line_magic
    from IPython.core.magic_arguments import argument, magic_arguments, parse_argstring

    @magic_arguments()
    # To enable positional/keyword argument for the same type
    @argument(
        "path",
        help=("Path to the project root directory."),
        nargs='?',
        default=None
    )
    @argument(
        "--env",
        dest="env",
        default=None,
        help=("Environment for the Kedro project."),
    )
    @argument(
        "--extra_params",
        dest="extra_params",
        type=json.loads,
        default=None,
        help=("""Optional dictionary containing extra project parameters
                    for underlying KedroContext. If specified, will update (and therefore
                    take precedence over) the parameters retrieved from the project
                    configuration."""),
    )
    @register_line_magic("reload_kedro")  # Register the line magic's name as `reload_kedro`
    def reload_kedro_line_magic(line):
        args = parse_argstring(reload_kedro_line_magic, line)
        reload_kedro(args.path, args.env, args.extra_params)

    global default_project_path
    # ipython.register_magic_function(reload_kedro, "line", "reload_kedro")

    default_project_path = _find_kedro_project(Path.cwd())

    if default_project_path is None:
        logger.warning(
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        return

    reload_kedro(default_project_path)
