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
import configparser
import json
import re
import sys
from pathlib import Path, PurePath, PurePosixPath, PureWindowsPath
from time import sleep
from typing import Any, Dict

import pandas as pd
import pytest
import toml
import yaml
from pandas.util.testing import assert_frame_equal

from kedro import __version__ as kedro_version
from kedro.config import ConfigLoader, MissingConfigException
from kedro.extras.datasets.pandas import CSVDataSet
from kedro.framework.context import KedroContext, KedroContextError
from kedro.framework.context.context import (
    _convert_paths_to_absolute_posix,
    _is_relative_path,
    _validate_layers_for_transcoding,
)
from kedro.framework.hooks import get_hook_manager, hook_impl
from kedro.framework.project import (
    Validator,
    _ProjectPipelines,
    _ProjectSettings,
    configure_project,
    pipelines,
)
from kedro.io import DataCatalog
from kedro.io.core import Version, generate_timestamp
from kedro.pipeline import Pipeline, node
from kedro.runner import ParallelRunner, SequentialRunner

MOCK_PACKAGE_NAME = "mock_package_name"


def _write_yaml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _write_toml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    toml_str = toml.dumps(config)
    filepath.write_text(toml_str)


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
    cars_filepath = (tmp_path / "cars.csv").as_posix()
    trains_filepath = (tmp_path / "trains.csv").as_posix()

    return {
        "trains": {"type": "pandas.CSVDataSet", "filepath": trains_filepath},
        "cars": {
            "type": "pandas.CSVDataSet",
            "filepath": cars_filepath,
            "save_args": {"index": True},
        },
    }


@pytest.fixture
def local_config(tmp_path):
    cars_filepath = (tmp_path / "cars.csv").as_posix()
    boats_filepath = (tmp_path / "boats.csv").as_posix()
    # use one dataset with a relative filepath
    horses_filepath = "horses.csv"
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
            "layer": "raw",
        },
        "horses": {
            "type": "pandas.CSVDataSet",
            "filepath": horses_filepath,
            "versioned": True,
        },
    }


@pytest.fixture(params=[None])
def env(request):
    return request.param


@pytest.fixture
def prepare_project_dir(tmp_path, base_config, local_config, env):
    env = "local" if env is None else env
    proj_catalog = tmp_path / "conf" / "base" / "catalog.yml"
    env_catalog = tmp_path / "conf" / str(env) / "catalog.yml"
    env_credentials = tmp_path / "conf" / str(env) / "credentials.yml"
    parameters = tmp_path / "conf" / "base" / "parameters.json"
    db_config_path = tmp_path / "conf" / "base" / "db.ini"
    project_parameters = {"param1": 1, "param2": 2, "param3": {"param4": 3}}
    _write_yaml(proj_catalog, base_config)
    _write_yaml(env_catalog, local_config)
    _write_yaml(env_credentials, local_config)
    _write_json(parameters, project_parameters)
    _write_dummy_ini(db_config_path)

    _write_toml(tmp_path / "pyproject.toml", pyproject_toml_payload)


class RegistrationHooks:
    @hook_impl
    def register_catalog(
        self, catalog, credentials, load_versions, save_version, journal
    ) -> DataCatalog:
        return DataCatalog.from_config(
            catalog, credentials, load_versions, save_version, journal
        )

    @hook_impl
    def register_config_loader(self, conf_paths) -> ConfigLoader:
        return ConfigLoader(conf_paths)


class MockSettings(_ProjectSettings):
    _HOOKS = Validator("HOOKS", default=(RegistrationHooks(),))


@pytest.fixture(autouse=True)
def mock_settings(mocker):
    mocked_settings = MockSettings()
    mocker.patch("kedro.framework.session.session.settings", mocked_settings)
    mocker.patch("kedro.framework.context.context.settings", mocked_settings)
    return mocker.patch("kedro.framework.project.settings", mocked_settings)


