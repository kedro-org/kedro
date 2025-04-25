import importlib
import logging
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

from kedro.framework.project import LOGGING, configure_logging, configure_project
from kedro.io import KedroDataCatalog
from kedro.logging import RichHandler, _format_rich
from kedro.utils import _has_rich_handler


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
        _format_rich("Hello World!", "dark_orange")
        == "[dark_orange]Hello World![/dark_orange]"
    )


def test_has_rich_handler():
    test_logger = logging.getLogger("test_logger")
    with mock.patch("builtins.__import__", side_effect=ImportError):
        assert not _has_rich_handler(test_logger)

    if importlib.util.find_spec("rich"):
        from rich.logging import RichHandler

        test_logger.addHandler(RichHandler())
        assert _has_rich_handler(test_logger)
    else:
        assert not _has_rich_handler(test_logger)


def test_default_logging_info_emission(monkeypatch, tmp_path, caplog):
    config_path = (Path(tmp_path) / "conf" / "logging.yml").absolute()
    config_path.parent.mkdir(parents=True)
    logging_config = {"version": 1, "loggers": {"kedro": {"level": "DEBUG"}}}
    with config_path.open("w", encoding="utf-8") as f:
        yaml.dump(logging_config, f)
    import os

    from kedro.framework.project import _ProjectLogging

    os.chdir(tmp_path)
    LOGGING = _ProjectLogging()

    assert LOGGING.data == logging_config
    assert logging.getLogger("kedro").level == logging.DEBUG
    expected_message = "You can change this by setting the KEDRO_LOGGING_CONFIG environment variable accordingly."
    assert expected_message in "".join(caplog.messages).strip("\n")


def test_logger_without_rich_markup():
    class CustomHandler(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

    data = ("dummy",)
    catalog = KedroDataCatalog.from_config({"dummy": {"type": "MemoryDataset"}})
    catalog._use_rich_markup = False

    # Add a custom handler
    custom_handler = CustomHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(custom_handler)

    # Emit some logs
    assert not custom_handler.records
    catalog.save("dummy", data)
    assert custom_handler.records

    for record in custom_handler.records:
        assert "[dark_orange]" not in record.message


def test_logger_with_invalid_markup_args():
    root_logger = logging.getLogger()
    rich_handler = RichHandler()
    root_logger.addHandler(rich_handler)
    var = "dummy"
    with pytest.raises(TypeError):
        root_logger.warning("dummy %s", var, extra={"rich_format": "invalid_arg"})


def test_rich_format_with_list(capsys, mocker):
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    rich_handler = RichHandler()
    root_logger.addHandler(rich_handler)

    mock_format_rich = mocker.patch(
        "kedro.logging._format_rich",
        side_effect=["[blue]blue[/blue]", "[red]red[/red]"],
    )

    root_logger.warning(
        "text in %s, and text in %s",
        "blue",
        "red",
        extra={"rich_format": ["blue", "red"]},
    )

    captured = capsys.readouterr()
    stdout = captured.out + captured.err

    assert "text in" in stdout and "blue" in stdout
    assert mock_format_rich.call_count == 2


def test_rich_format_with_invalid_type():
    root_logger = logging.getLogger()
    root_logger.handlers.clear()

    rich_handler = RichHandler()
    root_logger.addHandler(rich_handler)

    with pytest.raises(
        TypeError, match="rich_format only accept non-empty list as an argument"
    ):
        root_logger.warning("value: %s", "val", extra={"rich_format": "red"})
