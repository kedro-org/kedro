import logging.config
from pathlib import Path

from IPython.core.magic import register_line_magic


@register_line_magic
def reload_kedro(project_path, line=None):
    """"Line magic which reloads all Kedro default variables."""
    global startup_error
    global context
    global catalog
    try:
        import kedro.config.default_logger
        from kedro.context import load_context

        context = load_context(project_path)
        catalog = context.catalog
        logging.info("** Kedro project {}".format(context.project_name))

        logging.info("Defined global variable `context` and `catalog`")
    except ImportError:
        logging.error(
            "Kedro appears not to be installed in your current environment "
            "or your current IPython session was not started in a valid Kedro project."
        )
        raise
    except Exception as err:
        startup_error = err
        logging.error("Kedro's ipython session startup script failed:\n%s", str(err))
        raise err


# Find the project root (./../../../)
startup_error = None
project_path = Path(__file__).parents[3].resolve()
reload_kedro(project_path)
