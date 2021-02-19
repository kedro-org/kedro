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
# pylint: disable=too-many-lines
import logging
import re
import sys
from collections import namedtuple
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import pandas as pd
import pytest
import toml
import yaml

from kedro import __version__ as kedro_version
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext, KedroContextError
from kedro.framework.context.context import _convert_paths_to_absolute_posix
from kedro.framework.hooks import hook_impl
from kedro.framework.hooks.manager import get_hook_manager
from kedro.framework.project import Validator, _ProjectSettings, settings
from kedro.framework.session import KedroSession
from kedro.framework.session.session import _register_all_project_hooks
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node, node
from kedro.runner import ParallelRunner
from kedro.versioning import Journal

SKIP_ON_WINDOWS = pytest.mark.skipif(
    sys.platform.startswith("win"), reason="Due to bug in parallel runner"
)


@pytest.fixture
def local_logging_config():
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


def identity(x: str):
    return x


def broken_node():
    raise ValueError("broken")


def assert_exceptions_equal(e1: Exception, e2: Exception):
    assert isinstance(e1, type(e2)) and str(e1) == str(e2)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"test": [1, 2]})


CONTEXT_PIPELINE = Pipeline(
    [
        node(identity, "cars", "planes", name="node1"),
        node(identity, "boats", "ships", name="node2"),
    ],
    tags="pipeline",
)

BROKEN_PIPELINE = Pipeline(
    [
        node(broken_node, None, "A", name="node1"),
        node(broken_node, None, "B", name="node2"),
    ],
    tags="pipeline",
)

MockDistInfo = namedtuple("Distinfo", ["project_name", "version"])


