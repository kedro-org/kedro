import logging
import os
import sys
from multiprocessing.sharedctypes import Value
from pathlib import Path

import click
import rich.logging
import rich.pretty
import rich.traceback

logger = logging.getLogger(__file__)


class RichHandler(rich.logging.RichHandler):
    """Identical to rich's logging handler but with a few extra behaviours:
    * warnings issued by the `warnings` module are redirected to logging
    * pretty printing is enabled on the Python REPL (including IPython and Jupyter)
    * all tracebacks are handled by rich when rich_tracebacks=True
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.captureWarnings(True)
        rich.pretty.install()

        # We suppress click here to hide tracebacks related to it conversely,
        # kedro is not suppressed to show its tracebacks for easier debugging.
        # sys.executable is used to get the kedro executable path to hide the
        # top level traceback.
        # Rich traceback handling does not work on databricks. Hopefully this will be
        # fixed on their side at some point, but until then we disable it.
        # See https://github.com/Textualize/rich/issues/2455

        mapped_kwargs = {"suppress": [click, str(Path(sys.executable).parent)]}

        # Mapping Arguments from RichHandler's Constructor to rich.traceback.install
        for key, value in kwargs.items():
            prefix = "tracebacks_"
            if key.startswith(prefix):
                key_prefix_removed = key[len(prefix) :]
                if key_prefix_removed == "suppress":
                    mapped_kwargs[key_prefix_removed] += value
                else:
                    mapped_kwargs[key_prefix_removed] = value
            elif key in ("locals_max_length", "locals_max_string"):
                mapped_kwargs[key] = value

        if self.rich_tracebacks:
            if "DATABRICKS_RUNTIME_VERSION" not in os.environ:
                # https://rich.readthedocs.io/en/stable/reference/logging.html?highlight=rich%20handler#rich.logging.RichHandler
                # Support compatible arguments between RichHandler and rich.traceback.install
                rich.traceback.install(**mapped_kwargs)
