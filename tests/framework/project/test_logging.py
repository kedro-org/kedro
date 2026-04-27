import importlib
import logging
import sys
from pathlib import Path
from unittest import mock

import pytest
import yaml

from kedro.framework.project import LOGGING, configure_logging, configure_project
from kedro.io import DataCatalog
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


@pytest.mark.parametrize(
    "logging_filename",
    ["logging.yml", "logging.yaml"],
)
def test_environment_variable_logging_config(monkeypatch, tmp_path, logging_filename):
    config_path = Path(tmp_path) / logging_filename
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
    """Test the configuration is not overridden but extend for `suppress`"""
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


@pytest.mark.parametrize(
    "logging_filename",
    ["logging.yml", "logging.yaml"],
)
def test_default_logging_info_emission(monkeypatch, tmp_path, caplog, logging_filename):
    config_path = (Path(tmp_path) / "conf" / logging_filename).absolute()
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
    catalog = DataCatalog.from_config({"dummy": {"type": "MemoryDataset"}})

    # Add a custom handler (non-RichHandler)
    custom_handler = CustomHandler()
    root_logger = logging.getLogger()
    root_logger.addHandler(custom_handler)

    # Emit some logs
    assert not custom_handler.records
    catalog.save("dummy", data)
    assert custom_handler.records

    for record in custom_handler.records:
        # Markup should never appear in the message itself with the new approach
        # Markup is handled via rich_format extra attribute, which is ignored by non-RichHandler
        assert "[dark_orange]" not in record.message


def test_configure_project_preserve_logging_keeps_runtime_handlers():
    """Runtime-added handlers should survive configure_project() when preserve_logging=True.

    Regression test for https://github.com/kedro-org/kedro/issues/4606:
    calling configure_project() triggers dictConfig(), which resets the logging
    state and silently discards any handlers added after the initial LOGGING setup.
    """
    custom_handler = logging.StreamHandler()
    custom_handler.name = "custom_runtime_handler"
    root_logger = logging.getLogger()
    root_logger.addHandler(custom_handler)

    try:
        configure_project("test_project_preserve", preserve_logging=True)

        handler_names = {h.name for h in root_logger.handlers}
        assert "custom_runtime_handler" in handler_names
        # The package logger should still be registered in LOGGING.data
        assert "test_project_preserve" in LOGGING.data.get("loggers", {})
    finally:
        root_logger.removeHandler(custom_handler)


def test_configure_project_overwrites_runtime_handlers_by_default():
    """Without preserve_logging=True, configure_project() wipes runtime-added handlers.

    This documents the existing (pre-fix) default behaviour and ensures we haven't
    accidentally changed it.
    """
    custom_handler = logging.StreamHandler()
    custom_handler.name = "custom_runtime_handler_default"
    root_logger = logging.getLogger()
    root_logger.addHandler(custom_handler)

    try:
        configure_project("test_project_no_preserve")

        handler_names = {h.name for h in root_logger.handlers}
        assert "custom_runtime_handler_default" not in handler_names
    finally:
        root_logger.removeHandler(custom_handler)


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


def test_validate_safe_config():
    """Test that _validate_logging_config passes safe configs unchanged."""
    from kedro.framework.project import _ProjectLogging

    input_config = {
        "version": 1,
        "handlers": {"console": {"class": "logging.StreamHandler"}},
        "loggers": {"kedro": {"level": "INFO"}},
    }

    logging_instance = _ProjectLogging()
    result = logging_instance._validate_logging_config(input_config)
    assert result == input_config


@pytest.mark.parametrize(
    "class_path",
    [
        "logging.StreamHandler",
        "logging.FileHandler",
        "logging.handlers.RotatingFileHandler",
        "logging.Formatter",
        "logging.Filter",
        "kedro.logging.RichHandler",
    ],
)
def test_validate_logging_class_allows_legitimate_classes(class_path):
    """Legitimate logging classes must pass validation without error."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    # Should not raise
    logging_instance._validate_logging_class(class_path)


@pytest.mark.parametrize(
    "class_path",
    [
        "subprocess.Popen",
        "os.system",
        "builtins.eval",
        "builtins.exec",
    ],
)
def test_validate_logging_class_blocks_non_logging_classes(class_path):
    """Non-logging classes (e.g. subprocess.Popen) must be rejected."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    with pytest.raises(ValueError, match="Invalid logging class"):
        logging_instance._validate_logging_class(class_path)


def test_validate_logging_class_blocks_nonexistent_class():
    """A class that doesn't exist in its module must be rejected."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    with pytest.raises(ValueError, match="not found in module"):
        logging_instance._validate_logging_class("logging.NonExistentHandler")


def test_validate_logging_class_blocks_nonexistent_module():
    """A class from a non-importable module must be rejected."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    with pytest.raises(ValueError, match="Cannot import module"):
        logging_instance._validate_logging_class("totally.fake.module.Handler")


def test_validate_logging_class_bare_name_passes():
    """A bare class name with no module prefix must pass (logging resolves it)."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    logging_instance._validate_logging_class("StreamHandler")  # should not raise


def test_validate_config_blocks_rce_via_class():
    """The subprocess.Popen RCE vector via the 'class' key must be blocked."""
    from kedro.framework.project import _ProjectLogging

    malicious_config = {
        "version": 1,
        "handlers": {
            "rce": {
                "class": "subprocess.Popen",
                "args": "id",
                "shell": True,
            }
        },
        "root": {"handlers": ["rce"]},
    }

    logging_instance = _ProjectLogging()
    with pytest.raises(ValueError, match="Invalid logging class"):
        logging_instance.configure(malicious_config)


@pytest.mark.parametrize(
    "input_config",
    [
        # Simple dict with '()' key
        {
            "version": 1,
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "()": "os.system",  # Dangerous factory
                    "args": ["echo pwned"],
                }
            },
            "loggers": {"kedro": {"level": "INFO"}},
        },
        # Nested dict with '()' in list
        {
            "handlers": [
                {"class": "logging.StreamHandler", "()": "subprocess.call"},
                {"class": "logging.FileHandler", "filename": "log.txt"},
            ]
        },
    ],
)
def test_validate_raises_error_on_factory_keys(input_config):
    """Test that _validate_logging_config raises ValueError on '()' factory keys."""
    from kedro.framework.project import _ProjectLogging

    logging_instance = _ProjectLogging()
    with pytest.raises(
        ValueError, match="The '\\(\\)\\' key is not allowed in logging configuration"
    ):
        logging_instance.configure(input_config)