class LoggingHooks:
    """A set of test hooks that only log information when invoked.
    Use a log queue to properly test log messages written by hooks invoked by ParallelRunner.
    """

    handler_name = "hooks_handler"

    def __init__(self, logs_queue):
        self.logger = logging.getLogger("hooks_handler")
        self.logger.handlers = []

        self.queue = logs_queue
        self.queue_handler = QueueHandler(self.queue)
        # We need this queue listener to prevent pytest from hanging on Windows.
        self.queue_listener = QueueListener(self.queue)
        self.logger.addHandler(self.queue_handler)

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
        self.logger.info(
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
        self.logger.info(
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
        self.logger.info(
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
        self.logger.info(
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
        self.logger.info(
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
        self.logger.info(
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
        self.logger.info(
            "Pipeline error",
            extra={
                "error": error,
                "run_params": run_params,
                "pipeline": pipeline,
                "catalog": catalog,
            },
        )

    @hook_impl
    def before_dataset_loaded(self, dataset_name: str,) -> None:
        self.logger.info("Before dataset loaded", extra={"dataset_name": dataset_name})

    @hook_impl
    def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
        self.logger.info(
            "After dataset loaded", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def before_dataset_saved(self, dataset_name: str, data: Any) -> None:
        self.logger.info(
            "Before dataset saved", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def after_dataset_saved(self, dataset_name: str, data: Any) -> None:
        self.logger.info(
            "After dataset saved", extra={"dataset_name": dataset_name, "data": data}
        )

    @hook_impl
    def register_pipelines(self) -> Dict[str, Pipeline]:
        self.logger.info("Registering pipelines")
        return {"__default__": CONTEXT_PIPELINE, "de": CONTEXT_PIPELINE}

    @hook_impl
    def register_config_loader(
        self, conf_paths: Iterable[str], env: str, extra_params: Dict[str, Any]
    ) -> ConfigLoader:
        self.logger.info(
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
        self.logger.info(
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


class DuplicateHooks:
    @hook_impl
    def register_pipelines(self) -> Dict[str, Pipeline]:
        return {"__default__": CONTEXT_PIPELINE, "pipe": CONTEXT_PIPELINE}


class MockDatasetReplacement:  # pylint: disable=too-few-public-methods
    pass


class RequiredHooks:
    """Mandatory registration hooks"""

    @hook_impl
    def register_pipelines(self) -> Dict[str, Pipeline]:
        return {"__default__": CONTEXT_PIPELINE}

    @hook_impl
    def register_config_loader(self, conf_paths: Iterable[str]) -> ConfigLoader:
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
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version, journal
        )


class BrokenConfigLoaderHooks(RequiredHooks):
    @hook_impl
    def register_config_loader(self, conf_paths):
        return None


class BrokenCatalogHooks(RequiredHooks):
    @hook_impl
    def register_catalog(
        self, catalog, credentials, load_versions, save_version, journal,
    ):
        return None


class BeforeNodeRunHook(RequiredHooks):
    """Should overwrite the `cars` dataset"""

    @hook_impl
    def before_node_run(self, node: Node):
        return {"cars": MockDatasetReplacement()} if node.name == "node1" else None


class BrokenBeforeNodeRunHook(RequiredHooks):
    """Broken since `before_node_run` doesn't return a dictionary"""

    @hook_impl
    def before_node_run(self):
        return MockDatasetReplacement()


@pytest.fixture
def logs_queue():
    return Queue()


@pytest.fixture
def logging_hooks(logs_queue):
    return LoggingHooks(logs_queue)


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


MOCK_PACKAGE_NAME = "mock_package_name"


@pytest.fixture
def mock_broken_pipeline(mocker):
    mocker.patch.object(
        KedroContext, "_get_pipelines", return_value={"__default__": BROKEN_PIPELINE}
    )


def _mock_imported_settings_paths(mocker, mock_settings):
    for path in [
        "kedro.framework.context.context.settings",
        "kedro.framework.session.session.settings",
        "kedro.framework.project.settings",
    ]:
        mocker.patch(path, mock_settings)
    return mock_settings


def _mock_settings_with_hooks(mocker, hooks):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=hooks)

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_with_logging_hooks(mocker, logging_hooks):
    return _mock_settings_with_hooks(mocker, hooks=(logging_hooks,))


@pytest.fixture
def mock_settings_duplicate_hooks(mocker, logging_hooks):
    return _mock_settings_with_hooks(mocker, hooks=(logging_hooks, DuplicateHooks(),))


@pytest.fixture
def mock_settings_before_node_run_hooks(mocker, logging_hooks):
    return _mock_settings_with_hooks(
        mocker, hooks=(logging_hooks, BeforeNodeRunHook(),)
    )


@pytest.fixture
def mock_settings_broken_before_node_run_hooks(mocker, logging_hooks):
    return _mock_settings_with_hooks(
        mocker, hooks=(logging_hooks, BrokenBeforeNodeRunHook(),)
    )


@pytest.fixture
def mock_settings_broken_config_loader_hooks(mocker):
    return _mock_settings_with_hooks(mocker, hooks=(BrokenConfigLoaderHooks(),))


@pytest.fixture
def mock_settings_broken_catalog_hooks(mocker):
    return _mock_settings_with_hooks(mocker, hooks=(BrokenCatalogHooks(),))


@pytest.fixture
def naughty_plugin():
    return MockDistInfo("test-project-a", "0.1")


@pytest.fixture
def mock_settings_with_disabled_hooks(mocker, logging_hooks, naughty_plugin):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(logging_hooks,))
        _DISABLE_HOOKS_FOR_PLUGINS = Validator(
            "DISABLE_HOOKS_FOR_PLUGINS", default=(naughty_plugin.project_name,)
        )

    _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_session_with_hooks(
    tmp_path, mock_settings_with_logging_hooks, logging_hooks
):  # pylint: disable=unused-argument
    logging_hooks.queue_listener.start()
    yield KedroSession.create(
        MOCK_PACKAGE_NAME, tmp_path, extra_params={"params:key": "value"}
    )
    logging_hooks.queue_listener.stop()


class TestKedroSessionHooks:
    def test_assert_register_hooks(self, request, logging_hooks):
        hook_manager = get_hook_manager()
        assert not hook_manager.is_registered(logging_hooks)

        # call the fixture to construct the session
        request.getfixturevalue("mock_session_with_hooks")

        assert hook_manager.is_registered(logging_hooks)

    @pytest.mark.usefixtures("mock_session_with_hooks")
    def test_calling_register_hooks_twice(self, logging_hooks):
        """Calling hook registration multiple times should not raise"""
        hook_manager = get_hook_manager()

        # hooks already registered when fixture 'mock_session_with_hooks' was called
        assert hook_manager.is_registered(logging_hooks)
        _register_all_project_hooks(hook_manager)
        _register_all_project_hooks(hook_manager)
        assert hook_manager.is_registered(logging_hooks)

    @pytest.mark.parametrize("num_plugins", [0, 1])
    def test_hooks_registered_when_session_created(
        self, mocker, request, caplog, logging_hooks, num_plugins
    ):
        hook_manager = get_hook_manager()
        assert not hook_manager.get_plugins()

        load_setuptools_entrypoints = mocker.patch.object(
            hook_manager, "load_setuptools_entrypoints", return_value=num_plugins
        )
        distinfo = [("plugin_obj_1", MockDistInfo("test-project-a", "0.1"))]
        list_distinfo_mock = mocker.patch.object(
            hook_manager, "list_plugin_distinfo", return_value=distinfo
        )

        # call a fixture which creates a session
        request.getfixturevalue("mock_session_with_hooks")
        assert hook_manager.is_registered(logging_hooks)

        load_setuptools_entrypoints.assert_called_once_with("kedro.hooks")
        list_distinfo_mock.assert_called_once_with()

        if num_plugins:
            log_messages = [record.getMessage() for record in caplog.records]
            plugin = f"{distinfo[0][1].project_name}-{distinfo[0][1].version}"
            expected_msg = (
                f"Registered hooks from {num_plugins} installed plugin(s): {plugin}"
            )
            assert expected_msg in log_messages

    @pytest.mark.usefixtures("mock_settings_with_disabled_hooks")
    def test_disabling_auto_discovered_hooks(
        self, mocker, caplog, logging_hooks, tmp_path
    ):
        hook_manager = get_hook_manager()
        assert not hook_manager.get_plugins()

        # pretend that some setuptools plugins were autodiscovered
        naughty_plugin = MockDistInfo("test-project-a", "0.1")
        good_plugin = MockDistInfo("test-project-b", "0.2")

        distinfo = [("plugin_obj_1", naughty_plugin), ("plugin_obj_2", good_plugin)]
        list_distinfo_mock = mocker.patch.object(
            hook_manager, "list_plugin_distinfo", return_value=distinfo
        )
        mocker.patch.object(
            hook_manager, "load_setuptools_entrypoints", return_value=len(distinfo)
        )
        unregister_mock = mocker.patch.object(hook_manager, "unregister")

        logging_hooks.queue_listener.start()
        KedroSession.create(
            MOCK_PACKAGE_NAME, tmp_path, extra_params={"params:key": "value"}
        )
        logging_hooks.queue_listener.stop()
        list_distinfo_mock.assert_called_once_with()
        unregister_mock.assert_called_once_with(plugin=distinfo[0][0])

        # check the logs
        log_messages = [record.getMessage() for record in caplog.records]
        expected_msg = (
            f"Registered hooks from 1 installed plugin(s): "
            f"{good_plugin.project_name}-{good_plugin.version}"
        )
        assert expected_msg in log_messages

        expected_msg = (
            f"Hooks are disabled for plugin(s): "
            f"{naughty_plugin.project_name}-{naughty_plugin.version}"
        )
        assert expected_msg in log_messages

    def test_after_catalog_created_hook(self, mocker, caplog, mock_session_with_hooks):
        context = mock_session_with_hooks.load_context()
        fake_run_id = mocker.sentinel.fake_run_id
        mocker.patch.object(context, "_get_run_id", return_value=fake_run_id)

        project_path = context.project_path
        catalog = context.catalog
        config_loader = context.config_loader

        relevant_records = [
            r
            for r in caplog.records
            if r.name == LoggingHooks.handler_name
            and r.getMessage() == "Catalog created"
        ]
        assert len(relevant_records) == 1
        record = relevant_records[0]
        assert record.catalog is catalog
        assert record.conf_creds == config_loader.get("credentials*")
        assert record.conf_catalog == _convert_paths_to_absolute_posix(
            project_path=project_path, conf_dictionary=config_loader.get("catalog*"),
        )
        # save_version is only passed during a run, not on the property getter
        assert record.save_version is None
        assert record.load_versions is None
        assert record.run_id is fake_run_id

    def test_before_and_after_pipeline_run_hooks(
        self, caplog, mock_session_with_hooks, dummy_dataframe
    ):
        context = mock_session_with_hooks.load_context()
        catalog = context.catalog
        default_pipeline = context.pipeline
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)
        mock_session_with_hooks.run()

        # test before pipeline run hook
        before_pipeline_run_calls = [
            record
            for record in caplog.records
            if record.funcName == "before_pipeline_run"
        ]
        assert len(before_pipeline_run_calls) == 1
        call_record = before_pipeline_run_calls[0]
        assert call_record.pipeline is default_pipeline
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["pipeline", "catalog", "run_params"]
        )

        # test after pipeline run hook
        after_pipeline_run_calls = [
            record
            for record in caplog.records
            if record.funcName == "after_pipeline_run"
        ]
        assert len(after_pipeline_run_calls) == 1
        call_record = after_pipeline_run_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["pipeline", "catalog", "run_params"]
        )
        assert call_record.pipeline is default_pipeline

    @pytest.mark.usefixtures("mock_broken_pipeline")
    def test_on_pipeline_error_hook(self, caplog, mock_session_with_hooks):
        with pytest.raises(ValueError, match="broken"):
            mock_session_with_hooks.run()

        on_pipeline_error_calls = [
            record
            for record in caplog.records
            if record.funcName == "on_pipeline_error"
        ]
        assert len(on_pipeline_error_calls) == 1
        call_record = on_pipeline_error_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["error", "run_params", "pipeline", "catalog"]
        )
        expected_error = ValueError("broken")
        assert_exceptions_equal(call_record.error, expected_error)

    @pytest.mark.usefixtures("mock_broken_pipeline")
    def test_on_node_error_hook_sequential_runner(
        self, caplog, mock_session_with_hooks
    ):
        with pytest.raises(ValueError, match="broken"):
            mock_session_with_hooks.run(node_names=["node1"])

        on_node_error_calls = [
            record for record in caplog.records if record.funcName == "on_node_error"
        ]
        assert len(on_node_error_calls) == 1
        call_record = on_node_error_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["error", "node", "catalog", "inputs", "is_async", "run_id"]
        )
        expected_error = ValueError("broken")
        assert_exceptions_equal(call_record.error, expected_error)

    def test_before_and_after_node_run_hooks_sequential_runner(
        self, caplog, mock_session_with_hooks, dummy_dataframe
    ):
        context = mock_session_with_hooks.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        mock_session_with_hooks.run(node_names=["node1"])

        # test before node run hook
        before_node_run_calls = [
            record for record in caplog.records if record.funcName == "before_node_run"
        ]
        assert len(before_node_run_calls) == 1
        call_record = before_node_run_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["node", "catalog", "inputs", "is_async", "run_id"]
        )
        # sanity check a couple of important parameters
        assert call_record.inputs["cars"].to_dict() == dummy_dataframe.to_dict()
        assert call_record.run_id == mock_session_with_hooks.session_id

        # test after node run hook
        after_node_run_calls = [
            record for record in caplog.records if record.funcName == "after_node_run"
        ]
        assert len(after_node_run_calls) == 1
        call_record = after_node_run_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["node", "catalog", "inputs", "outputs", "is_async", "run_id"]
        )
        # sanity check a couple of important parameters
        assert call_record.outputs["planes"].to_dict() == dummy_dataframe.to_dict()
        assert call_record.run_id == mock_session_with_hooks.session_id

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_broken_pipeline", "mock_settings_with_logging_hooks")
    def test_on_node_error_hook_parallel_runner(self, tmp_path, logging_hooks):
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        log_records = []

        class LogHandler(logging.Handler):  # pylint: disable=abstract-method
            def handle(self, record):
                log_records.append(record)

        logs_queue_listener = QueueListener(logging_hooks.queue, LogHandler())
        logs_queue_listener.start()

        with pytest.raises(ValueError, match="broken"):
            try:
                session.run(
                    runner=ParallelRunner(max_workers=2), node_names=["node1", "node2"]
                )
            finally:
                logs_queue_listener.stop()

        on_node_error_records = [
            r for r in log_records if r.funcName == "on_node_error"
        ]
        assert len(on_node_error_records) == 2

        for call_record in on_node_error_records:
            _assert_hook_call_record_has_expected_parameters(
                call_record,
                ["error", "node", "catalog", "inputs", "is_async", "run_id"],
            )
            expected_error = ValueError("broken")
            assert_exceptions_equal(call_record.error, expected_error)

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_settings_with_logging_hooks")
    def test_before_and_after_node_run_hooks_parallel_runner(
        self, tmp_path, logging_hooks, dummy_dataframe
    ):
        log_records = []
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        class LogHandler(logging.Handler):  # pylint: disable=abstract-method
            def handle(self, record):
                log_records.append(record)

        logs_queue_listener = QueueListener(logging_hooks.queue, LogHandler())
        logs_queue_listener.start()

        try:
            session.run(runner=ParallelRunner(), node_names=["node1", "node2"])
        finally:
            logs_queue_listener.stop()

        before_node_run_log_records = [
            r for r in log_records if r.funcName == "before_node_run"
        ]
        assert len(before_node_run_log_records) == 2
        for record in before_node_run_log_records:
            assert record.getMessage() == "About to run node"
            assert record.node.name in ["node1", "node2"]
            assert set(record.inputs.keys()) <= {"cars", "boats"}

        after_node_run_log_records = [
            r for r in log_records if r.funcName == "after_node_run"
        ]
        assert len(after_node_run_log_records) == 2
        for record in after_node_run_log_records:
            assert record.getMessage() == "Ran node"
            assert record.node.name in ["node1", "node2"]
            assert set(record.outputs.keys()) <= {"planes", "ships"}

    def test_before_and_after_dataset_loaded_hooks_sequential_runner(
        self, caplog, mock_session_with_hooks, dummy_dataframe
    ):
        context = mock_session_with_hooks.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        mock_session_with_hooks.run(node_names=["node1"])

        # test before dataset loaded hook
        before_dataset_loaded_calls = [
            record
            for record in caplog.records
            if record.funcName == "before_dataset_loaded"
        ]
        assert len(before_dataset_loaded_calls) == 1
        call_record = before_dataset_loaded_calls[0]
        _assert_hook_call_record_has_expected_parameters(call_record, ["dataset_name"])

        assert call_record.dataset_name == "cars"

        # test after dataset loaded hook
        after_dataset_loaded_calls = [
            record
            for record in caplog.records
            if record.funcName == "after_dataset_loaded"
        ]
        assert len(after_dataset_loaded_calls) == 1
        call_record = after_dataset_loaded_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["dataset_name", "data"]
        )

        assert call_record.dataset_name == "cars"
        pd.testing.assert_frame_equal(call_record.data, dummy_dataframe)

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_settings_with_logging_hooks")
    def test_before_and_after_dataset_loaded_hooks_parallel_runner(
        self, tmp_path, logging_hooks, dummy_dataframe
    ):
        log_records = []
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        class LogHandler(logging.Handler):  # pylint: disable=abstract-method
            def handle(self, record):
                log_records.append(record)

        logs_queue_listener = QueueListener(logging_hooks.queue, LogHandler())
        logs_queue_listener.start()
        try:
            session.run(runner=ParallelRunner(), node_names=["node1", "node2"])
        finally:
            logs_queue_listener.stop()

        before_dataset_loaded_log_records = [
            r for r in log_records if r.funcName == "before_dataset_loaded"
        ]
        assert len(before_dataset_loaded_log_records) == 2
        for record in before_dataset_loaded_log_records:
            assert record.getMessage() == "Before dataset loaded"
            assert record.dataset_name in ["cars", "boats"]

        after_dataset_loaded_log_records = [
            r for r in log_records if r.funcName == "after_dataset_loaded"
        ]
        assert len(after_dataset_loaded_log_records) == 2
        for record in after_dataset_loaded_log_records:
            assert record.getMessage() == "After dataset loaded"
            assert record.dataset_name in ["cars", "boats"]
            pd.testing.assert_frame_equal(record.data, dummy_dataframe)

    def test_before_and_after_dataset_saved_hooks_sequential_runner(
        self, caplog, mock_session_with_hooks, dummy_dataframe
    ):
        context = mock_session_with_hooks.load_context()
        context.catalog.save("cars", dummy_dataframe)
        mock_session_with_hooks.run(node_names=["node1"])

        # test before dataset saved hook
        before_dataset_saved_calls = [
            record
            for record in caplog.records
            if record.funcName == "before_dataset_saved"
        ]
        assert len(before_dataset_saved_calls) == 1
        call_record = before_dataset_saved_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["dataset_name", "data"]
        )

        assert call_record.dataset_name == "planes"
        assert call_record.data.to_dict() == dummy_dataframe.to_dict()

        # test after dataset saved hook
        after_dataset_saved_calls = [
            record
            for record in caplog.records
            if record.funcName == "after_dataset_saved"
        ]
        assert len(after_dataset_saved_calls) == 1
        call_record = after_dataset_saved_calls[0]
        _assert_hook_call_record_has_expected_parameters(
            call_record, ["dataset_name", "data"]
        )

        assert call_record.dataset_name == "planes"
        assert call_record.data.to_dict() == dummy_dataframe.to_dict()

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_settings_with_logging_hooks")
    def test_before_and_after_dataset_saved_hooks_parallel_runner(
        self, tmp_path, logging_hooks, dummy_dataframe
    ):
        log_records = []
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        class LogHandler(logging.Handler):  # pylint: disable=abstract-method
            def handle(self, record):
                log_records.append(record)

        logs_queue_listener = QueueListener(logging_hooks.queue, LogHandler())
        logs_queue_listener.start()
        try:
            session.run(runner=ParallelRunner(), node_names=["node1", "node2"])
        finally:
            logs_queue_listener.stop()

        before_dataset_saved_log_records = [
            r for r in log_records if r.funcName == "before_dataset_saved"
        ]
        assert len(before_dataset_saved_log_records) == 2
        for record in before_dataset_saved_log_records:
            assert record.getMessage() == "Before dataset saved"
            assert record.dataset_name in ["planes", "ships"]
            assert record.data.to_dict() == dummy_dataframe.to_dict()

        after_dataset_saved_log_records = [
            r for r in log_records if r.funcName == "after_dataset_saved"
        ]
        assert len(after_dataset_saved_log_records) == 2
        for record in after_dataset_saved_log_records:
            assert record.getMessage() == "After dataset saved"
            assert record.dataset_name in ["planes", "ships"]
            assert record.data.to_dict() == dummy_dataframe.to_dict()


