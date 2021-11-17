"""This module contains unit tests for methods in the Kedro __init__.py
"""

import logging

from kedro.config.default_logger import LOGGING_CONFIG


def test_cli_logging_setup():
    def to_names(handlers):
        return [h.name for h in handlers]

    assert LOGGING_CONFIG is not None

    # Check root logger is set up correctly
    root_handler_names = to_names(logging.getLogger().handlers)
    all_handlers = ["console", "info_file_handler", "error_file_handler"]
    intersection = set(root_handler_names).intersection(all_handlers)
    assert len(intersection) == 3
