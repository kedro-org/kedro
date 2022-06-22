"""This module facilitates the loading of the default ``kedro.config``
for setting up the logging
"""
import os
import sys
from pathlib import Path

import click
import yaml
from rich.traceback import install

from kedro.framework.project import configure_logging


def configure_default_logging():
    logging_config = yaml.safe_load((Path(__file__).parent / "logging.yml").read_text())
    configure_logging(logging_config)

    # We suppress click here to hide tracebacks related to it conversely,
    # kedro is not suppressed to show its tracebacks for easier debugging.
    # sys.executable is used to get the kedro executable path to hide the top level traceback.
    install(show_locals=True, suppress=[click, os.path.dirname(sys.executable)])
