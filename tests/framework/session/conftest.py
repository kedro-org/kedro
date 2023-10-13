from __future__ import annotations

import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
import toml
import yaml
from dynaconf.validator import Validator

from kedro import __version__ as kedro_version
from kedro.framework.context.context import KedroContext
from kedro.framework.hooks import hook_impl
from kedro.framework.project import (
    _ProjectPipelines,
    _ProjectSettings,
    configure_project,
)
from kedro.framework.session import KedroSession
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.pipeline.node import Node, node

logger = logging.getLogger(__name__)

MOCK_PACKAGE_NAME = "fake_package"


@pytest.fixture
def mock_package_name() -> str:
    return MOCK_PACKAGE_NAME


def _write_yaml(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _write_toml(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    toml_str = toml.dumps(config)
    filepath.write_text(toml_str)


def _assert_hook_call_record_has_expected_parameters(
    call_record: logging.LogRecord, expected_parameters: list[str]
):
    """Assert the given call record has all expected parameters."""
    for param in expected_parameters:
        assert hasattr(call_record, param)


def _assert_pipeline_equal(p: Pipeline, q: Pipeline):
    assert sorted(p.nodes) == sorted(q.nodes)


@pytest.fixture
def local_config(tmp_path):
    cars_filepath = str(tmp_path / "cars.csv")
    boats_filepath = str(tmp_path / "boats.csv")
    return {
        "cars": {
            "type": "pandas.CSVDataset",
            "filepath": cars_filepath,
            "save_args": {"index": False},
            "versioned": True,
        },
        "boats": {
            "type": "pandas.CSVDataset",
            "filepath": boats_filepath,
            "versioned": True,
        },
    }


@pytest.fixture(autouse=True)
def config_dir(tmp_path, local_config):
    catalog = tmp_path / "conf" / "base" / "catalog.yml"
    credentials = tmp_path / "conf" / "local" / "credentials.yml"
    pyproject_toml = tmp_path / "pyproject.toml"
    _write_yaml(catalog, local_config)
    _write_yaml(credentials, {"dev_s3": "foo"})
    payload = {
        "tool": {
            "kedro": {
                "kedro_init_version": kedro_version,
                "project_name": "test hooks",
                "package_name": "test_hooks",
            }
        }
    }
    _write_toml(pyproject_toml, payload)


def identity_node(x: str):
    return x


def assert_exceptions_equal(e1: Exception, e2: Exception):
    assert isinstance(e1, type(e2)) and str(e1) == str(e2)


@pytest.fixture
def dummy_dataframe() -> pd.DataFrame:
    return pd.DataFrame({"test": [1, 2]})


@pytest.fixture
def mock_pipeline() -> Pipeline:
    return modular_pipeline(
        [
            node(identity_node, "cars", "planes", name="node1"),
            node(identity_node, "boats", "ships", name="node2"),
        ],
        tags="pipeline",
    )


class LogRecorder(logging.Handler):
    """Record logs received from a process-safe log listener"""

    def __init__(self):
        super().__init__()
        self.log_records = []

    def handle(self, record):
        self.log_records.append(record)


class LogsListener(QueueListener):
    """Listen to logs stream and capture log records with LogRecorder."""

    def __init__(self):
        # Queue where logs will be sent to
        queue = Queue()

        # Tells python logging to send logs to this queue
        self.log_handler = QueueHandler(queue)
        logger.addHandler(self.log_handler)

        # The listener listens to new logs on the queue and saves it to the recorder
        self.log_recorder = LogRecorder()
        super().__init__(queue, self.log_recorder)

    @property
    def logs(self):
        return self.log_recorder.log_records


@pytest.fixture
def logs_listener():
    """Fixture to start the logs listener before a test and clean up after the test finishes"""
    listener = LogsListener()
    listener.start()
    yield listener
    logger.removeHandler(listener.log_handler)
    listener.stop()


class LoggingHooks:
    """A set of test hooks that only log information when invoked"""

    @hook_impl
    def after_catalog_created(
        self,
        catalog: DataCatalog,
        conf_catalog: dict[str, Any],
        conf_creds: dict[str, Any],
        feed_dict: dict[str, Any],
        save_version: str,
        load_versions: dict[str, str],
    ):
        logger.info(
            "Catalog created",
            extra={
                "catalog": catalog,
                "conf_catalog": conf_catalog,
                "conf_creds": conf_creds,
                "feed_dict": feed_dict,
                "save_version": save_version,
                "load_versions": load_versions,
            },
        )

    @hook_impl
    def before_node_run(
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: dict[str, Any],
        is_async: str,
        session_id: str,
    ) -> None:
        logger.info(
            "About to run node",
            extra={
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "is_async": is_async,
                "session_id": session_id,
            },
        )

    @hook_impl
    def after_node_run(
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        is_async: str,
        session_id: str,
    ) -> None:
        logger.info(
            "Ran node",
            extra={
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "outputs": outputs,
                "is_async": is_async,
                "session_id": session_id,
            },
        )

    @hook_impl
    def on_node_error(
        self,
        error: Exception,
        node: Node,
        catalog: DataCatalog,
        inputs: dict[str, Any],
        is_async: bool,
        session_id: str,
    ):
        logger.info(
            "Node error",
            extra={
                "error": error,
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "is_async": is_async,
                "session_id": session_id,
            },
        )

    @hook_impl
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Pipeline, catalog: DataCatalog
    ) -> None:
        logger.info(
            "About to run pipeline",
            extra={"pipeline": pipeline, "run_params": run_params, "catalog": catalog},
        )

    @hook_impl
    def after_pipeline_run(
        self,
        run_params: dict[str, Any],
        run_result: dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        logger.info(
            "Ran pipeline",
            extra={
                "pipeline": pipeline,
                "run_params": run_params,
                "run_result": run_result,
                "catalog": catalog,
            },
        )

    @hook_impl
    def on_pipeline_error(
        self,
        error: Exception,
        run_params: dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        logger.info(
            "Pipeline error",
            extra={
                "error": error,
                "run_params": run_params,
                "pipeline": pipeline,
                "catalog": catalog,
            },
        )

    @hook_impl
    def before_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        logger.info(
            "Before dataset loaded", extra={"dataset_name": dataset_name, "node": node}
        )

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any, node: Node) -> None:
        logger.info(
            "After dataset loaded",
            extra={"dataset_name": dataset_name, "data": data, "node": node},
        )

    @hook_impl
    def before_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        logger.info(
            "Before dataset saved",
            extra={"dataset_name": dataset_name, "data": data, "node": node},
        )

    @hook_impl
    def after_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        logger.info(
            "After dataset saved",
            extra={"dataset_name": dataset_name, "data": data, "node": node},
        )

    @hook_impl
    def after_context_created(self, context: KedroContext) -> None:
        logger.info("After context created", extra={"context": context})


@pytest.fixture
def project_hooks():
    """A set of project hook implementations that log to stdout whenever it is invoked."""
    return LoggingHooks()


@pytest.fixture(autouse=True)
def mock_pipelines(mocker, mock_pipeline):
    def mock_register_pipelines():
        return {
            "__default__": mock_pipeline,
            "pipe": mock_pipeline,
        }

    mocker.patch.object(
        _ProjectPipelines,
        "_get_pipelines_registry_callable",
        return_value=mock_register_pipelines,
    )
    return mock_register_pipelines()


def _mock_imported_settings_paths(mocker, mock_settings):
    for path in [
        "kedro.framework.session.session.settings",
        "kedro.framework.project.settings",
        "kedro.runner.parallel_runner.settings",
    ]:
        mocker.patch(path, mock_settings)
    return mock_settings


@pytest.fixture
def mock_settings(mocker, project_hooks):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(project_hooks,))

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_session(mock_settings, mock_package_name, tmp_path):
    configure_project(mock_package_name)
    session = KedroSession.create(
        mock_package_name, tmp_path, extra_params={"params:key": "value"}
    )
    yield session
    session.close()


@pytest.fixture(autouse=True)
def mock_validate_settings(mocker):
    # KedroSession eagerly validates that a project's settings.py is correct by
    # importing it. settings.py does not actually exists as part of this test suite
    # since we are testing session in isolation, so the validation is patched.
    mocker.patch("kedro.framework.session.session.validate_settings")
