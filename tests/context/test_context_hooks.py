# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import logging
from logging.handlers import QueueHandler, QueueListener
from multiprocessing import Queue
from pathlib import Path
from typing import Any, Dict, List, Union

import pandas as pd
import pytest
import yaml

from kedro import __version__
from kedro.context import KedroContext
from kedro.context.context import _expand_path
from kedro.hooks import hook_impl
from kedro.hooks.manager import _create_hook_manager
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node, node
from kedro.runner import ParallelRunner


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
def config_dir(tmp_path, local_config, local_logging_config):
    catalog = tmp_path / "conf" / "base" / "catalog.yml"
    credentials = tmp_path / "conf" / "local" / "credentials.yml"
    logging = tmp_path / "conf" / "local" / "logging.yml"
    _write_yaml(catalog, local_config)
    _write_yaml(credentials, {"dev_s3": "foo"})
    _write_yaml(logging, local_logging_config)


@pytest.fixture(autouse=True)
def hook_manager(monkeypatch):
    # re-create the global hook manager after every test
    hook_manager = _create_hook_manager()
    monkeypatch.setattr("kedro.hooks.get_hook_manager", lambda: hook_manager)
    monkeypatch.setattr("kedro.context.context.get_hook_manager", lambda: hook_manager)
    monkeypatch.setattr("kedro.runner.runner.get_hook_manager", lambda: hook_manager)
    return hook_manager


def identity(x: str):
    return x


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"test": [1, 2]})


class LoggingHooks:
    """A set of test hooks that only log information when invoked.
    Use a log queue to properly test log messages written by hooks invoked by ParallelRunner.
    """

    handler_name = "hooks_handler"

    def __init__(self, logs_queue):
        self.logger = logging.getLogger("hooks_handler")
        self.logger.handlers = []
        self.logger.addHandler(QueueHandler(logs_queue))

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
    def before_pipeline_run(
        self, run_params: Dict[str, Any], pipeline: Pipeline, catalog: DataCatalog
    ) -> None:
        self.logger.info(
            "About to run pipeline",
            extra={"pipeline": pipeline, "run_params": run_params, "catalog": catalog},
        )

    @hook_impl
    def after_pipeline_run(
        self, run_params: Dict[str, Any], pipeline: Pipeline, catalog: DataCatalog
    ) -> None:
        self.logger.info(
            "Ran pipeline",
            extra={"pipeline": pipeline, "run_params": run_params, "catalog": catalog},
        )


@pytest.fixture
def logs_queue():
    return Queue()


@pytest.fixture
def logging_hooks(logs_queue):
    return LoggingHooks(logs_queue)


@pytest.fixture
def context_with_hooks(tmp_path, mocker, logging_hooks):
    class DummyContextWithHooks(KedroContext):
        project_name = "test hooks"
        package_name = "test_hooks"
        project_version = __version__
        hooks = (logging_hooks,)

        def _get_run_id(self, *args, **kwargs) -> Union[None, str]:
            return "mocked context with hooks run id"

        def _get_pipelines(self) -> Dict[str, Pipeline]:
            pipeline = Pipeline(
                [
                    node(identity, "cars", "planes", name="node1"),
                    node(identity, "boats", "ships", name="node2"),
                ],
                tags="pipeline",
            )
            return {"__default__": pipeline}

    mocker.patch("logging.config.dictConfig")
    return DummyContextWithHooks(str(tmp_path), env="local")