@pytest.fixture(autouse=True)
def mock_pipelines(mocker):
    mocker.patch.object(
        _ProjectPipelines,
        "_get_pipelines_registry_callable",
        return_value=_create_pipelines,
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


def identity(input1: str):
    return input1  # pragma: no cover


def bad_node(x):
    raise ValueError("Oh no!")


expected_message_middle = (
    "There are 2 nodes that have not run.\n"
    "You can resume the pipeline run by adding the following "
    "argument to your previous command:\n"
    '  --from-nodes "nodes3"'
)


expected_message_head = (
    "There are 4 nodes that have not run.\n"
    "You can resume the pipeline run by adding the following "
    "argument to your previous command:\n"
)

pyproject_toml_payload = {
    "tool": {
        "kedro": {
            "project_name": "mock_project_name",
            "project_version": kedro_version,
            "package_name": MOCK_PACKAGE_NAME,
        }
    }
}


def _create_pipelines():
    bad_pipeline_middle = Pipeline(
        [
            node(identity, "cars", "boats", name="node1", tags=["tag1"]),
            node(identity, "boats", "trains", name="node2"),
            node(bad_node, "trains", "ships", name="nodes3"),
            node(identity, "ships", "planes", name="node4"),
        ],
        tags="bad_pipeline",
    )
    bad_pipeline_head = Pipeline(
        [
            node(bad_node, "cars", "boats", name="node1", tags=["tag1"]),
            node(identity, "boats", "trains", name="node2"),
            node(identity, "trains", "ships", name="nodes3"),
            node(identity, "ships", "planes", name="node4"),
        ],
        tags="bad_pipeline",
    )
    default_pipeline = Pipeline(
        [
            node(identity, "cars", "boats", name="node1", tags=["tag1"]),
            node(identity, "boats", "trains", name="node2"),
            node(identity, "trains", "ships", name="node3"),
            node(identity, "ships", "planes", name="node4"),
        ],
        tags="pipeline",
    )
    return {
        "__default__": default_pipeline,
        "empty": Pipeline([]),
        "simple": Pipeline([node(identity, "cars", "boats")]),
        "bad_pipeline_middle": bad_pipeline_middle,
        "bad_pipeline_head": bad_pipeline_head,
    }


@pytest.fixture(params=[None])
def extra_params(request):
    return request.param


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture
def dummy_context(
    tmp_path, prepare_project_dir, env, extra_params, mocker
):  # pylint: disable=unused-argument
    mocker.patch("kedro.framework.project._validate_module")
    configure_project(MOCK_PACKAGE_NAME)
    context = KedroContext(
        MOCK_PACKAGE_NAME, str(tmp_path), env=env, extra_params=extra_params
    )

    yield context
    pipelines._clear(MOCK_PACKAGE_NAME)


@pytest.fixture(autouse=True)
def clear_hook_manager():
    yield
    hook_manager = get_hook_manager()
    plugins = hook_manager.get_plugins()
    for plugin in plugins:
        hook_manager.unregister(plugin)


class TestKedroContext:
    def test_deprecate_reading_conf_root_from_context(self, dummy_context):
        pattern = (
            "Accessing CONF_ROOT via the context will be deprecated in Kedro 0.18.0."
        )
        with pytest.warns(DeprecationWarning, match=pattern):
            assert dummy_context.CONF_ROOT == "conf"

    def test_deprecate_setting_conf_root_on_context(self, dummy_context):
        pattern = (
            "Accessing CONF_ROOT via the context will be deprecated in Kedro 0.18.0."
        )
        with pytest.warns(DeprecationWarning, match=pattern):
            dummy_context.CONF_ROOT = "test_conf"

    @pytest.mark.parametrize("property_name", ["io", "pipeline", "pipelines"])
    def test_deprecate_properties_on_context(self, property_name, dummy_context):
        pattern = f"Accessing {property_name} via the context will be deprecated in Kedro 0.18.0."
        with pytest.warns(DeprecationWarning, match=pattern):
            assert getattr(dummy_context, property_name)

    def test_attributes(self, tmp_path, dummy_context):
        project_metadata = pyproject_toml_payload["tool"]["kedro"]
        assert dummy_context.package_name == project_metadata["package_name"]
        assert isinstance(dummy_context.project_path, Path)
        assert dummy_context.project_path == tmp_path.resolve()

    def test_get_catalog_always_using_absolute_path(self, dummy_context):
        conf_catalog = dummy_context.config_loader.get("catalog*")

        # even though the raw configuration uses relative path
        assert conf_catalog["horses"]["filepath"] == "horses.csv"

        # the catalog and its dataset should be loaded using absolute path
        # based on the project path
        catalog = dummy_context._get_catalog()
        ds_path = catalog._data_sets["horses"]._filepath
        assert PurePath(ds_path.as_posix()).is_absolute()
        assert (
            ds_path.as_posix()
            == (dummy_context._project_path / "horses.csv").as_posix()
        )

    def test_get_catalog_validates_layers(self, dummy_context, mocker):
        mock_validate = mocker.patch(
            "kedro.framework.context.context._validate_layers_for_transcoding"
        )
        catalog = dummy_context.catalog

        mock_validate.assert_called_once_with(catalog)

    def test_catalog(self, dummy_context, dummy_dataframe):
        assert dummy_context.catalog.layers == {"raw": {"boats"}}
        dummy_context.catalog.save("cars", dummy_dataframe)
        reloaded_df = dummy_context.catalog.load("cars")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_io(self, dummy_context, dummy_dataframe):
        dummy_context.io.save("cars", dummy_dataframe)
        reloaded_df = dummy_context.io.load("cars")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.parametrize(
        "extra_params",
        [None, {}, {"foo": "bar", "baz": [1, 2], "qux": None}],
        indirect=True,
    )
    def test_params(self, dummy_context, extra_params):
        extra_params = extra_params or {}
        expected = {"param1": 1, "param2": 2, "param3": {"param4": 3}, **extra_params}
        assert dummy_context.params == expected

    @pytest.mark.parametrize(
        "param,expected",
        [("params:param3", {"param4": 3}), ("params:param3.param4", 3)],
    )
    def test_nested_params(self, param, expected, dummy_context):
        param = dummy_context.catalog.load(param)
        assert param == expected

    @pytest.mark.parametrize(
        "extra_params",
        [None, {}, {"foo": "bar", "baz": [1, 2], "qux": None}],
        indirect=True,
    )
    def test_params_missing(self, mocker, extra_params, dummy_context):
        mock_config_loader = mocker.patch.object(KedroContext, "config_loader")
        mock_config_loader.get.side_effect = MissingConfigException("nope")
        extra_params = extra_params or {}

        pattern = "Parameters not found in your Kedro project config"
        with pytest.warns(UserWarning, match=pattern):
            actual = dummy_context.params
        assert actual == extra_params

    def test_config_loader(self, dummy_context):
        params = dummy_context.config_loader.get("parameters*")
        db_conf = dummy_context.config_loader.get("db*")
        catalog = dummy_context.config_loader.get("catalog*")

        assert params["param1"] == 1
        assert db_conf["prod"]["url"] == "postgresql://user:pass@url_prod/db"

        assert catalog["trains"]["type"] == "pandas.CSVDataSet"
        assert catalog["cars"]["type"] == "pandas.CSVDataSet"
        assert catalog["boats"]["type"] == "pandas.CSVDataSet"
        assert not catalog["cars"]["save_args"]["index"]

    def test_default_env(self, dummy_context):
        assert dummy_context.env == "local"

    @pytest.mark.parametrize("env", ["custom_env"], indirect=True)
    def test_custom_env(self, dummy_context, env):
        assert dummy_context.env == env

    def test_missing_parameters(self, tmp_path, dummy_context):
        parameters = tmp_path / "conf" / "base" / "parameters.json"
        parameters.unlink()

        pattern = "Parameters not found in your Kedro project config."
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            _ = dummy_context.catalog

    def test_missing_credentials(self, dummy_context):
        env_credentials = (
            dummy_context.project_path / "conf" / "local" / "credentials.yml"
        )
        env_credentials.unlink()

        pattern = "Credentials not found in your Kedro project config."
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            _ = dummy_context.catalog

    def test_pipeline(self, dummy_context):
        assert dummy_context.pipeline.nodes[0].inputs == ["cars"]
        assert dummy_context.pipeline.nodes[0].outputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].inputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].outputs == ["trains"]

    def test_pipelines(self, dummy_context):
        assert len(dummy_context.pipelines) == 5
        assert len(dummy_context.pipelines["__default__"].nodes) == 4


