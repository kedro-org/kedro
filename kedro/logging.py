import copy
import logging
import sys
from logging import LogRecord
from pathlib import Path
from typing import Any

import click
import rich.logging
import rich.pretty
import rich.traceback

from kedro.utils import _format_rich, _is_databricks


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

    def __init__(self, *args: Any, **kwargs: Any):
        if "markup" not in kwargs:
            kwargs.update({"markup": True})  # Set markup as default
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

        if self.rich_tracebacks and not _is_databricks():
            # Rich traceback handling does not work on databricks. Hopefully this will be
            # fixed on their side at some point, but until then we disable it.
            # See https://github.com/Textualize/rich/issues/2455
            rich.traceback.install(**traceback_install_kwargs)  # type: ignore[arg-type]

    def emit(self, record: LogRecord) -> None:
        args = record.args
        if not args or not hasattr(record, "rich_format"):
            return super().emit(record)

        else:
            # LogRecord is shared among all handler, created a new instance so it does not affect the rest.
            updated_record = copy.copy(record)
            format_args = record.rich_format  # type: ignore

            if format_args and isinstance(format_args, list):
                new_args = list(args)
                # Add markup to the message
                # if the list is shorter than the arg list, keep it unchanged
                for i, color in enumerate(format_args):
                    new_args[i] = _format_rich(str(new_args[i]), color)
                updated_record.args = tuple(new_args)
                super().emit(updated_record)
            else:
                raise TypeError("rich_format only accept non-empty list as an argument")