class TestKedroContextHooks:
    @staticmethod
    def _assert_hook_call_record_has_expected_parameters(
        call_record: logging.LogRecord, expected_parameters: List[str]
    ):
        """Assert the given call record has all expected parameters."""
        for param in expected_parameters:
            assert hasattr(call_record, param)

    def test_calling_register_hooks_multiple_times_should_not_raise(
        self, context_with_hooks
    ):
        context_with_hooks._register_hooks()
        context_with_hooks._register_hooks()
        assert True  # if we get to this statement, it means the previous repeated calls don't raise

    def test_hooks_are_registered_when_context_is_created(
        self, tmp_path, mocker, logging_hooks, hook_manager
    ):
        # assert hooks are not registered before context is created
        assert not hook_manager.is_registered(logging_hooks)

        # create the context
        context_with_hooks(tmp_path, mocker, logging_hooks)

        # assert hooks are registered after context is created
        assert hook_manager.is_registered(logging_hooks)

    def test_after_catalog_created_hook_is_called(self, context_with_hooks, caplog):
        catalog = context_with_hooks.catalog
        config_loader = context_with_hooks.config_loader
        relevant_records = [
            r for r in caplog.records if r.name == LoggingHooks.handler_name
        ]
        record = relevant_records[0]
        assert record.getMessage() == "Catalog created"
        assert record.catalog == catalog
        assert record.conf_creds == config_loader.get("credentials*")
        assert record.conf_catalog == _expand_path(
            project_path=context_with_hooks.project_path,
            conf_dictionary=config_loader.get("catalog*"),
        )
        assert record.save_version is None
        assert record.load_versions is None
        assert record.run_id == "mocked context with hooks run id"

    def test_before_and_after_pipeline_run_hooks_are_called(
        self, context_with_hooks, dummy_dataframe, caplog
    ):

        context_with_hooks.catalog.save("cars", dummy_dataframe)
        context_with_hooks.catalog.save("boats", dummy_dataframe)
        context_with_hooks.run()

        # test before pipeline run hook
        before_pipeline_run_calls = [
            record
            for record in caplog.records
            if record.funcName == "before_pipeline_run"
        ]
        assert len(before_pipeline_run_calls) == 1
        call_record = before_pipeline_run_calls[0]
        assert call_record.pipeline.describe() == context_with_hooks.pipeline.describe()
        self._assert_hook_call_record_has_expected_parameters(
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
        self._assert_hook_call_record_has_expected_parameters(
            call_record, ["pipeline", "catalog", "run_params"]
        )
        assert call_record.pipeline.describe() == context_with_hooks.pipeline.describe()

    def test_before_and_after_node_run_hooks_are_called_with_sequential_runner(
        self, context_with_hooks, dummy_dataframe, caplog
    ):
        context_with_hooks.catalog.save("cars", dummy_dataframe)
        context_with_hooks.run(node_names=["node1"])

        # test before node run hook
        before_node_run_calls = [
            record for record in caplog.records if record.funcName == "before_node_run"
        ]
        assert len(before_node_run_calls) == 1
        call_record = before_node_run_calls[0]
        self._assert_hook_call_record_has_expected_parameters(
            call_record, ["node", "catalog", "inputs", "is_async", "run_id"]
        )
        # sanity check a couple of important parameters
        assert call_record.inputs["cars"].to_dict() == dummy_dataframe.to_dict()
        assert call_record.run_id == context_with_hooks.run_id

        # test after node run hook
        after_node_run_calls = [
            record for record in caplog.records if record.funcName == "after_node_run"
        ]
        assert len(after_node_run_calls) == 1
        call_record = after_node_run_calls[0]
        self._assert_hook_call_record_has_expected_parameters(
            call_record, ["node", "catalog", "inputs", "outputs", "is_async", "run_id"]
        )
        # sanity check a couple of important parameters
        assert call_record.outputs["planes"].to_dict() == dummy_dataframe.to_dict()
        assert call_record.run_id == context_with_hooks.run_id

    def test_before_and_after_node_run_hooks_are_called_with_parallel_runner(
        self, context_with_hooks, dummy_dataframe, logs_queue
    ):
        log_records = []

        class LogHandler(logging.Handler):  # pylint: disable=abstract-method
            def handle(self, record):
                log_records.append(record)

        logs_queue_listener = QueueListener(logs_queue, LogHandler())
        logs_queue_listener.start()
        context_with_hooks.catalog.save("cars", dummy_dataframe)
        context_with_hooks.catalog.save("boats", dummy_dataframe)
        context_with_hooks.run(runner=ParallelRunner(), node_names=["node1", "node2"])
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
