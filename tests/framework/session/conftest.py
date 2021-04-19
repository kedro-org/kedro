# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import pytest
import toml
import yaml
from dynaconf.validator import Validator

from kedro import __version__ as kedro_version
from kedro.config import ConfigLoader
from kedro.framework.hooks import hook_impl
from kedro.framework.hooks.manager import get_hook_manager
from kedro.framework.project import _ProjectPipelines, _ProjectSettings
from kedro.framework.session import KedroSession
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node, node
from kedro.versioning import Journal

logger = logging.getLogger(__name__)


@pytest.fixture
def mock_package_name() -> str:
    return "mock_package_name"


@pytest.fixture
def local_logging_config() -> Dict[str, Any]:
    return {
        "version": 1,
        "formatters": {
            "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {"kedro": {"level": "INFO", "handlers": ["console"]}},
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
    }


def _write_yaml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _write_toml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    toml_str = toml.dumps(config)
    filepath.write_text(toml_str)


def _assert_hook_call_record_has_expected_parameters(
    call_record: logging.LogRecord, expected_parameters: List[str]
):
    """Assert the given call record has all expected parameters."""
    for param in expected_parameters:
        assert hasattr(call_record, param)


@pytest.fixture
def local_config(tmp_path):
    cars_filepath = str(tmp_path / "cars.csv")
    boats_filepath = str(tmp_path / "boats.csv")
    return {
        "cars": {
            "type": "pandas.CSVDataSet",
            "filepath": cars_filepath,
            "save_args": {"index": False},
            "versioned": True,
        },
        "boats": {
            "type": "pandas.CSVDataSet",
            "filepath": boats_filepath,
            "versioned": True,
        },
    }


@pytest.fixture(autouse=True)
def clear_hook_manager():
    yield
    hook_manager = get_hook_manager()
    plugins = hook_manager.get_plugins()
    for plugin in plugins:
        hook_manager.unregister(plugin)


@pytest.fixture(autouse=True)
def config_dir(tmp_path, local_config, local_logging_config):
    catalog = tmp_path / "conf" / "base" / "catalog.yml"
    credentials = tmp_path / "conf" / "local" / "credentials.yml"
    logging = tmp_path / "conf" / "local" / "logging.yml"
    pyproject_toml = tmp_path / "pyproject.toml"
    _write_yaml(catalog, local_config)
    _write_yaml(credentials, {"dev_s3": "foo"})
    _write_yaml(logging, local_logging_config)
    payload = {
        "tool": {
            "kedro": {
                "project_version": kedro_version,
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
    return Pipeline(
        [
            node(identity_node, "cars", "planes", name="node1"),
            node(identity_node, "boats", "ships", name="node2"),
        ],
        tags="pipeline",
    )


class LogRecorder(logging.Handler):  # pylint: disable=abstract-method
    """Record logs received from a process-safe log listener"""

    def __init__(self):
        super().__init__()
        self.log_records = []

    def handle(self, record):
        self.log_records.append(record)


class LogsListener(QueueListener):
    """Listen to logs stream and capture log records with LogRecorder.
    """

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
    """Fixture to start the logs listener before a test and clean up after the test finishes
    """
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
        conf_catalog: Dict[str, Any],
        conf_creds: Dict[str, Any],
        feed_dict: Dict[str, Any],
        save_version: str,
        load_versions: Dict[str, str],
        run_id: str,
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
                "run_id": run_id,
            },
        )

    @hook_impl
    def before_node_run(
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: str,
        run_id: str,
    ) -> None:
        logger.info(
            "About to run node",
            extra={
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "is_async": is_async,
                "run_id": run_id,
            },
        )

    @hook_impl
    def after_node_run(
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        is_async: str,
        run_id: str,
    ) -> None:
        logger.info(
            "Ran node",
            extra={
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "outputs": outputs,
                "is_async": is_async,
                "run_id": run_id,
            },
        )

    @hook_impl
    def on_node_error(
        self,
        error: Exception,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: bool,
        run_id: str,
    ):
        logger.info(
            "Node error",
            extra={
                "error": error,
                "node": node,
                "catalog": catalog,
                "inputs": inputs,
                "is_async": is_async,
                "run_id": run_id,
            },
        )

    @hook_impl
    def before_pipeline_run(
        self, run_params: Dict[str, Any], pipeline: Pipeline, catalog: DataCatalog
    ) -> None:
        logger.info(
            "About to run pipeline",
            extra={"pipeline": pipeline, "run_params": run_params, "catalog": catalog},
        )

    @hook_impl
    def after_pipeline_run(
        self,
        run_params: Dict[str, Any],
        run_result: Dict[str, Any],
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
        run_params: Dict[str, Any],
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
    def before_dataset_loaded(self, dataset_name: str) -> None:
        logger.info("Before dataset loaded", extra={"dataset_name": dataset_name})

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
        logger.info(
            "After dataset loaded", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def before_dataset_saved(self, dataset_name: str, data: Any) -> None:
        logger.info(
            "Before dataset saved", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def after_dataset_saved(self, dataset_name: str, data: Any) -> None:
        logger.info(
            "After dataset saved", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def register_config_loader(
        self, conf_paths: Iterable[str], env: str, extra_params: Dict[str, Any]
    ) -> ConfigLoader:
        logger.info(
            "Registering config loader",
            extra={"conf_paths": conf_paths, "env": env, "extra_params": extra_params},
        )
        return ConfigLoader(conf_paths)

    @hook_impl
    def register_catalog(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]],
        load_versions: Dict[str, str],
        save_version: str,
        journal: Journal,
    ) -> DataCatalog:
        logger.info(
            "Registering catalog",
            extra={
                "catalog": catalog,
                "credentials": credentials,
                "load_versions": load_versions,
                "save_version": save_version,
                "journal": journal,
            },
        )
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version, journal
        )


@pytest.fixture(autouse=True)
def patched_validate_module(mocker):
    """Patching this so KedroSession could be created for testing purpose
    since KedroSession.create is still calling configure_project at the moment
    """
    mocker.patch("kedro.framework.project._validate_module")


@pytest.fixture
def project_hooks():
    """A set of project hook implementations that log to stdout whenever it is invoked."""
    return LoggingHooks()


@pytest.fixture(autouse=True)
def mock_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


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
        "kedro.framework.context.context.settings",
        "kedro.framework.session.session.settings",
        "kedro.framework.project.settings",
    ]:
        mocker.patch(path, mock_settings)
    return mock_settings


@pytest.fixture
def mock_settings(mocker, project_hooks):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(project_hooks,))

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_session(
    mock_settings, mock_package_name, tmp_path
):  # pylint: disable=unused-argument
    return KedroSession.create(
        mock_package_name, tmp_path, extra_params={"params:key": "value"}
    )
