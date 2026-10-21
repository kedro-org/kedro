"""Logging configuration must be rejected before untrusted code executes."""

import logging
import os
import queue
import subprocess
import sys
import textwrap
from collections import UserDict, namedtuple
from pathlib import Path

import pytest
import yaml

from kedro.framework import project
from kedro.framework.project import _ProjectLogging

SKIP_WITHOUT_QUEUE_CONFIG = pytest.mark.skipif(
    sys.version_info < (3, 12), reason="Requires Python 3.12 queue config"
)


@pytest.fixture
def logging_probe(tmp_path, monkeypatch):
    """An importable module whose import, factory and constructor leave markers."""
    module_name = "kedro_logging_security_probe"
    marker = tmp_path / "executed.txt"
    (tmp_path / f"{module_name}.py").write_text(
        textwrap.dedent(
            f"""
            import logging
            import logging.handlers
            import queue
            import sys
            from pathlib import Path

            marker = Path({str(marker)!r})
            marker.write_text("imported\\n")
            STREAM = sys.stdout

            class Probe:
                # Force a later handler.name assignment to fail, proving that
                # rejection after construction is already too late.
                __slots__ = ()

                def __init__(self, *args, **kwargs):
                    marker.write_text(marker.read_text() + "constructed\\n")

            class Handler(logging.StreamHandler):
                def __init__(self, *args, **kwargs):
                    marker.write_text(marker.read_text() + "handler\\n")
                    super().__init__(*args, **kwargs)

            class EndpointHandler(Handler):
                def __init__(self, endpoint):
                    self.endpoint = endpoint
                    self.address = (endpoint.host, endpoint.port)
                    super().__init__(stream=sys.stdout)

            class Listener(logging.handlers.QueueListener):
                pass

            def queue_factory():
                marker.write_text(marker.read_text() + "factory\\n")
                return queue.Queue()
            """
        ),
        encoding="utf-8",
    )
    monkeypatch.syspath_prepend(str(tmp_path))
    yield module_name, marker
    sys.modules.pop(module_name, None)


@pytest.mark.parametrize(
    ("vector", "mapping"),
    [
        ("ext", dict),
        ("cfg_handler", dict),
        ("cfg_formatter", dict),
        ("formatter", dict),
        ("bare", dict),
        ("cfg_formatter", UserDict),
    ],
)
def test_untrusted_references_do_not_execute(logging_probe, vector, mapping):
    """Rejected configurations must not import or construct untrusted objects."""
    module_name, marker = logging_probe
    logging_instance = _ProjectLogging()
    handler = {"class": "logging.StreamHandler"}
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {"console": handler},
    }
    if vector == "ext":
        handler["stream"] = f"ext://{module_name}.STREAM"
    elif vector == "cfg_handler":
        handler["class"] = "cfg://target"
        config["target"] = f"{module_name}.Probe"
    elif vector == "cfg_formatter":
        config["formatters"] = {"probe": {"class": "cfg://target"}}
        config["target"] = f"{module_name}.Probe"
    elif vector == "formatter":
        config["formatters"] = {"probe": {"class": f"{module_name}.Probe"}}
    else:
        handler["class"] = module_name

    with pytest.raises(ValueError):
        logging_instance.configure(mapping(config))

    assert not marker.exists(), "The configuration was rejected after code executed"
    assert module_name not in sys.modules


@pytest.mark.parametrize(
    "reference",
    [
        "ext://subprocess.Popen",
        "ext://os.path",
        "ext://logging_untrusted.Handler",
        "ext://kedro.OtherHandler",
        "ext://sys.stdin",
        "ext://sys.exit",
        "ext://queue.LifoQueue",
        "ext://untrusted",
        "ext://",
    ],
)
def test_external_references_checked_before_import(reference, mocker):
    """Reject untrusted external names before attempting their imports."""
    logging_instance = _ProjectLogging()
    importer = mocker.patch("kedro.framework.project.importlib.import_module")

    with pytest.raises(ValueError):
        logging_instance._validate_logging_config({"stream": reference})

    importer.assert_not_called()


