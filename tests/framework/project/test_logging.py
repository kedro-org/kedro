import logging
from kedro.framework.project import (
    LOGGING,
    configure_logging,
)  # noqa # pylint:disable=unused-import


def test_default_logging_config():
    assert LOGGING.data == {
        "disable_existing_loggers": False,
        "handlers": {"rich": {"class": "rich.logging.RichHandler"}},
        "loggers": {"kedro": {"level": "INFO"}},
        "root": {"handlers": ["rich"]},
        "version": 1,
    }
    assert "rich" in {handler.name for handler in logging.getLogger().handlers}
    assert logging.getLogger("kedro").level == logging.INFO


def test_configure_logging():
    logging_config = {"version": 1, "loggers": {"kedro": {"level": "WARNING"}}}
    configure_logging(logging_config)
    assert LOGGING.data == logging_config
    assert logging.getLogger("kedro").level == logging.WARNING
