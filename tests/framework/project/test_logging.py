import logging
import sys
from pathlib import Path

import pytest
import yaml

from kedro.framework.project import LOGGING, configure_logging, configure_project
from kedro.logging import RichHandler, fmt_rich, has_rich_handler


@pytest.fixture
def default_logging_config_with_project():
    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "rich": {"class": "kedro.logging.RichHandler", "rich_tracebacks": True}
        },
        "loggers": {"kedro": {"level": "INFO"}, "test_project": {"level": "INFO"}},
        "root": {"handlers": ["rich"]},
    }
    return logging_config


def test_default_logging_config(default_logging_config):
    assert LOGGING.data == default_logging_config
    assert "rich" in {handler.name for handler in logging.getLogger().handlers}
    assert logging.getLogger("kedro").level == logging.INFO


def test_project_logging_in_default_logging_config(default_logging_config_with_project):
    configure_project("test_project")
    assert LOGGING.data == default_logging_config_with_project
    assert logging.getLogger("kedro").level == logging.INFO
    assert logging.getLogger("test_project").level == logging.INFO


def test_environment_variable_logging_config(monkeypatch, tmp_path):
    config_path = Path(tmp_path) / "logging.yml"
    monkeypatch.setenv("KEDRO_LOGGING_CONFIG", config_path.absolute())
    logging_config = {"version": 1, "loggers": {"kedro": {"level": "WARNING"}}}
    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(logging_config, f)
    from kedro.framework.project import _ProjectLogging

    LOGGING = _ProjectLogging()

    assert LOGGING.data == logging_config
    assert logging.getLogger("kedro").level == logging.WARNING


def test_configure_logging():
    logging_config = {"version": 1, "loggers": {"kedro": {"level": "WARNING"}}}
    configure_logging(logging_config)
    assert LOGGING.data == logging_config
    assert logging.getLogger("kedro").level == logging.WARNING


def test_rich_traceback_enabled(mocker, default_logging_config):
    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")

    LOGGING.configure(default_logging_config)

    rich_traceback_install.assert_called()
    rich_pretty_install.assert_called()


def test_rich_traceback_not_installed(mocker, default_logging_config):
    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")
    rich_handler = {
        "class": "kedro.logging.RichHandler",
        "rich_tracebacks": False,
    }
    test_logging_config = default_logging_config
    test_logging_config["handlers"]["rich"] = rich_handler

    LOGGING.configure(test_logging_config)

    rich_pretty_install.assert_called_once()
    rich_traceback_install.assert_not_called()


def test_rich_traceback_configuration(mocker, default_logging_config):
    import click

    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")

    sys_executable_path = str(Path(sys.executable).parent)
    traceback_install_defaults = {"suppress": [click, sys_executable_path]}

    rich_handler = {
        "class": "kedro.logging.RichHandler",
        "rich_tracebacks": True,
        "tracebacks_show_locals": True,
    }

    test_logging_config = default_logging_config
    test_logging_config["handlers"]["rich"] = rich_handler
    LOGGING.configure(test_logging_config)

    expected_install_defaults = traceback_install_defaults
    expected_install_defaults["show_locals"] = True
    rich_traceback_install.assert_called_with(**expected_install_defaults)
    rich_pretty_install.assert_called_once()


def test_rich_traceback_configuration_extend_suppress(mocker, default_logging_config):
    """Test the configuration is not overrided but extend for `suppress`"""
    import click

    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")

    sys_executable_path = str(Path(sys.executable).parent)
    traceback_install_defaults = {"suppress": [click, sys_executable_path]}
    fake_path = "dummy"
    rich_handler = {
        "class": "kedro.logging.RichHandler",
        "rich_tracebacks": True,
        "tracebacks_suppress": [fake_path],
    }

    test_logging_config = default_logging_config
    test_logging_config["handlers"]["rich"] = rich_handler
    LOGGING.configure(test_logging_config)

    expected_install_defaults = traceback_install_defaults
    expected_install_defaults["suppress"].extend([fake_path])
    rich_traceback_install.assert_called_with(**expected_install_defaults)
    rich_pretty_install.assert_called_once()


def test_rich_traceback_disabled_on_databricks(
    mocker, monkeypatch, default_logging_config
):
    monkeypatch.setenv("DATABRICKS_RUNTIME_VERSION", "1")
    rich_traceback_install = mocker.patch("rich.traceback.install")
    rich_pretty_install = mocker.patch("rich.pretty.install")

    LOGGING.configure(default_logging_config)

    rich_traceback_install.assert_not_called()
    rich_pretty_install.assert_called()


def test_rich_format():
    assert (
        fmt_rich("Hello World!", "dark_orange")
        == "[dark_orange]Hello World![/dark_orange]"
    )


def test_has_rich_handler():
    test_logger = logging.getLogger("test_logger")
    assert not has_rich_handler(test_logger)
    test_logger.addHandler(RichHandler())
    assert has_rich_handler(test_logger)


def test_default_logging_info_emission(monkeypatch, capsys):
    # Expected path and logging configuration
    expected_path = Path("conf/logging.yml")
    dummy_logging_config = yaml.dump(
        {"version": 1, "loggers": {"kedro": {"level": "INFO"}}}
    )

    # Setup environment and path mocks
    monkeypatch.delenv("KEDRO_LOGGING_CONFIG", raising=False)
    monkeypatch.setattr(Path, "exists", lambda x: x == expected_path)
    monkeypatch.setattr(
        Path,
        "read_text",
        lambda x, encoding="utf-8": dummy_logging_config
        if x == expected_path
        else FileNotFoundError("File not found"),
    )

    from kedro.framework.project import _ProjectLogging

    _ProjectLogging()

    captured = capsys.readouterr()

    expected_message = f"Using `{expected_path}`"
    assert (
        expected_message in captured.out
    ), f"Expected message not found in logs: {captured.out}"
