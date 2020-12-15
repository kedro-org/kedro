import logging.config
import sys
from pathlib import Path

from IPython.core.magic import register_line_magic, needs_local_scope

# Find the project root (./../../../)
from kedro.framework.startup import _get_project_metadata

startup_error = None
project_path = Path(__file__).parents[3].resolve()


@register_line_magic
def reload_kedro(path, line=None):
    """Line magic which reloads all Kedro default variables."""
    global startup_error
    global context
    global catalog
    global session

    try:
        import kedro.config.default_logger
        from kedro.framework.hooks import get_hook_manager
        from kedro.framework.session import KedroSession
        from kedro.framework.session.session import _activate_session
        from kedro.framework.cli.jupyter import collect_line_magic
    except ImportError:
        logging.error(
            "Kedro appears not to be installed in your current environment "
            "or your current IPython session was not started in a valid Kedro project."
        )
        raise

    try:
        path = path or project_path

        # clear hook manager
        hook_manager = get_hook_manager()
        name_plugin_pairs = hook_manager.list_name_plugin()
        for name, plugin in name_plugin_pairs:
            hook_manager.unregister(name=name, plugin=plugin)

        # remove cached user modules
        metadata = _get_project_metadata(path)
        to_remove = [
            mod for mod in sys.modules if mod.startswith(metadata.package_name)
        ]
        # `del` is used instead of `reload()` because: If the new version of a module does not
        # define a name that was defined by the old version, the old definition remains.
        for module in to_remove:
            del sys.modules[module]

        session = KedroSession.create(metadata.package_name, path)
        _activate_session(session, force=True)
        logging.debug("Loading the context from %s", str(path))
        context = session.load_context()
        catalog = context.catalog

        logging.info("** Kedro project %s", str(metadata.project_name))
        logging.info("Defined global variable `context`, `session` and `catalog`")

        for line_magic in collect_line_magic():
            register_line_magic(needs_local_scope(line_magic))
            logging.info("Registered line magic `%s`", line_magic.__name__)
    except Exception as err:
        startup_error = err
        logging.exception(
            "Kedro's ipython session startup script failed:\n%s", str(err)
        )
        raise err


reload_kedro(project_path)
