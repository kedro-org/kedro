import logging.config
import os
import sys
from pathlib import Path

from IPython.core.magic import register_line_magic

# Find the project root (./../../../)
startup_error = None
project_path = Path(__file__).parents[3].resolve()


@register_line_magic
def reload_kedro(path, line=None):
    """"Line magic which reloads all Kedro default variables."""
    global startup_error
    global context
    global catalog

    try:
        import kedro.config.default_logger
        from kedro.context import KEDRO_ENV_VAR, load_context
        from kedro.cli.jupyter import collect_line_magic
    except ImportError:
        logging.error(
            "Kedro appears not to be installed in your current environment "
            "or your current IPython session was not started in a valid Kedro project."
        )
        raise

    try:
        path = path or project_path
        logging.debug("Loading the context from %s", str(path))

        context = load_context(path, env=os.getenv(KEDRO_ENV_VAR))
        catalog = context.catalog

        # remove cached user modules
        package_name = context.__module__.split(".")[0]
        to_remove = [mod for mod in sys.modules if mod.startswith(package_name)]
        for module in to_remove:
            del sys.modules[module]

        logging.info("** Kedro project %s", str(context.project_name))
        logging.info("Defined global variable `context` and `catalog`")

        for line_magic in collect_line_magic():
            register_line_magic(line_magic)
            logging.info("Registered line magic `%s`", line_magic.__name__)
    except Exception as err:
        startup_error = err
        logging.exception(
            "Kedro's ipython session startup script failed:\n%s", str(err)
        )
        raise err


reload_kedro(project_path)
