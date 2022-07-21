import logging

import pytest

from kedro.framework.project import LOGGING, configure_logging

default_logging_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"rich": {"class": "rich.logging.RichHandler"}},
    "loggers": {"kedro": {"level": "INFO"}},
    "root": {"handlers": ["rich"]},
}


@pytest.fixture(autouse=True)
def reset_logging():
    yield
    configure_logging(default_logging_config)


def test_default_logging_config():
    assert LOGGING.data == default_logging_config
    assert "rich" in {handler.name for handler in logging.getLogger().handlers}
    assert logging.getLogger("kedro").level == logging.INFO


def test_configure_logging():
    logging_config = {"version": 1, "loggers": {"kedro": {"level": "WARNING"}}}
    configure_logging(logging_config)
    assert LOGGING.data == logging_config
    assert logging.getLogger("kedro").level == logging.WARNING
