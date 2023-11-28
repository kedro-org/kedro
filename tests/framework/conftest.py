import pytest

from kedro.framework.project import configure_logging


@pytest.fixture
def default_logging_config():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "rich": {"class": "kedro.logging.RichHandler", "rich_tracebacks": True}
        },
        "loggers": {"kedro": {"level": "INFO"}},
        "root": {"handlers": ["rich"]},
    }
    return logging_config


@pytest.fixture(autouse=True)
def reset_logging(request, default_logging_config):
    yield
    if "nologreset" in request.keywords:
        return

    configure_logging(default_logging_config)
