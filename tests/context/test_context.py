# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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

import configparser
import json
import os
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest
import yaml
from pandas.util.testing import assert_frame_equal

from kedro import __version__
from kedro.config import MissingConfigException
from kedro.context import KedroContext, KedroContextError
from kedro.io import CSVLocalDataSet
from kedro.io.core import Version, generate_timestamp
from kedro.pipeline import Pipeline, node
from kedro.runner import ParallelRunner, SequentialRunner


def _get_local_logging_config():
    return {
        "version": 1,
        "formatters": {
            "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "kedro": {"level": "INFO", "handlers": ["console"], "propagate": False}
        },
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


def _write_json(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    json_str = json.dumps(config)
    filepath.write_text(json_str)


def _write_dummy_ini(filepath: Path):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser()
    config["prod"] = {"url": "postgresql://user:pass@url_prod/db"}
    config["staging"] = {"url": "postgresql://user:pass@url_staging/db"}
    with filepath.open("wt") as configfile:  # save
        config.write(configfile)


@pytest.fixture
def base_config(tmp_path):
    cars_filepath = str(tmp_path / "cars.csv")
    trains_filepath = str(tmp_path / "trains.csv")

    return {
        "trains": {"type": "CSVLocalDataSet", "filepath": trains_filepath},
        "cars": {
            "type": "CSVLocalDataSet",
            "filepath": cars_filepath,
            "save_args": {"index": True},
        },
    }


@pytest.fixture
def local_config(tmp_path):
    cars_filepath = str(tmp_path / "cars.csv")
    boats_filepath = str(tmp_path / "boats.csv")
    return {
        "cars": {
            "type": "CSVLocalDataSet",
            "filepath": cars_filepath,
            "save_args": {"index": False},
            "versioned": True,
        },
        "boats": {"type": "CSVLocalDataSet", "filepath": boats_filepath},
    }


@pytest.fixture(params=[None])
def env(request):
    return request.param


@pytest.fixture
def config_dir(tmp_path, base_config, local_config, env):
    env = "local" if env is None else env
    proj_catalog = tmp_path / "conf" / "base" / "catalog.yml"
    env_catalog = tmp_path / "conf" / str(env) / "catalog.yml"
    env_credentials = tmp_path / "conf" / str(env) / "credentials.yml"
    env_logging = tmp_path / "conf" / str(env) / "logging.yml"
    parameters = tmp_path / "conf" / "base" / "parameters.json"
    db_config_path = tmp_path / "conf" / "base" / "db.ini"
    project_parameters = dict(param1=1, param2=2)
    _write_yaml(proj_catalog, base_config)
    _write_yaml(env_catalog, local_config)
    _write_yaml(env_credentials, local_config)
    _write_yaml(env_logging, _get_local_logging_config())
    _write_json(parameters, project_parameters)
    _write_dummy_ini(db_config_path)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


def identity(input1: str):
    return input1  # pragma: no cover


def bad_node(x):
    raise ValueError("Oh no!")


bad_pipeline_middle = Pipeline(
    [
        node(identity, "cars", "boats", name="node1", tags=["tag1"]),
        node(identity, "boats", "trains", name="node2"),
        node(bad_node, "trains", "ships", name="nodes3"),
        node(identity, "ships", "planes", name="node4"),
    ],
    name="bad_pipeline",
)

expected_message_middle = (
    "There are 2 nodes that have not run.\n"
    "You can resume the pipeline run with the following command:\n"
    "kedro run --from-inputs trains"
)


bad_pipeline_head = Pipeline(
    [
        node(bad_node, "cars", "boats", name="node1", tags=["tag1"]),
        node(identity, "boats", "trains", name="node2"),
        node(identity, "trains", "ships", name="nodes3"),
        node(identity, "ships", "planes", name="node4"),
    ],
    name="bad_pipeline",
)

expected_message_head = (
    "There are 4 nodes that have not run.\n"
    "You can resume the pipeline run with the following command:\n"
    "kedro run"
)


class DummyContext(KedroContext):
    project_name = "bob"
    project_version = __version__

    def _get_pipelines(self) -> Dict[str, Pipeline]:
        pipeline = Pipeline(
            [
                node(identity, "cars", "boats", name="node1", tags=["tag1"]),
                node(identity, "boats", "trains", name="node2"),
                node(identity, "trains", "ships", name="node3"),
                node(identity, "ships", "planes", name="node4"),
            ],
            name="pipeline",
        )
        return {"__default__": pipeline}


class DummyContextWithPipelinePropertyOnly(KedroContext):
    """
    We need this for testing the backward compatibility.
    """

    # pylint: disable=abstract-method

    project_name = "bob_old"
    project_version = __version__

    @property
    def pipeline(self) -> Pipeline:
        return Pipeline(
            [
                node(identity, "cars", "boats", name="node1", tags=["tag1"]),
                node(identity, "boats", "trains", name="node2"),
                node(identity, "trains", "ships", name="node3"),
                node(identity, "ships", "planes", name="node4"),
            ],
            name="pipeline",
        )


@pytest.fixture
def dummy_context(tmp_path, mocker, env):
    # Disable logging.config.dictConfig in KedroContext._setup_logging as
    # it changes logging.config and affects other unit tests
    mocker.patch("logging.config.dictConfig")
    return DummyContext(str(tmp_path), env=env)


@pytest.mark.usefixtures("config_dir")
class TestKedroContext:
    def test_project_name(self, dummy_context):
        assert dummy_context.project_name == "bob"

    def test_project_version(self, dummy_context):
        assert dummy_context.project_version == __version__

    def test_project_path(self, dummy_context, tmp_path):
        assert str(dummy_context.project_path) == str(tmp_path.resolve())

    def test_catalog(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        reloaded_df = dummy_context.catalog.load("cars")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_io(self, dummy_context, dummy_dataframe):
        dummy_context.io.save("cars", dummy_dataframe)
        reloaded_df = dummy_context.io.load("cars")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_params(self, dummy_context):
        assert dummy_context.params == dict(param1=1, param2=2)

    def test_params_missing(self, dummy_context, mocker):
        mock_config_loader = mocker.patch.object(DummyContext, "config_loader")
        mock_config_loader.get.side_effect = MissingConfigException("nope")

        pattern = "Parameters not found in your Kedro project config"
        with pytest.warns(UserWarning, match=pattern):
            actual = dummy_context.params
        assert actual == {}

    def test_config_loader(self, dummy_context):
        params = dummy_context.config_loader.get("parameters*")
        db_conf = dummy_context.config_loader.get("db*")
        catalog = dummy_context.config_loader.get("catalog*")

        assert params["param1"] == 1
        assert db_conf["prod"]["url"] == "postgresql://user:pass@url_prod/db"

        assert catalog["trains"]["type"] == "CSVLocalDataSet"
        assert catalog["cars"]["type"] == "CSVLocalDataSet"
        assert catalog["boats"]["type"] == "CSVLocalDataSet"
        assert not catalog["cars"]["save_args"]["index"]

    def test_default_env(self, dummy_context):
        assert dummy_context.env == "local"

    @pytest.mark.parametrize(
        "invalid_version", ["0.13.0", "10.0", "101.1", "100.0", "-0"]
    )
    def test_invalid_version(self, tmp_path, mocker, invalid_version):
        # Disable logging.config.dictConfig in KedroContext._setup_logging as
        # it changes logging.config and affects other unit tests
        mocker.patch("logging.config.dictConfig")

        class _DummyContext(KedroContext):
            project_name = "bob"
            project_version = invalid_version

            def _get_pipelines(self) -> Dict[str, Pipeline]:
                return {"__default__": Pipeline([])}  # pragma: no cover

        pattern = (
            r"Your Kedro project version {} does not match "
            r"Kedro package version {} you are running. ".format(
                invalid_version, __version__
            )
        )
        with pytest.raises(KedroContextError, match=pattern):
            _DummyContext(str(tmp_path))

    @pytest.mark.parametrize("env", ["custom_env"], indirect=True)
    def test_custom_env(self, dummy_context):
        assert dummy_context.env == "custom_env"

    def test_missing_parameters(self, tmp_path, mocker):
        parameters = tmp_path / "conf" / "base" / "parameters.json"
        os.remove(str(parameters))

        # Disable logging.config.dictConfig in KedroContext._setup_logging as
        # it changes logging.config and affects other unit tests
        mocker.patch("logging.config.dictConfig")

        with pytest.warns(
            UserWarning, match="Parameters not found in your Kedro project config."
        ):
            DummyContext(  # pylint: disable=expression-not-assigned
                str(tmp_path)
            ).catalog

    def test_missing_credentials(self, tmp_path, mocker):
        env_credentials = tmp_path / "conf" / "local" / "credentials.yml"
        os.remove(str(env_credentials))

        # Disable logging.config.dictConfig in KedroContext._setup_logging as
        # it changes logging.config and affects other unit tests
        mocker.patch("logging.config.dictConfig")

        with pytest.warns(
            UserWarning, match="Credentials not found in your Kedro project config."
        ):
            DummyContext(  # pylint: disable=expression-not-assigned
                str(tmp_path)
            ).catalog

    def test_pipeline(self, dummy_context):
        assert dummy_context.pipeline.nodes[0].inputs == ["cars"]
        assert dummy_context.pipeline.nodes[0].outputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].inputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].outputs == ["trains"]

    def test_pipelines(self, dummy_context):
        assert len(dummy_context.pipelines) == 1
        assert len(dummy_context.pipelines["__default__"].nodes) == 4


@pytest.mark.usefixtures("config_dir")
class TestKedroContextRun:
    def test_run_output(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run()
        pd.testing.assert_frame_equal(outputs["planes"], dummy_dataframe)

    def test_run_no_output(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(node_names=["node1"])
        assert not outputs

    def test_default_run(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run()

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]

        assert "kedro.runner.sequential_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs

    def test_sequential_run_arg(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(runner=SequentialRunner())

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]
        assert "kedro.runner.sequential_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs

    def test_parallel_run_arg(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(runner=ParallelRunner())

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]
        assert "kedro.runner.parallel_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_with_node_names(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(node_names=["node1"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs

    def test_run_with_node_names_and_tags(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(node_names=["node1"], tags=["tag1", "pipeline"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs

    def test_run_with_tags(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(tags=["tag1"])
        log_msgs = [record.getMessage() for record in caplog.records]

        assert "Completed 1 out of 1 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_with_wrong_tags(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        pattern = r"Pipeline contains no nodes with tags: \['non\-existent'\]"
        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run(tags=["non-existent"])

    def test_run_from_nodes(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(from_nodes=["node1"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 4 out of 4 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_to_nodes(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(to_nodes=["node2"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 2 out of 2 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" not in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_with_node_range(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(from_nodes=["node1"], to_nodes=["node3"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 3 out of 3 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_with_invalid_node_range(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        pattern = "Pipeline contains no nodes"

        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run(from_nodes=["node3"], to_nodes=["node1"])

    def test_run_from_inputs(self, dummy_context, dummy_dataframe, caplog):
        for dataset in ("cars", "trains", "boats"):
            dummy_context.catalog.save(dataset, dummy_dataframe)
        dummy_context.run(from_inputs=["trains"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 2 out of 2 tasks" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" in log_msgs
        assert "Running node: node4: identity([ships]) -> [planes]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_load_versions(self, tmp_path, dummy_context, dummy_dataframe, mocker):
        class DummyContext(KedroContext):
            project_name = "bob"
            project_version = __version__

            def _get_pipelines(self) -> Dict[str, Pipeline]:
                return {"__default__": Pipeline([node(identity, "cars", "boats")])}

        mocker.patch("logging.config.dictConfig")
        dummy_context = DummyContext(str(tmp_path))
        filepath = str(dummy_context.project_path / "cars.csv")

        old_save_version = generate_timestamp()
        old_df = pd.DataFrame({"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]})
        old_csv_data_set = CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, old_save_version),
        )
        old_csv_data_set.save(old_df)

        new_save_version = generate_timestamp()
        new_csv_data_set = CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, new_save_version),
        )
        new_csv_data_set.save(dummy_dataframe)

        load_versions = {"cars": old_save_version}
        dummy_context.run(load_versions=load_versions)
        assert not dummy_context.catalog.load("boats").equals(dummy_dataframe)
        assert dummy_context.catalog.load("boats").equals(old_df)

    def test_run_with_empty_pipeline(self, tmp_path, mocker):
        class DummyContext(KedroContext):
            project_name = "bob"
            project_version = __version__

            def _get_pipelines(self) -> Dict[str, Pipeline]:
                return {"__default__": Pipeline([])}

        mocker.patch("logging.config.dictConfig")
        dummy_context = DummyContext(str(tmp_path))
        assert dummy_context.project_name == "bob"
        assert dummy_context.project_version == __version__
        pattern = "Pipeline contains no nodes"
        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run()

    @pytest.mark.parametrize(
        "context_pipeline,expected_message",
        [
            (bad_pipeline_middle, expected_message_middle),
            (bad_pipeline_head, expected_message_head),
        ],  # pylint: disable=too-many-arguments
    )
    def test_run_failure_prompts_resume_command(
        self,
        mocker,
        tmp_path,
        dummy_dataframe,
        caplog,
        context_pipeline,
        expected_message,
    ):
        class BadContext(KedroContext):
            project_name = "fred"
            project_version = __version__

            def _get_pipelines(self) -> Dict[str, Pipeline]:
                return {"__default__": context_pipeline}

        mocker.patch("logging.config.dictConfig")

        bad_context = BadContext(str(tmp_path))
        bad_context.catalog.save("cars", dummy_dataframe)
        with pytest.raises(ValueError, match="Oh no"):
            bad_context.run()

        actual_messages = [
            record.getMessage()
            for record in caplog.records
            if record.levelname == "WARNING"
        ]

        assert expected_message in actual_messages

    def test_missing_pipeline_name(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)

        with pytest.raises(KedroContextError, match="Failed to find the pipeline"):
            dummy_context.run(pipeline_name="invalid-name")

    def test_without_get_pipeline_deprecated(
        self, dummy_dataframe, mocker, tmp_path, env
    ):
        """
        The old way of providing a `pipeline` context property is deprecated,
        but still works, yielding a warning message.
        """
        mocker.patch("logging.config.dictConfig")
        dummy_context = DummyContextWithPipelinePropertyOnly(str(tmp_path), env=env)
        dummy_context.catalog.save("cars", dummy_dataframe)

        msg = "You are using the deprecated pipeline construction mechanism"
        with pytest.warns(DeprecationWarning, match=msg):
            outputs = dummy_context.run()

        pd.testing.assert_frame_equal(outputs["planes"], dummy_dataframe)

    def test_without_get_pipeline_error(self, dummy_dataframe, mocker, tmp_path, env):
        """
        The old way of providing a `pipeline` context property is deprecated,
        but still works, yielding a warning message.
        If you try to run a sub-pipeline by name - it's an error.
        """

        mocker.patch("logging.config.dictConfig")
        dummy_context = DummyContextWithPipelinePropertyOnly(str(tmp_path), env=env)
        dummy_context.catalog.save("cars", dummy_dataframe)

        error_msg = "The project is not fully migrated to use multiple pipelines."

        with pytest.raises(KedroContextError, match=error_msg):
            dummy_context.run(pipeline_name="missing-pipeline")