class TestBeforeNodeRunHookWithInputUpdates:
    """Test the behavior of `before_node_run_hook` when updating node inputs"""

    @pytest.mark.usefixtures("mock_settings_before_node_run_hooks")
    def test_correct_input_update(self, tmp_path, dummy_dataframe):

        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        result = session.run()
        assert isinstance(result["planes"], MockDatasetReplacement)
        assert isinstance(result["ships"], pd.DataFrame)

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_settings_before_node_run_hooks")
    def test_correct_input_update_parallel(self, tmp_path, dummy_dataframe):
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        result = session.run(runner=ParallelRunner())
        assert isinstance(result["planes"], MockDatasetReplacement)
        assert isinstance(result["ships"], pd.DataFrame)

    @pytest.mark.usefixtures("mock_settings_broken_before_node_run_hooks")
    def test_broken_input_update(self, tmp_path, dummy_dataframe):
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        pattern = (
            "`before_node_run` must return either None or a dictionary "
            "mapping dataset names to updated values, got `MockDatasetReplacement`"
        )
        with pytest.raises(TypeError, match=re.escape(pattern)):
            session.run()

    @SKIP_ON_WINDOWS
    @pytest.mark.usefixtures("mock_settings_broken_before_node_run_hooks")
    def test_broken_input_update_parallel(self, tmp_path, dummy_dataframe):
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        pattern = (
            "`before_node_run` must return either None or a dictionary "
            "mapping dataset names to updated values, got `MockDatasetReplacement`"
        )
        with pytest.raises(TypeError, match=re.escape(pattern)):
            session.run(runner=ParallelRunner())


