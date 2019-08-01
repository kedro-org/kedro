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
import sys
import textwrap
from pathlib import Path
from typing import Dict

import pandas as pd
import pytest
import yaml
from pandas.util.testing import assert_frame_equal

from kedro import __version__
from kedro.context import KedroContext, KedroContextError, load_context
from kedro.context.context import check_context_version
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


@pytest.fixture(autouse=True)
def restore_cwd():
    cwd_ = os.getcwd()
    yield
    if cwd_ != os.getcwd():
        os.chdir(cwd_)


@pytest.fixture
def fake_project(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    kedro_cli = project / "kedro_cli.py"
    script = """
        class Fake:
            project_name = "fake"
            project_version = "{}"

        def __get_kedro_context__():
            return Fake()
    """.format(
        __version__
    )
    kedro_cli.write_text(textwrap.dedent(script), encoding="utf-8")
    yield project


def identity(input1: str):
    return input1  # pragma: no cover


class DummyContext(KedroContext):
    project_name = "bob"
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
    if env is None:
        return DummyContext(str(tmp_path))
    return DummyContext(str(tmp_path), env)


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
            DummyContext(str(tmp_path))

    def test_missing_credentials(self, tmp_path, mocker):
        env_credentials = tmp_path / "conf" / "local" / "credentials.yml"
        os.remove(str(env_credentials))

        # Disable logging.config.dictConfig in KedroContext._setup_logging as
        # it changes logging.config and affects other unit tests
        mocker.patch("logging.config.dictConfig")

        with pytest.warns(
            UserWarning, match="Credentials not found in your Kedro project config."
        ):
            DummyContext(str(tmp_path))

    def test_pipeline(self, dummy_context):
        assert dummy_context.pipeline.nodes[0].inputs == ["cars"]
        assert dummy_context.pipeline.nodes[0].outputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].inputs == ["boats"]
        assert dummy_context.pipeline.nodes[1].outputs == ["trains"]


@pytest.mark.usefixtures("config_dir")
class TestKedroContextRun:
    def test_default_run(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run()

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]

        assert "kedro.runner.sequential_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs
        pd.testing.assert_frame_equal(outputs['planes'], dummy_dataframe)

    def test_sequential_run_arg(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(runner=SequentialRunner())

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]
        assert "kedro.runner.sequential_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs
        pd.testing.assert_frame_equal(outputs['planes'], dummy_dataframe)

    def test_parallel_run_arg(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(runner=ParallelRunner())

        log_msgs = [record.getMessage() for record in caplog.records]
        log_names = [record.name for record in caplog.records]
        assert "kedro.runner.parallel_runner" in log_names
        assert "Pipeline execution completed successfully." in log_msgs
        pd.testing.assert_frame_equal(outputs['planes'], dummy_dataframe)

    def test_run_with_node_names(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(node_names=["node1"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs
        assert not outputs

    def test_run_with_node_names_and_tags(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(node_names=["node1"], tags=["tag1", "pipeline"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs
        assert not outputs

    def test_run_with_tags(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(tags=["tag1"])
        log_msgs = [record.getMessage() for record in caplog.records]

        assert "Completed 1 out of 1 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" not in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert not outputs

    def test_run_with_wrong_tags(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        pattern = r"Pipeline contains no nodes with tags: \['non\-existent'\]"
        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run(tags=["non-existent"])

    def test_run_from_nodes(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(from_nodes=["node1"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 4 out of 4 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        pd.testing.assert_frame_equal(outputs['planes'], dummy_dataframe)

    def test_run_to_nodes(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(to_nodes=["node2"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 2 out of 2 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" not in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        assert not outputs

    def test_run_with_node_range(self, dummy_context, dummy_dataframe, caplog):
        dummy_context.catalog.save("cars", dummy_dataframe)
        outputs = dummy_context.run(from_nodes=["node1"], to_nodes=["node3"])

        log_msgs = [record.getMessage() for record in caplog.records]
        assert "Completed 3 out of 3 tasks" in log_msgs
        assert "Running node: node1: identity([cars]) -> [boats]" in log_msgs
        assert "Running node: node2: identity([boats]) -> [trains]" in log_msgs
        assert "Running node: node3: identity([trains]) -> [ships]" in log_msgs
        assert "Pipeline execution completed successfully." in log_msgs
        pd.testing.assert_frame_equal(outputs['ships'], dummy_dataframe)

    def test_run_with_invalid_node_range(self, dummy_context, dummy_dataframe):
        dummy_context.catalog.save("cars", dummy_dataframe)
        pattern = "Pipeline contains no nodes"

        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run(from_nodes=["node3"], to_nodes=["node1"])

    @pytest.mark.filterwarnings("ignore")
    def test_run_with_empty_pipeline(self, tmp_path, mocker):
        class DummyContext(KedroContext):
            project_name = "bob"
            project_version = __version__

            @property
            def pipeline(self) -> Pipeline:
                return Pipeline([])

        mocker.patch("logging.config.dictConfig")
        dummy_context = DummyContext(str(tmp_path))
        assert dummy_context.project_name == "bob"
        assert dummy_context.project_version == __version__
        pattern = "Pipeline contains no nodes"
        with pytest.raises(KedroContextError, match=pattern):
            dummy_context.run()


def test_load_context(fake_project, tmp_path, mocker):
    """Test getting project context"""
    mocker.patch("kedro.context.context.check_context_version")
    result = load_context(str(fake_project))
    assert result.project_name == "fake"
    assert result.project_version == __version__
    assert str(fake_project.resolve()) in sys.path
    assert os.getcwd() == str(fake_project.resolve())

    other_path = tmp_path / "other"
    other_path.mkdir()
    pattern = (
        r"Cannot load context for `{}`, since another project "
        r"`.*` has already been loaded".format(other_path.resolve())
    )
    with pytest.raises(KedroContextError, match=pattern):
        load_context(str(other_path))


def test_valid_context_version(mocker):
    mocked_context = mocker.patch("kedro.context.KedroContext", autospec=True)
    context = mocked_context("fake_path")
    context.project_version = __version__
    check_context_version(context)


def test_invalid_context_version_dict():
    context_dict = {"project_version": __version__}
    pattern = (
        r"Your Kedro project version {} does not match "
        r"Kedro package version {} you are running. ".format(
            context_dict["project_version"], __version__
        )
    )
    with pytest.raises(KedroContextError, match=pattern):
        check_context_version(context_dict)


@pytest.mark.parametrize("project_version", ["0.13.0", "10.0", "101.1", "100.0", "-0"])
def test_invalid_context_version(mocker, project_version):
    mocked_context = mocker.patch("kedro.context.KedroContext", autospec=True)
    context = mocked_context("fake_path")
    context.project_version = project_version

    pattern = (
        r"Your Kedro project version {} does not match "
        r"Kedro package version {} you are running. ".format(
            context.project_version, __version__
        )
    )
    with pytest.raises(KedroContextError, match=pattern):
        check_context_version(context)
