"""This module facilitates the loading of the default ``kedro.config``
for setting up the logging
"""

import logging.config
import os
import sys

import click
import yaml
from rich.traceback import install

CURRENT_DIR = os.path.dirname(__file__)

with open(os.path.join(CURRENT_DIR, "logging.yml"), encoding="utf-8") as conf_file:
    LOGGING_CONFIG = yaml.safe_load(conf_file.read())
    logging.config.dictConfig(LOGGING_CONFIG)
    logging.captureWarnings(True)

# We suppress click here to hide tracebacks related to it conversely,
# kedro is not suppressed to show its tracebacks for easier debugging.
# sys.executable is used to get the kedro executable path and hide the top level traceback.
install(show_locals=True, suppress=[click, os.path.dirname(sys.executable)])