class TestRegistrationHooks:
    def test_register_pipelines_is_called(
        self, mock_session_with_hooks, dummy_dataframe, caplog
    ):
        context = mock_session_with_hooks.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)
        mock_session_with_hooks.run()

        register_pipelines_calls = [
            record
            for record in caplog.records
            if record.funcName == "register_pipelines"
        ]
        assert len(register_pipelines_calls) == 1
        call_record = register_pipelines_calls[0]
        _assert_hook_call_record_has_expected_parameters(call_record, [])

        expected_pipelines = {"__default__": CONTEXT_PIPELINE, "de": CONTEXT_PIPELINE}
        assert context.pipelines == expected_pipelines

    @pytest.mark.usefixtures("mock_settings_duplicate_hooks")
    def test_register_pipelines_with_duplicate_entries(self, tmp_path, dummy_dataframe):
        session = KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)
        context = session.load_context()
        catalog = context.catalog
        catalog.save("cars", dummy_dataframe)
        catalog.save("boats", dummy_dataframe)

        pattern = (
            "Found duplicate pipeline entries. The following "
            "will be overwritten: __default__"
        )
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            session.run()

        # check that all pipeline dictionaries merged together correctly
        expected_pipelines = {
            key: CONTEXT_PIPELINE for key in ("__default__", "de", "pipe")
        }
        assert context.pipelines == expected_pipelines

    def test_register_config_loader_is_called(self, mock_session_with_hooks, caplog):
        context = mock_session_with_hooks.load_context()
        _ = context.config_loader

        relevant_records = [
            r for r in caplog.records if r.name == LoggingHooks.handler_name
        ]
        assert len(relevant_records) == 1
        record = relevant_records[0]
        assert record.getMessage() == "Registering config loader"

        expected_conf_paths = [
            str(context.project_path / settings.CONF_ROOT / "base"),
            str(context.project_path / settings.CONF_ROOT / "local"),
        ]
        assert record.conf_paths == expected_conf_paths
        assert record.env == context.env
        assert record.extra_params == {"params:key": "value"}

    def test_register_catalog_is_called(self, mock_session_with_hooks, caplog):
        context = mock_session_with_hooks.load_context()
        catalog = context.catalog
        assert isinstance(catalog, DataCatalog)

        relevant_records = [
            r
            for r in caplog.records
            if r.name == LoggingHooks.handler_name
            and r.getMessage() == "Registering catalog"
        ]
        assert len(relevant_records) == 1

        record = relevant_records[0]
        assert record.catalog.keys() == {"cars", "boats"}
        assert record.credentials == {"dev_s3": "foo"}
        # save_version is only passed during a run, not on the property getter
        assert record.save_version is None
        assert record.load_versions is None
        assert record.journal is None

    @pytest.mark.usefixtures("mock_settings_broken_config_loader_hooks")
    def test_broken_register_config_loader_hook(self, tmp_path):
        pattern = "Expected an instance of `ConfigLoader`, got `NoneType` instead."
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            KedroSession.create(MOCK_PACKAGE_NAME, tmp_path)

    @pytest.mark.usefixtures("mock_settings_broken_catalog_hooks")
    def test_broken_register_catalog_hook(self, tmp_path):
        pattern = "Expected an instance of `DataCatalog`, got `NoneType` instead."
        with KedroSession.create(MOCK_PACKAGE_NAME, tmp_path) as session:
            context = session.load_context()
            with pytest.raises(KedroContextError, match=re.escape(pattern)):
                _ = context.catalog
