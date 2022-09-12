# pylint: disable=import-outside-toplevel,unused-import,reimported
import logging
import sys

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


def test_rich_traceback_enabled(mocker):
    """Note we need to force reload; just doing from kedro.framework.project import ...
    will not call rich.traceback.install again. Using importlib.reload does not work
    well with other tests here, hence the manual del sys.modules."""
    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")
    del sys.modules["kedro.framework.project"]
    from kedro.framework.project import LOGGING  # noqa

    rich_traceback_install.assert_called()
    rich_pretty_install.assert_called()


def test_rich_traceback_disabled_on_databricks(mocker, monkeypatch):
    monkeypatch.setenv("DATABRICKS_RUNTIME_VERSION", "1")
    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")
    del sys.modules["kedro.framework.project"]
    from kedro.framework.project import LOGGING  # noqa

    rich_traceback_install.assert_not_called()
    rich_pretty_install.assert_called()
