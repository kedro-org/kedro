import logging.config
import sys
from pathlib import Path

from IPython.core.magic import register_line_magic, needs_local_scope

# Find the project root (./../../../)
startup_error = None
project_path = Path(__file__).parents[3].resolve()


@register_line_magic
def reload_kedro(path, line=None):
    """Line magic which reloads all Kedro default variables."""
    global startup_error
    global context
    global catalog

    try:
        import kedro.config.default_logger
        from kedro.framework.context import load_context
        from kedro.framework.cli.jupyter import collect_line_magic
    except ImportError:
        logging.error(
            "Kedro appears not to be installed in your current environment "
            "or your current IPython session was not started in a valid Kedro project."
        )
        raise

    try:
        path = path or project_path

        # remove cached user modules
        context = load_context(path)
        to_remove = [mod for mod in sys.modules if mod.startswith(context.package_name)]
        # `del` is used instead of `reload()` because: If the new version of a module does not
        # define a name that was defined by the old version, the old definition remains.
        for module in to_remove:
            del sys.modules[module]

        logging.debug("Loading the context from %s", str(path))
        # Reload context to fix `pickle` related error (it is unable to serialize reloaded objects)
        # Some details can be found here:
        # https://modwsgi.readthedocs.io/en/develop/user-guides/issues-with-pickle-module.html#packing-and-script-reloading
        context = load_context(path)
        catalog = context.catalog

        logging.info("** Kedro project %s", str(context.project_name))
        logging.info("Defined global variable `context` and `catalog`")

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