@pytest.mark.parametrize(
    "config",
    [
        {"value": "cfg://target"},
        {"class": "cfg://target"},
        {"nested": [{"value": "cfg://targets[0]"}]},
        {"nested": ("cfg://target",)},
        {"first": "cfg://second", "second": "cfg://first"},
    ],
)
def test_internal_references_rejected_without_resolution(config, mocker):
    """Reject config navigation consistently without resolving targets or cycles."""
    logging_instance = _ProjectLogging()
    importer = mocker.patch("kedro.framework.project.importlib.import_module")

    with pytest.raises(ValueError, match="cfg://"):
        logging_instance._validate_logging_config(config)

    importer.assert_not_called()


def test_mapping_wrappers_cannot_hide_factory_keys(mocker):
    """Validate nested mapping wrappers before any factory can be resolved."""
    logging_instance = _ProjectLogging()
    importer = mocker.patch("kedro.framework.project.importlib.import_module")
    config = UserDict({"filters": UserDict({"unsafe": UserDict({"()": "os.system"})})})

    with pytest.raises(ValueError, match="security risk"):
        logging_instance._validate_logging_config(config)

    importer.assert_not_called()


@pytest.mark.parametrize(
    ("class_path", "replacement"),
    [
        (None, None),
        (123, None),
        ("", None),
        ("ext://logging.StreamHandler", None),
        ("_StderrHandler", None),
        ("StreamHandler", "logging.StreamHandler"),
        ("SysLogHandler", "logging.handlers.SysLogHandler"),
    ],
)
def test_class_references_must_be_explicit_names(class_path, replacement, mocker):
    """Class values must be dotted names rather than objects or references."""
    logging_instance = _ProjectLogging()
    importer = mocker.patch("kedro.framework.project.importlib.import_module")

    with pytest.raises(ValueError, match="fully qualified") as error:
        logging_instance._validate_logging_class(class_path)

    importer.assert_not_called()
    assert "#supported-logging-references" in str(error.value)
    if replacement:
        assert f"Use '{replacement}' instead." in str(error.value)
    else:
        assert "Use 'logging." not in str(error.value)


@pytest.mark.parametrize(
    "reference", ["logging.os.system", "logging.handlers.os.abort"]
)
def test_module_aliases_cannot_escape_the_allowlist(reference):
    """An approved module's attributes cannot act as alternate import paths."""
    logging_instance = _ProjectLogging()

    with pytest.raises(ValueError, match="Cannot import module") as error:
        logging_instance._resolve_logging_object(reference)

    assert "exported directly by an importable module" in str(error.value)
    assert "use 'ext://sys.stdout'" in str(error.value)


@pytest.mark.parametrize(
    ("import_statement", "exception_type", "missing_name"),
    [
        (
            "import kedro_logging_missing_dependency",
            ModuleNotFoundError,
            "kedro_logging_missing_dependency",
        ),
        (
            "from kedro_logging_broken_formatter import missing_symbol",
            ImportError,
            "kedro_logging_broken_formatter",
        ),
    ],
)
def test_import_failures_do_not_suggest_attribute_chains(
    tmp_path, monkeypatch, import_statement, exception_type, missing_name
):
    """Failures inside a trusted module retain their cause without migration hints."""
    module_name = "kedro_logging_broken_formatter"
    (tmp_path / f"{module_name}.py").write_text(import_statement, encoding="utf-8")
    monkeypatch.syspath_prepend(str(tmp_path))
    monkeypatch.setenv("KEDRO_LOGGING_MODULE_ALLOWLIST", module_name)
    logging_instance = _ProjectLogging()

    with pytest.raises(ValueError, match=missing_name) as error:
        logging_instance._resolve_logging_object(f"{module_name}.Formatter")

    assert "attribute chain" not in str(error.value)
    cause = error.value.__cause__
    assert type(cause) is exception_type
    assert cause.name == missing_name
    assert str(cause) in str(error.value)


