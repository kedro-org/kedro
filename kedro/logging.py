"""
This module contains a logging handler class which produces coloured logs and tracebacks.
"""

import logging
import os
import sys
from pathlib import Path

import click
import rich.logging
import rich.pretty
import rich.traceback


class RichHandler(rich.logging.RichHandler):
    """Identical to rich's logging handler but with a few extra behaviours:
    * warnings issued by the `warnings` module are redirected to logging
    * pretty printing is enabled on the Python REPL (including IPython and Jupyter)
    * all tracebacks are handled by rich when rich_tracebacks=True
    * constructor's arguments are mapped and passed to `rich.traceback.install`

    The list of available options of ``RichHandler`` can be found here:
    https://rich.readthedocs.io/en/stable/reference/logging.html#rich.logging.RichHandler

    The list of available options of `rich.traceback.install` can be found here:
    https://rich.readthedocs.io/en/stable/reference/traceback.html#rich.traceback.install
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        logging.captureWarnings(True)
        rich.pretty.install()

        # We suppress click here to hide tracebacks related to it conversely,
        # kedro is not suppressed to show its tracebacks for easier debugging.
        # sys.executable is used to get the kedro executable path to hide the
        # top level traceback.

        traceback_install_kwargs = {
            "suppress": [click, str(Path(sys.executable).parent)]
        }

        # Mapping arguments from RichHandler's Constructor to rich.traceback.install
        prefix = "tracebacks_"
        for key, value in kwargs.items():
            if key.startswith(prefix):
                key_prefix_removed = key[len(prefix) :]
                if key_prefix_removed == "suppress":
                    traceback_install_kwargs[key_prefix_removed].extend(value)
                else:
                    traceback_install_kwargs[key_prefix_removed] = value

        if self.rich_tracebacks and "DATABRICKS_RUNTIME_VERSION" not in os.environ:
            # Rich traceback handling does not work on databricks. Hopefully this will be
            # fixed on their side at some point, but until then we disable it.
            # See https://github.com/Textualize/rich/issues/2455
            rich.traceback.install(**traceback_install_kwargs)
