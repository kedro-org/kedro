# pylint: disable=import-outside-toplevel,global-statement,invalid-name
"""
This script creates an IPython extension to load Kedro-related variables in
local scope.
"""
import logging.config
import sys
from pathlib import Path
from typing import Any, Dict

from IPython import get_ipython
from IPython.core.magic import needs_local_scope, register_line_magic

startup_path = Path.cwd()
project_path = startup_path


def _remove_cached_modules(package_name):
    to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
    # `del` is used instead of `reload()` because: If the new version of a module does not
    # define a name that was defined by the old version, the old definition remains.
    for module in to_remove:
        del sys.modules[module]  # pragma: no cover


def _clear_hook_manager():
    from kedro.framework.hooks import get_hook_manager

    hook_manager = get_hook_manager()
    name_plugin_pairs = hook_manager.list_name_plugin()
    for name, plugin in name_plugin_pairs:
        hook_manager.unregister(name=name, plugin=plugin)  # pragma: no cover


def _find_kedro_project(current_dir):  # pragma: no cover
    from kedro.framework.startup import _is_project

    while current_dir != current_dir.parent:
        if _is_project(current_dir):
            return current_dir
        current_dir = current_dir.parent

    return None


def reload_kedro(path, env: str = None, extra_params: Dict[str, Any] = None):
    """Line magic which reloads all Kedro default variables."""

    import kedro.config.default_logger  # noqa: F401 # pylint: disable=unused-import
    from kedro.framework.cli import load_entry_points
    from kedro.framework.project import pipelines
    from kedro.framework.session import KedroSession
    from kedro.framework.session.session import _activate_session
    from kedro.framework.startup import bootstrap_project

    _clear_hook_manager()

    path = path or project_path
    metadata = bootstrap_project(path)

    _remove_cached_modules(metadata.package_name)

    session = KedroSession.create(
        metadata.package_name, path, env=env, extra_params=extra_params
    )
    _activate_session(session, force=True)
    logging.debug("Loading the context from %s", str(path))
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

    logging.info("** Kedro project %s", str(metadata.project_name))
    logging.info(
        "Defined global variable `context`, `session`, `catalog` and `pipelines`"
    )

    for line_magic in load_entry_points("line_magic"):
        register_line_magic(needs_local_scope(line_magic))
        logging.info("Registered line magic `%s`", line_magic.__name__)  # type: ignore


def init_kedro(path=""):
    """Line magic to set path to Kedro project.
    `%reload_kedro` will default to this location.
    """
    global project_path
    if path:
        project_path = Path(path).expanduser().resolve()
        logging.info("Updated path to Kedro project: %s", str(project_path))
    else:
        logging.info("No path argument was provided. Using: %s", str(project_path))


def load_ipython_extension(ipython):
    """Main entry point when %load_ext is executed"""

    global project_path
    global startup_path  # pylint:disable=global-variable-not-assigned

    ipython.register_magic_function(init_kedro, "line")
    ipython.register_magic_function(reload_kedro, "line", "reload_kedro")

    project_path = _find_kedro_project(startup_path)

    try:
        reload_kedro(project_path)
    except (ImportError, ModuleNotFoundError):
        logging.error("Kedro appears not to be installed in your current environment.")
    except Exception:  # pylint: disable=broad-except
        logging.warning(
            "Kedro extension was registered. Make sure you pass the project path to "
            "`%reload_kedro` or set it using `%init_kedro`."
        )