@pytest.mark.parametrize(
    ("key", "reference"),
    [
        ("stream", "ext://logging.sys.stdout"),
        pytest.param(
            "queue",
            "logging.handlers.queue.Queue",
            marks=SKIP_WITHOUT_QUEUE_CONFIG,
        ),
        pytest.param(
            "listener",
            "logging.handlers.logging.handlers.QueueListener",
            marks=SKIP_WITHOUT_QUEUE_CONFIG,
        ),
    ],
)
def test_runtime_resolution_rejects_attribute_chains(key, reference):
    """The runtime guard must block attribute walks that pass static name checks."""
    handler = {
        "class": (
            "logging.StreamHandler"
            if key == "stream"
            else "logging.handlers.QueueHandler"
        ),
        key: reference,
    }

    with pytest.raises(ValueError) as error:
        _ProjectLogging().configure({"version": 1, "handlers": {"probe": handler}})

    assert "Cannot import module" in str(error.value.__cause__)


@pytest.mark.parametrize(
    "reference", ["logging._lock", "logging._acquireLock", "logging.__builtins__"]
)
def test_private_objects_rejected_before_import(reference, mocker):
    """Even trusted modules must not expose private state or internal functions."""
    logging_instance = _ProjectLogging()
    importer = mocker.patch("kedro.framework.project.importlib.import_module")

    with pytest.raises(ValueError, match="private object"):
        logging_instance._resolve_logging_object(reference)

    importer.assert_not_called()


def test_exported_module_objects_remain_supported():
    """Module exports remain usable by options such as Rich's traceback suppress."""
    assert _ProjectLogging()._resolve_logging_object("logging.os") is os


@pytest.mark.parametrize(
    ("key", "object_name"), [("queue", "queue_factory"), ("listener", "Listener")]
)
@pytest.mark.parametrize("prefix", ["", "ext://"])
def test_untrusted_queue_references_preserve_existing_handlers(
    key, object_name, prefix, logging_probe, capsys
):
    """Reject queue references before stdlib closes or unregisters existing handlers."""
    module_name, marker = logging_probe
    logging_instance = _ProjectLogging()
    logging_instance.configure(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "existing": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                }
            },
            "root": {"handlers": ["existing"], "level": "INFO"},
        }
    )
    root = logging.getLogger()
    [existing_handler] = root.handlers
    original_config = dict(logging_instance)
    config = {
        "version": 1,
        "handlers": {
            "queued": {
                "class": "logging.handlers.QueueHandler",
                key: f"{prefix}{module_name}.{object_name}",
            }
        },
    }

    with pytest.raises(ValueError, match="is not permitted"):
        logging_instance.configure(config)

    assert existing_handler in root.handlers
    assert logging._handlers["existing"] is existing_handler
    assert logging_instance.data == original_config
    assert not marker.exists()
    assert module_name not in sys.modules
    logging.getLogger("kedro").info("STILL LOGGING")
    assert "STILL LOGGING" in capsys.readouterr().out


@pytest.mark.parametrize("stream_name", ["stdout", "stderr"])
def test_standard_streams_still_emit(stream_name, capsys):
    """Default stream exceptions still emit messages and preserve config data."""
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "stream": f"ext://sys.{stream_name}",
            }
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }
    logging_instance = _ProjectLogging()
    logging_instance.configure(config)

    logging.getLogger().info("Normal logging still works")

    captured = capsys.readouterr()
    output = captured.out if stream_name == "stdout" else captured.err
    assert "Normal logging still works" in output
    assert logging_instance.data == config


@pytest.mark.parametrize("queue_class", ["Queue", "SimpleQueue"])
@SKIP_WITHOUT_QUEUE_CONFIG
def test_standard_queue_factories_still_work(queue_class):
    """Supported queue factories and listeners produce a functioning queue handler."""
    logging_instance = _ProjectLogging()
    logging_instance.configure(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "queued": {
                    "class": "logging.handlers.QueueHandler",
                    "queue": f"queue.{queue_class}",
                    "listener": "logging.handlers.QueueListener",
                }
            },
            "root": {"handlers": ["queued"], "level": "INFO"},
        }
    )

    handler = logging.getLogger().handlers[0]
    assert isinstance(handler.queue, getattr(queue, queue_class))
    assert isinstance(handler.listener, logging.handlers.QueueListener)
    logging.getLogger().info("Queued message")
    assert handler.queue.get_nowait().getMessage() == "Queued message"