class TestKedroContextRun:
    def test_deprecate_run(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        pattern = (
            "`kedro.framework.context.KedroContext.run` is now deprecated in favour of "
            "`KedroSession.run` and will be removed in Kedro 0.18.0."
        )
        with pytest.warns(DeprecationWarning, match=pattern):
            dummy_context.run()

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

    @pytest.mark.skipif(
        sys.platform.startswith("win"), reason="Due to bug in parallel runner"
    )
    def test_parallel_run_arg(self, dummy_context, dummy_dataframe, caplog, mocker):
        mocker.patch(
            "kedro.framework.context.context.load_context", return_value=dummy_context
        )
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

    def test_run_to_outputs(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(to_outputs=["trains"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 2 out of 2 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" not in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs

    def test_run_load_versions(self, dummy_context, dummy_dataframe):
        filepath = (dummy_context.project_path / "cars.csv").as_posix()

        old_save_version = generate_timestamp()
        old_df = pd.DataFrame({"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]})
        old_csv_data_set = CSVDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, old_save_version),
        )
        old_csv_data_set.save(old_df)

        sleep(0.5)
        new_save_version = generate_timestamp()
        new_csv_data_set = CSVDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, new_save_version),
        )
        new_csv_data_set.save(dummy_dataframe)

        load_versions = {"cars": old_save_version}
        dummy_context.run(load_versions=load_versions, pipeline_name="simple")
        assert not dummy_context.catalog.load("boats").equals(dummy_dataframe)
        assert dummy_context.catalog.load("boats").equals(old_df)

    def test_run_with_empty_pipeline(self, dummy_context):
        with pytest.raises(KedroContextError, match="Pipeline contains no nodes"):
            dummy_context.run(pipeline_name="empty")

    @pytest.mark.parametrize(
        "pipeline_name,expected_message",
        [
            ("bad_pipeline_middle", expected_message_middle),
            ("bad_pipeline_head", expected_message_head),
        ],  # pylint: disable=too-many-arguments
    )
    def test_run_failure_prompts_resume_command(
        self, dummy_context, dummy_dataframe, caplog, pipeline_name, expected_message
    ):
        dummy_context.catalog.save("cars", dummy_dataframe)
        with pytest.raises(ValueError, match="Oh no"):
            dummy_context.run(pipeline_name=pipeline_name)

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

    @pytest.mark.parametrize(
        "extra_params",
        [None, {}, {"foo": "bar", "baz": [1, 2], "qux": None}],
        indirect=True,
    )
    def test_run_with_extra_params(
        self, mocker, dummy_context, dummy_dataframe, extra_params
    ):
        mock_journal = mocker.patch("kedro.framework.context.context.Journal")
        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run()

        assert mock_journal.call_args[0][0]["extra_params"] == extra_params

    def test_run_with_save_version_as_run_id(
        self, mocker, dummy_context, dummy_dataframe, caplog
    ):
        """Test that the default behaviour, with run_id set to None,
        creates a journal record with the run_id the same as save_version.
        """
        save_version = "2020-01-01T00.00.00.000Z"
        mocked_get_save_version = mocker.patch.object(
            dummy_context, "_get_save_version", return_value=save_version
        )

        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run(load_versions={"boats": save_version})

        mocked_get_save_version.assert_called_once_with()
        log_msg = next(
            record.getMessage()
            for record in caplog.records
            if record.name == "kedro.journal"
        )
        assert json.loads(log_msg)["run_id"] == save_version

    def test_run_with_custom_run_id(
        self, mocker, dummy_context, dummy_dataframe, caplog
    ):
        run_id = "001"
        mocked_get_run_id = mocker.patch.object(
            dummy_context, "_get_run_id", return_value=run_id
        )

        dummy_context.catalog.save("cars", dummy_dataframe)
        dummy_context.run()

        # once during run, and twice for each `.catalog`
        assert mocked_get_run_id.call_count == 3
        log_msg = next(
            record.getMessage()
            for record in caplog.records
            if record.name == "kedro.journal"
        )
        assert json.loads(log_msg)["run_id"] == run_id


@pytest.mark.parametrize(
    "path_string,expected",
    [
        # remote paths shouldn't be relative paths
        ("s3://", False),
        ("gcp://path/to/file.json", False),
        # windows absolute path shouldn't relative paths
        ("C:\\path\\to\\file.json", False),
        ("C:", False),
        ("C:/Windows/", False),
        # posix absolute path shouldn't be relative paths
        ("/tmp/logs/info.log", False),
        ("/usr/share", False),
        # test relative paths
        ("data/01_raw/data.json", True),
        ("logs/info.log", True),
        ("logs\\error.txt", True),
        ("data", True),
    ],
)
def test_is_relative_path(path_string: str, expected: bool):
    assert _is_relative_path(path_string) == expected


def test_convert_paths_raises_error_on_relative_project_path():
    path = Path("relative") / "path"

    pattern = f"project_path must be an absolute path. Received: {path}"
    with pytest.raises(ValueError, match=re.escape(pattern)):
        _convert_paths_to_absolute_posix(project_path=path, conf_dictionary={})


@pytest.mark.parametrize(
    "project_path,input_conf,expected",
    [
        (
            PurePosixPath("/tmp"),
            {"handler": {"filename": "logs/info.log"}},
            {"handler": {"filename": "/tmp/logs/info.log"}},
        ),
        (
            PurePosixPath("/User/kedro"),
            {"my_dataset": {"filepath": "data/01_raw/dataset.json"}},
            {"my_dataset": {"filepath": "/User/kedro/data/01_raw/dataset.json"}},
        ),
        (
            PureWindowsPath("C:\\kedro"),
            {"my_dataset": {"path": "data/01_raw/dataset.json"}},
            {"my_dataset": {"path": "C:/kedro/data/01_raw/dataset.json"}},
        ),
        # test: the function shouldn't modify paths for key not associated with filepath
        (
            PurePosixPath("/User/kedro"),
            {"my_dataset": {"fileurl": "relative/url"}},
            {"my_dataset": {"fileurl": "relative/url"}},
        ),
    ],
)
def test_convert_paths_to_absolute_posix_for_all_known_filepath_keys(
    project_path: Path, input_conf: Dict[str, Any], expected: Dict[str, Any]
):
    assert _convert_paths_to_absolute_posix(project_path, input_conf) == expected


@pytest.mark.parametrize(
    "project_path,input_conf,expected",
    [
        (
            PurePosixPath("/tmp"),
            {"handler": {"filename": "/usr/local/logs/info.log"}},
            {"handler": {"filename": "/usr/local/logs/info.log"}},
        ),
        (
            PurePosixPath("/User/kedro"),
            {"my_dataset": {"filepath": "s3://data/01_raw/dataset.json"}},
            {"my_dataset": {"filepath": "s3://data/01_raw/dataset.json"}},
        ),
    ],
)
def test_convert_paths_to_absolute_posix_not_changing_non_relative_path(
    project_path: Path, input_conf: Dict[str, Any], expected: Dict[str, Any]
):
    assert _convert_paths_to_absolute_posix(project_path, input_conf) == expected


@pytest.mark.parametrize(
    "project_path,input_conf,expected",
    [
        (
            PureWindowsPath("D:\\kedro"),
            {"my_dataset": {"path": r"C:\data\01_raw\dataset.json"}},
            {"my_dataset": {"path": "C:/data/01_raw/dataset.json"}},
        )
    ],
)
def test_convert_paths_to_absolute_posix_converts_full_windows_path_to_posix(
    project_path: Path, input_conf: Dict[str, Any], expected: Dict[str, Any]
):
    assert _convert_paths_to_absolute_posix(project_path, input_conf) == expected


@pytest.mark.parametrize(
    "layers",
    [
        {"raw": {"A"}, "interm": {"B", "C"}},
        {"raw": {"A"}, "interm": {"B@2", "B@1"}},
        {"raw": {"C@1"}, "interm": {"A", "B@1", "B@2", "B@3"}},
    ],
)
def test_validate_layers(layers, mocker):
    mock_catalog = mocker.MagicMock()
    mock_catalog.layers = layers

    _validate_layers_for_transcoding(mock_catalog)  # it shouldn't raise any error


@pytest.mark.parametrize(
    "layers,conflicting_datasets",
    [
        ({"raw": {"A", "B@1"}, "interm": {"B@2"}}, ["B@2"]),
        ({"raw": {"A"}, "interm": {"B@1", "B@2"}, "prm": {"B@3"}}, ["B@3"]),
        (
            {
                "raw": {"A@1"},
                "interm": {"B@1", "B@2"},
                "prm": {"B@3", "B@4"},
                "other": {"A@2"},
            },
            ["A@2", "B@3", "B@4"],
        ),
    ],
)
def test_validate_layers_error(layers, conflicting_datasets, mocker):
    mock_catalog = mocker.MagicMock()
    mock_catalog.layers = layers
    error_str = ", ".join(conflicting_datasets)

    pattern = (
        f"Transcoded datasets should have the same layer. "
        f"Mismatch found for: {error_str}"
    )
    with pytest.raises(ValueError, match=re.escape(pattern)):
        _validate_layers_for_transcoding(mock_catalog)