def test_trusted_external_stream_and_handler(logging_probe, monkeypatch, capsys):
    """Explicitly trusted modules may supply handlers and external objects."""
    module_name, marker = logging_probe
    monkeypatch.setenv("KEDRO_LOGGING_MODULE_ALLOWLIST", module_name)
    logging_instance = _ProjectLogging()
    logging_instance.configure(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "console": {
                    "class": f"{module_name}.Handler",
                    "stream": f"ext://{module_name}.STREAM",
                }
            },
            "root": {"handlers": ["console"], "level": "INFO"},
        }
    )

    logging.getLogger().info("Trusted custom handler")
    assert "Trusted custom handler" in capsys.readouterr().out
    assert marker.read_text() == "imported\nhandler\n"


@SKIP_WITHOUT_QUEUE_CONFIG
def test_trusted_queue_factory_and_listener(logging_probe, monkeypatch):
    """Trusted custom factories and listener classes remain usable."""
    module_name, marker = logging_probe
    monkeypatch.setenv("KEDRO_LOGGING_MODULE_ALLOWLIST", module_name)
    logging_instance = _ProjectLogging()
    logging_instance.configure(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": {
                "queued": {
                    "class": "logging.handlers.QueueHandler",
                    "queue": f"{module_name}.queue_factory",
                    "listener": f"{module_name}.Listener",
                }
            },
            "root": {"handlers": ["queued"]},
        }
    )

    handler = logging.getLogger().handlers[0]
    assert isinstance(handler.queue, queue.Queue)
    assert type(handler.listener).__module__ == module_name
    assert marker.read_text() == "imported\nfactory\n"


@pytest.mark.parametrize("filename", ["default_logging.yml", "rich_logging.yml"])
def test_shipped_configurations_still_work(filename, capsys, monkeypatch, tmp_path):
    """Both shipped configurations must continue to emit real log messages."""
    monkeypatch.chdir(tmp_path)

    config = yaml.safe_load((Path(project.__file__).parent / filename).read_text())
    _ProjectLogging().configure(config)

    logging.getLogger("kedro").info("SMOKE")
    assert "SMOKE" in capsys.readouterr().out


def test_safe_reference_inside_tuple_is_preserved():
    """Tuple traversal preserves supported references and other values."""
    config = {"args": ("ext://sys.stdout", 42)}
    assert _ProjectLogging()._validate_logging_config(config) == config


def test_namedtuple_values_survive_public_configuration(
    logging_probe, monkeypatch, capsys
):
    """Public configuration preserves field access in programmatic namedtuple values."""
    module_name, marker = logging_probe
    monkeypatch.setenv("KEDRO_LOGGING_MODULE_ALLOWLIST", module_name)
    monkeypatch.setattr(project, "LOGGING", _ProjectLogging())
    endpoint_type = namedtuple("Endpoint", ["host", "port"])
    endpoint = endpoint_type("localhost", 443)
    config = {
        "version": 1,
        "disable_existing_loggers": False,
        "handlers": {
            "console": {"class": f"{module_name}.EndpointHandler", "endpoint": endpoint}
        },
        "root": {"handlers": ["console"], "level": "INFO"},
    }

    project.configure_logging(config)

    handler = logging.getLogger().handlers[0]
    assert handler.endpoint is endpoint
    assert handler.address == ("localhost", 443)
    assert project.LOGGING["handlers"]["console"]["endpoint"] is endpoint
    assert marker.read_text() == "imported\nhandler\n"
    logging.getLogger().info("Namedtuple handler")
    assert "Namedtuple handler" in capsys.readouterr().out


@pytest.mark.parametrize(
    "value", ["ext://os.path", "cfg://target", UserDict({"()": "os.system"})]
)
def test_namedtuple_contents_are_still_validated(value):
    """Preserving a namedtuple must not hide nested forbidden configuration."""
    options_type = namedtuple("Options", ["value"])

    with pytest.raises(ValueError):
        _ProjectLogging()._validate_logging_config({"options": options_type(value)})


def test_project_logging_mapping_can_be_reconfigured(capsys):
    """The ParallelRunner handoff validates LOGGING and stores a plain config dict."""
    config = UserDict(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "handlers": UserDict(
                {
                    "console": UserDict(
                        {"class": "logging.StreamHandler", "stream": "ext://sys.stdout"}
                    )
                }
            ),
            "root": {"handlers": ["console"], "level": "INFO"},
        }
    )
    project.configure_logging(config)
    project.configure_logging(project.LOGGING)

    assert type(project.LOGGING.data) is dict
    assert type(project.LOGGING["handlers"]) is dict
    assert type(project.LOGGING["handlers"]["console"]) is dict
    assert project.LOGGING.data == config
    logging.getLogger().info("Reconfigured mapping")
    assert "Reconfigured mapping" in capsys.readouterr().out


def test_standard_formatter_and_handler_connections_still_work(capsys, mocker):
    """Handler and formatter identifiers connect real components without cfg://."""
    logging_instance = _ProjectLogging()
    resolve_formatter = mocker.spy(logging.config, "_resolve")
    logging_instance.configure(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {
                "plain": {
                    "class": "logging.Formatter",
                    "format": "FORMATTED: %(message)s",
                }
            },
            "handlers": {
                "console": {
                    "class": "logging.StreamHandler",
                    "stream": "ext://sys.stdout",
                    "formatter": "plain",
                },
                "memory": {
                    "class": "logging.handlers.MemoryHandler",
                    "capacity": 1,
                    "target": "console",
                },
            },
            "root": {"handlers": ["memory"], "level": "INFO"},
        }
    )

    logging.getLogger().info("Buffered message")
    assert "FORMATTED: Buffered message" in capsys.readouterr().out
    resolve_formatter.assert_called_once_with("logging.Formatter")
    assert resolve_formatter.spy_return is logging.Formatter


@pytest.mark.parametrize(
    "vector",
    [
        "ext",
        "cfg",
        pytest.param(
            "private_queue",
            marks=SKIP_WITHOUT_QUEUE_CONFIG,
        ),
    ],
)
def test_fresh_startup_rejects_before_execution(
    vector, logging_probe, tmp_path, monkeypatch
):
    """Fresh startup rejects unsafe references, including a lock-taking queue factory."""
    module_name, marker = logging_probe
    handler = {"class": "logging.StreamHandler"}
    config = {"version": 1, "handlers": {"console": handler}}
    if vector == "ext":
        handler["stream"] = f"ext://{module_name}.STREAM"
    elif vector == "cfg":
        handler.update(
            {
                "class": "cfg://target",
                "args": [
                    sys.executable,
                    "-c",
                    f"from pathlib import Path; Path({str(marker)!r}).touch()",
                ],
            }
        )
        config["target"] = "subprocess.Popen"
    else:
        # Isolate the lock-taking factory so a regression cannot deadlock pytest.
        handler.update(
            {"class": "logging.handlers.QueueHandler", "queue": "logging._acquireLock"}
        )
    config_path = tmp_path / "logging.yml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    monkeypatch.setenv("KEDRO_LOGGING_CONFIG", str(config_path))
    monkeypatch.delenv("KEDRO_LOGGING_MODULE_ALLOWLIST", raising=False)
    monkeypatch.setenv(
        "PYTHONPATH",
        os.pathsep.join([str(Path(__file__).resolve().parents[3]), str(tmp_path)]),
    )

    # Only the current interpreter and a fixed import are executed by this test.
    result = subprocess.run(  # noqa: S603
        [sys.executable, "-c", "import kedro.framework.project"],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )

    assert result.returncode != 0
    assert "ValueError" in result.stderr
    expected_reason = {
        "ext": "is not permitted",
        "cfg": "'cfg://' prefix is not allowed",
        "private_queue": "private object",
    }
    assert expected_reason[vector] in result.stderr
    if vector in ("ext", "cfg"):
        assert not marker.exists()
