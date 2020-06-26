# Copyright 2020 QuantumBlack Visual Analytics Limited
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
import filecmp
import shutil
from pathlib import Path
from zipfile import ZipFile

import click
import pytest
import yaml
from click.testing import CliRunner
from pandas import DataFrame

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.framework.cli.pipeline import _sync_dirs
from kedro.framework.context import load_context

PACKAGE_NAME = "dummy_package"
PIPELINE_NAME = "my_pipeline"


@pytest.fixture(autouse=True)
def cleanup_pipelines(dummy_project):
    pipes_path = dummy_project / "src" / PACKAGE_NAME / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = dummy_project / "conf"
        for each in confs.glob(f"*/pipelines/{pipeline}"):  # clean all config envs
            shutil.rmtree(str(each))

        tests = dummy_project / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))


@pytest.fixture
def cleanup_dist(dummy_project):
    yield
    dist_dir = dummy_project / "src" / "dist"
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))


@pytest.fixture(params=["base"])
def make_pipelines(request, dummy_project, mocker):
    source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
    tests_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
    conf_path = dummy_project / "conf" / request.param / "pipelines" / PIPELINE_NAME

    for path in (source_path, tests_path, conf_path):
        path.mkdir(parents=True)

    (conf_path / "parameters.yml").touch()
    (tests_path / "test_pipe.py").touch()
    (source_path / "pipe.py").touch()

    yield
    mocker.stopall()
    shutil.rmtree(str(source_path), ignore_errors=True)
    shutil.rmtree(str(tests_path), ignore_errors=True)
    shutil.rmtree(str(conf_path), ignore_errors=True)


@pytest.fixture
def yaml_dump_mock(mocker):
    return mocker.patch("yaml.dump", return_value="Result YAML")


@pytest.fixture
def pipelines_dict():
    pipelines = {
        "de": ["Split Data (split_data)"],
        "ds": [
            "Train Model (train_model)",
            "Predict (predict)",
            "Report Accuracy (report_accuracy)",
        ],
    }
    pipelines["__default__"] = pipelines["de"] + pipelines["ds"]
    return pipelines


LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelineCreateCommand:
    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline(  # pylint: disable=too-many-locals
        self, dummy_project, fake_kedro_cli, env
    ):
        """Test creation of a pipeline"""
        pipelines_dir = dummy_project / "src" / PACKAGE_NAME / "pipelines"
        assert pipelines_dir.is_dir()

        assert not (pipelines_dir / PIPELINE_NAME).exists()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        cmd += ["-e", env] if env else []
        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert result.exit_code == 0
        assert (
            f"To be able to run the pipeline `{PIPELINE_NAME}`, you will need "
            f"to add it to `create_pipelines()`" in result.output
        )

        # pipeline
        assert f"Creating the pipeline `{PIPELINE_NAME}`: OK" in result.output
        assert f"Location: `{pipelines_dir / PIPELINE_NAME}`" in result.output
        assert f"Pipeline `{PIPELINE_NAME}` was successfully created." in result.output

        # config
        conf_env = env or "base"
        conf_dir = (
            dummy_project / "conf" / conf_env / "pipelines" / PIPELINE_NAME
        ).resolve()
        expected_configs = {"parameters.yml"}
        actual_configs = {f.name for f in conf_dir.iterdir()}
        assert actual_configs == expected_configs

        # tests
        test_dir = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        expected_files = {"__init__.py", "test_pipeline.py"}
        actual_files = {f.name for f in test_dir.iterdir()}
        assert actual_files == expected_files

    @pytest.mark.parametrize("env", [None, "local"])
    def test_create_pipeline_skip_config(self, dummy_project, fake_kedro_cli, env):
        """Test creation of a pipeline with no config"""

        cmd = ["pipeline", "create", "--skip-config", PIPELINE_NAME]
        cmd += ["-e", env] if env else []

        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert result.exit_code == 0
        assert (
            f"To be able to run the pipeline `{PIPELINE_NAME}`, you will need "
            f"to add it to `create_pipelines()`" in result.output
        )
        assert f"Creating the pipeline `{PIPELINE_NAME}`: OK" in result.output
        assert f"Pipeline `{PIPELINE_NAME}` was successfully created." in result.output

        conf_dirs = list((dummy_project / "conf").rglob(PIPELINE_NAME))
        assert conf_dirs == []  # no configs created for the pipeline

        test_dir = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        assert test_dir.is_dir()

    def test_catalog_and_params(self, dummy_project, fake_kedro_cli):
        """Test that catalog and parameter configs generated in pipeline
        sections propagate into the context"""
        pipelines_dir = dummy_project / "src" / PACKAGE_NAME / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert result.exit_code == 0

        # write pipeline catalog
        pipe_conf_dir = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        catalog_dict = {
            "ds_from_pipeline": {
                "type": "pandas.CSVDataSet",
                "filepath": "data/01_raw/iris.csv",
            }
        }
        with (pipe_conf_dir / "catalog.yml").open("w") as f:
            yaml.dump(catalog_dict, f)

        # write pipeline parameters
        params_dict = {"params_from_pipeline": {"p1": [1, 2, 3], "p2": None}}
        with (pipe_conf_dir / "parameters.yml").open("w") as f:
            yaml.dump(params_dict, f)

        ctx = load_context(Path.cwd())
        assert isinstance(ctx.catalog._data_sets["ds_from_pipeline"], CSVDataSet)
        assert isinstance(ctx.catalog.load("ds_from_pipeline"), DataFrame)
        assert ctx.params["params_from_pipeline"] == params_dict["params_from_pipeline"]

    def test_skip_copy(self, dummy_project, fake_kedro_cli):
        """Test skipping the copy of conf and test files if those already exist"""
        # touch pipeline
        catalog = (
            dummy_project
            / "conf"
            / "base"
            / "pipelines"
            / PIPELINE_NAME
            / "catalog.yml"
        )
        catalog.parent.mkdir(parents=True)
        catalog.touch()

        # touch test __init__.py
        tests_init = (
            dummy_project
            / "src"
            / "tests"
            / "pipelines"
            / PIPELINE_NAME
            / "__init__.py"
        )
        tests_init.parent.mkdir(parents=True)
        tests_init.touch()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)

        assert result.exit_code == 0
        assert "__init__.py`: SKIPPED" in result.output
        assert result.output.count("SKIPPED") == 1  # only 1 file skipped

    def test_failed_copy(self, dummy_project, fake_kedro_cli, mocker):
        """Test the error if copying some file fails"""
        error = Exception("Mock exception")
        mocked_copy = mocker.patch("shutil.copyfile", side_effect=error)

        cmd = ["pipeline", "create", PIPELINE_NAME]
        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        mocked_copy.assert_called_once()
        assert result.exit_code
        assert result.output.count("FAILED") == 1
        assert result.exception is error

        # but the pipeline is created anyways
        pipelines_dir = dummy_project / "src" / PACKAGE_NAME / "pipelines"
        assert (pipelines_dir / PIPELINE_NAME / "pipeline.py").is_file()

    def test_no_pipeline_arg_error(self, dummy_project, fake_kedro_cli):
        """Test the error when no pipeline name was provided"""
        pipelines_dir = dummy_project / "src" / PACKAGE_NAME / "pipelines"
        assert pipelines_dir.is_dir()

        result = CliRunner().invoke(fake_kedro_cli.cli, ["pipeline", "create"])
        assert result.exit_code
        assert "Missing argument 'NAME'" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(self, fake_kedro_cli, bad_name, error_message):
        """Test error message when bad pipeline name was provided"""
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", bad_name]
        )
        assert result.exit_code
        assert error_message in result.output

    def test_duplicate_pipeline_name(self, dummy_project, fake_kedro_cli):
        """Test error when attempting to create pipelines with duplicate names"""
        pipelines_dir = dummy_project / "src" / PACKAGE_NAME / "pipelines"
        assert pipelines_dir.is_dir()

        cmd = ["pipeline", "create", PIPELINE_NAME]
        first = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert first.exit_code == 0

        second = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert second.exit_code
        assert f"Creating the pipeline `{PIPELINE_NAME}`: FAILED" in second.output
        assert "directory already exists" in second.output

    def test_bad_env(self, fake_kedro_cli):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["pipeline", "create", "-e", env, PIPELINE_NAME]
        result = CliRunner().invoke(fake_kedro_cli.cli, cmd)
        assert result.exit_code
        assert f"Unable to load Kedro context with environment `{env}`" in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "make_pipelines")
class TestPipelineDeleteCommand:
    @pytest.mark.parametrize(
        "make_pipelines,env,expected_conf",
        [("base", None, "base"), ("local", "local", "local")],
        indirect=["make_pipelines"],
    )
    def test_delete_pipeline(self, env, expected_conf, dummy_project, fake_kedro_cli):
        options = ["--env", env] if env else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", "-y", PIPELINE_NAME, *options]
        )

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        tests_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        conf_path = dummy_project / "conf" / expected_conf / "pipelines" / PIPELINE_NAME

        assert f"Deleting `{source_path}`: OK" in result.output
        assert f"Deleting `{tests_path}`: OK" in result.output
        assert f"Deleting `{conf_path}`: OK" in result.output

        assert f"Pipeline `{PIPELINE_NAME}` was successfully deleted." in result.output
        assert (
            f"If you added the pipeline `{PIPELINE_NAME}` to `create_pipelines()` in "
            f"`{dummy_project / 'src' / PACKAGE_NAME / 'pipeline.py'}`, "
            f"you will need to remove it.`"
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not conf_path.exists()

    def test_delete_pipeline_skip(self, dummy_project, fake_kedro_cli):
        """Tests that delete pipeline handles missing or already deleted files gracefully"""
        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME

        shutil.rmtree(str(source_path))

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", "-y", PIPELINE_NAME]
        )
        tests_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        conf_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME

        assert f"Deleting `{source_path}`" not in result.output
        assert f"Deleting `{tests_path}`: OK" in result.output
        assert f"Deleting `{conf_path}`: OK" in result.output

        assert f"Pipeline `{PIPELINE_NAME}` was successfully deleted." in result.output
        assert (
            f"If you added the pipeline `{PIPELINE_NAME}` to `create_pipelines()` in "
            f"`{dummy_project / 'src' / PACKAGE_NAME / 'pipeline.py'}`, "
            f"you will need to remove it.`"
        ) in result.output

        assert not source_path.exists()
        assert not tests_path.exists()
        assert not conf_path.exists()

    def test_delete_pipeline_fail(self, dummy_project, fake_kedro_cli, mocker):
        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME

        mocker.patch(
            "kedro.framework.cli.pipeline.shutil.rmtree",
            side_effect=PermissionError("permission"),
        )
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", "-y", PIPELINE_NAME]
        )

        assert result.exit_code, result.output
        assert f"Deleting `{source_path}`: FAILED" in result.output

    @pytest.mark.parametrize(
        "bad_name,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_bad_pipeline_name(self, fake_kedro_cli, bad_name, error_message):
        """Test error message when bad pipeline name was provided."""
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", "-y", bad_name]
        )
        assert result.exit_code
        assert error_message in result.output

    def test_bad_env(self, fake_kedro_cli):
        """Test error when provided conf environment does not exist."""
        result = CliRunner().invoke(
            fake_kedro_cli.cli,
            ["pipeline", "delete", "-y", "-e", "invalid_env", PIPELINE_NAME],
        )
        assert result.exit_code
        assert (
            "Unable to load Kedro context with environment `invalid_env`"
            in result.output
        )

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation(self, dummy_project, fake_kedro_cli, input_):
        """Test that user confirmation of deletion works"""
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", PIPELINE_NAME], input=input_
        )

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        tests_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        conf_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME

        assert (
            "The following directories and everything within them will be removed"
            in result.output
        )
        assert str(source_path) in result.output
        assert str(tests_path) in result.output
        assert str(conf_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline `{PIPELINE_NAME}`"
            in result.output
        )
        assert "Deletion aborted!" in result.output

        assert source_path.is_dir()
        assert tests_path.is_dir()
        assert conf_path.is_dir()

    @pytest.mark.parametrize("input_", ["n", "N", "random"])
    def test_pipeline_delete_confirmation_skip(
        self, dummy_project, fake_kedro_cli, input_
    ):
        """Test that user confirmation of deletion works when
        some of the files are missing or already deleted
        """

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        shutil.rmtree(str(source_path))
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", PIPELINE_NAME], input=input_
        )

        tests_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        conf_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME

        assert (
            "The following directories and everything within them will be removed"
            in result.output
        )
        assert str(source_path) not in result.output
        assert str(tests_path) in result.output
        assert str(conf_path) in result.output

        assert (
            f"Are you sure you want to delete pipeline `{PIPELINE_NAME}`"
            in result.output
        )
        assert "Deletion aborted!" in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
def test_list_pipelines(fake_kedro_cli, yaml_dump_mock, pipelines_dict):
    result = CliRunner().invoke(fake_kedro_cli.cli, ["pipeline", "list"])

    assert not result.exit_code
    yaml_dump_mock.assert_called_once_with(sorted(pipelines_dict.keys()))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelineDescribeCommand:
    @pytest.mark.parametrize("pipeline_name", ["de", "ds", "__default__"])
    def test_describe_pipeline(
        self, fake_kedro_cli, yaml_dump_mock, pipeline_name, pipelines_dict
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "describe", pipeline_name]
        )

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict[pipeline_name]}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_not_found_pipeline(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "describe", "missing"]
        )

        assert result.exit_code
        expected_output = (
            "Error: `missing` pipeline not found. Existing pipelines: "
            "[__default__, de, ds]\n"
        )
        assert result.output == expected_output


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_dist")
class TestPipelinePackageCommand:
    @pytest.mark.parametrize(
        "alias_opt,package_name,success_message",
        [
            ([], PIPELINE_NAME, f"Pipeline `{PIPELINE_NAME}` packaged!"),
            (
                ["--alias", "alternative"],
                "alternative",
                f"Pipeline `{PIPELINE_NAME}` packaged as `alternative`!",
            ),
        ],
    )
    def test_package_pipeline(
        self, dummy_project, fake_kedro_cli, alias_opt, package_name, success_message
    ):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", PIPELINE_NAME]
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "package", PIPELINE_NAME] + alias_opt
        )

        assert result.exit_code == 0
        assert success_message in result.output

        wheel_location = dummy_project / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        wheel_file = wheel_location / f"{package_name}-0.1-py3-none-any.whl"
        assert wheel_file.is_file()
        assert len(list((wheel_location).iterdir())) == 1

        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        expected_files = {
            f"{package_name}/__init__.py",
            f"{package_name}/README.md",
            f"{package_name}/nodes.py",
            f"{package_name}/pipeline.py",
            f"{package_name}/config/parameters.yml",
            "tests/__init__.py",
            "tests/test_pipeline.py",
        }
        assert expected_files <= wheel_contents

    @pytest.mark.parametrize("existing_dir", [True, False])
    def test_pipeline_package_to_destination(
        self, fake_kedro_cli, existing_dir, tmp_path
    ):
        destination = (tmp_path / "in" / "here").resolve()
        if existing_dir:
            destination.mkdir(parents=True)

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", PIPELINE_NAME]
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_kedro_cli.cli,
            ["pipeline", "package", PIPELINE_NAME, "--destination", str(destination)],
        )

        assert result.exit_code == 0
        success_message = (
            f"Pipeline `{PIPELINE_NAME}` packaged! Location: {destination}"
        )
        assert success_message in result.output

        wheel_file = destination / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        assert wheel_file.is_file()

        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        expected_files = {
            f"{PIPELINE_NAME}/__init__.py",
            f"{PIPELINE_NAME}/README.md",
            f"{PIPELINE_NAME}/nodes.py",
            f"{PIPELINE_NAME}/pipeline.py",
            f"{PIPELINE_NAME}/config/parameters.yml",
            "tests/__init__.py",
            "tests/test_pipeline.py",
        }
        assert expected_files <= wheel_contents

    def test_pipeline_package_overwrites_wheel(self, fake_kedro_cli, tmp_path):
        destination = (tmp_path / "in" / "here").resolve()
        destination.mkdir(parents=True)
        wheel_file = destination / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        wheel_file.touch()

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", PIPELINE_NAME]
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_kedro_cli.cli,
            ["pipeline", "package", PIPELINE_NAME, "--destination", str(destination)],
        )
        assert result.exit_code == 0

        warning_message = f"Package file {wheel_file} will be overwritten!"
        success_message = (
            f"Pipeline `{PIPELINE_NAME}` packaged! Location: {destination}"
        )
        assert warning_message in result.output
        assert success_message in result.output

        assert wheel_file.is_file()
        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        expected_files = {
            f"{PIPELINE_NAME}/__init__.py",
            f"{PIPELINE_NAME}/README.md",
            f"{PIPELINE_NAME}/nodes.py",
            f"{PIPELINE_NAME}/pipeline.py",
            f"{PIPELINE_NAME}/config/parameters.yml",
            "tests/__init__.py",
            "tests/test_pipeline.py",
        }
        assert expected_files <= wheel_contents

    @pytest.mark.parametrize(
        "bad_alias,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_package_pipeline_bad_alias(self, fake_kedro_cli, bad_alias, error_message):
        result = CliRunner().invoke(
            fake_kedro_cli.cli,
            ["pipeline", "package", PIPELINE_NAME, "--alias", bad_alias],
        )
        assert result.exit_code
        assert error_message in result.output

    def test_package_pipeline_no_config(self, dummy_project, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", PIPELINE_NAME, "--skip-config"]
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "package", PIPELINE_NAME]
        )

        assert result.exit_code == 0
        assert f"Pipeline `{PIPELINE_NAME}` packaged!" in result.output
        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()
        assert len(list((dummy_project / "src" / "dist").iterdir())) == 1

        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        expected_files = {
            f"{PIPELINE_NAME}/__init__.py",
            f"{PIPELINE_NAME}/README.md",
            f"{PIPELINE_NAME}/nodes.py",
            f"{PIPELINE_NAME}/pipeline.py",
            "tests/__init__.py",
            "tests/test_pipeline.py",
        }
        assert expected_files <= wheel_contents
        assert f"{PIPELINE_NAME}/config/parameters.yml" not in wheel_contents


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_dist")
class TestPipelinePullCommand:
    def call_pipeline_create(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "create", PIPELINE_NAME]
        )
        assert result.exit_code == 0

    def call_pipeline_package(self, fake_kedro_cli, alias=None, destination=None):
        options = ["--alias", alias] if alias else []
        options += ["--destination", str(destination)] if destination else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "package", PIPELINE_NAME, *options]
        )
        assert result.exit_code == 0

    def call_pipeline_delete(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "delete", "-y", PIPELINE_NAME]
        )
        assert result.exit_code == 0

    def assert_package_files_exist(self, source_path):
        assert {f.name for f in source_path.iterdir()} == {
            "__init__.py",
            "nodes.py",
            "pipeline.py",
            "README.md",
        }

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_local_whl(self, fake_kedro_cli, dummy_project, env, alias):
        """
        Test for pulling a valid wheel file locally.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_kedro_cli)
        self.call_pipeline_package(fake_kedro_cli)
        self.call_pipeline_delete(fake_kedro_cli)

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not test_path.exists()
        assert not config_path.exists()

        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file), *options]
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        self.assert_package_files_exist(source_dest)
        assert (config_dest / "parameters.yml").is_file()
        assert {f.name for f in test_dest.iterdir()} == {
            "__init__.py",
            "test_pipeline.py",
        }

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_local_whl_compare(self, fake_kedro_cli, dummy_project, env, alias):
        """
        Test for pulling a valid wheel file locally, unpack it into another location and
        check that unpacked files are identical to the ones in the original modular pipeline.
        """
        # pylint: disable=too-many-locals
        pipeline_name = "another_pipeline"
        self.call_pipeline_create(fake_kedro_cli)
        self.call_pipeline_package(fake_kedro_cli, pipeline_name)

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME

        wheel_file = (
            dummy_project / "src" / "dist" / f"{pipeline_name}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file), *options]
        )
        assert result.exit_code == 0

        pipeline_name = alias or pipeline_name
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        assert not filecmp.dircmp(source_path, source_dest).diff_files
        assert not filecmp.dircmp(config_path, config_dest).diff_files
        assert not filecmp.dircmp(test_path, test_dest).diff_files

    def test_pull_two_dist_info(self, fake_kedro_cli, dummy_project, mocker, tmp_path):
        """
        Test for pulling a wheel file with more than one dist-info directory.
        """
        self.call_pipeline_package(fake_kedro_cli)
        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        (tmp_path / "dummy.dist-info").mkdir()

        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file)]
        )
        assert result.exit_code
        assert "Error: More than 1 or no dist-info files found" in result.output

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_tests_missing(self, fake_kedro_cli, dummy_project, env, alias):
        """
        Test for pulling a valid wheel file locally, but `tests` directory is missing
        from the wheel file.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_kedro_cli)
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        shutil.rmtree(test_path)
        assert not test_path.exists()
        self.call_pipeline_package(fake_kedro_cli)
        self.call_pipeline_delete(fake_kedro_cli)

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not config_path.exists()

        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file), *options]
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        self.assert_package_files_exist(source_dest)
        assert (config_dest / "parameters.yml").is_file()
        assert not test_dest.exists()

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_config_missing(self, fake_kedro_cli, dummy_project, env, alias):
        """
        Test for pulling a valid wheel file locally, but `config` directory is missing
        from the wheel file.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_kedro_cli)
        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        shutil.rmtree(config_path)
        assert not config_path.exists()
        self.call_pipeline_package(fake_kedro_cli)
        self.call_pipeline_delete(fake_kedro_cli)

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not test_path.exists()

        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file), *options]
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        self.assert_package_files_exist(source_dest)
        assert not config_dest.exists()
        assert {f.name for f in test_dest.iterdir()} == {
            "__init__.py",
            "test_pipeline.py",
        }

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_pipeline_missing(self, fake_kedro_cli, dummy_project, env, alias):
        """
        Test for pulling a valid wheel file locally, but `pipeline.py` is missing from the wheel
        file.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_kedro_cli)
        package_path = (
            dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        )
        shutil.rmtree(package_path)
        assert not package_path.exists()
        self.call_pipeline_package(fake_kedro_cli)
        self.call_pipeline_delete(fake_kedro_cli)

        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not test_path.exists()
        assert not config_path.exists()

        wheel_file = (
            dummy_project / "src" / "dist" / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", str(wheel_file), *options]
        )
        assert not result.exit_code

        pipeline_name = alias or PIPELINE_NAME
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        assert not source_dest.exists()
        assert not (config_dest / "parameters.yml").is_file()
        assert {f.name for f in test_dest.iterdir()} == {
            "__init__.py",
            "test_pipeline.py",
        }

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_from_pypi(
        self, fake_kedro_cli, dummy_project, mocker, tmp_path, env, alias
    ):
        """
        Test for pulling a valid wheel file from pypi.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_kedro_cli)
        # We mock the `pip download` call, and manually create a package wheel file
        # to simulate the pypi scenario instead
        self.call_pipeline_package(fake_kedro_cli, destination=tmp_path)
        wheel_file = tmp_path / f"{PIPELINE_NAME}-0.1-py3-none-any.whl"
        assert wheel_file.is_file()
        self.call_pipeline_delete(fake_kedro_cli)

        source_path = dummy_project / "src" / PACKAGE_NAME / "pipelines" / PIPELINE_NAME
        config_path = dummy_project / "conf" / "base" / "pipelines" / PIPELINE_NAME
        test_path = dummy_project / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from pypi.
        assert not source_path.exists()
        assert not test_path.exists()
        assert not config_path.exists()

        python_call_mock = mocker.patch("kedro.framework.cli.pipeline.python_call")
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", PIPELINE_NAME, *options]
        )
        assert result.exit_code == 0

        python_call_mock.assert_called_once_with(
            "pip", ["download", "--no-deps", "--dest", str(tmp_path), PIPELINE_NAME]
        )

        pipeline_name = alias or PIPELINE_NAME
        source_dest = dummy_project / "src" / PACKAGE_NAME / "pipelines" / pipeline_name
        config_env = env or "base"
        config_dest = dummy_project / "conf" / config_env / "pipelines" / pipeline_name
        test_dest = dummy_project / "src" / "tests" / "pipelines" / pipeline_name

        self.assert_package_files_exist(source_dest)
        assert (config_dest / "parameters.yml").is_file()
        assert {f.name for f in test_dest.iterdir()} == {
            "__init__.py",
            "test_pipeline.py",
        }

    def test_invalid_pull_from_pypi(self, fake_kedro_cli, mocker, tmp_path):
        """
        Test for pulling package from pypi, and it cannot be found.
        """

        pypi_error_message = (
            "ERROR: Could not find a version that satisfies the requirement"
        )
        python_call_mock = mocker.patch(
            "kedro.framework.cli.pipeline.python_call",
            side_effect=click.ClickException(pypi_error_message),
        )
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )

        invalid_pypi_name = "non_existent"
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", invalid_pypi_name]
        )
        assert result.exit_code

        python_call_mock.assert_called_once_with(
            "pip", ["download", "--no-deps", "--dest", str(tmp_path), invalid_pypi_name]
        )

        assert pypi_error_message in result.stdout

    def test_pull_from_pypi_more_than_one_wheel_file(
        self, fake_kedro_cli, mocker, tmp_path
    ):
        """
        Test for pulling a wheel file with `pip download`, but there are more than one wheel
        file to unzip.
        """
        # We mock the `pip download` call, and manually create a package wheel file
        # to simulate the pypi scenario instead
        self.call_pipeline_package(fake_kedro_cli, destination=tmp_path)
        self.call_pipeline_package(
            fake_kedro_cli, alias="another", destination=tmp_path
        )
        mocker.patch("kedro.framework.cli.pipeline.python_call")
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["pipeline", "pull", PIPELINE_NAME]
        )

        assert result.exit_code
        assert "Error: More than 1 or no wheel files found:" in result.output


class TestSyncDirs:
    @pytest.fixture(autouse=True)
    def mock_click(self, mocker):
        mocker.patch("click.secho")

    @pytest.fixture
    def source(self, tmp_path) -> Path:
        source_dir = Path(tmp_path) / "source"
        source_dir.mkdir()
        (source_dir / "existing").mkdir()
        (source_dir / "existing" / "source_file").touch()
        (source_dir / "existing" / "common").write_text("source")
        (source_dir / "new").mkdir()
        (source_dir / "new" / "source_file").touch()
        return source_dir

    def test_sync_target_exists(self, source, tmp_path):
        """Test _sync_dirs utility function if target exists."""
        target = Path(tmp_path) / "target"
        target.mkdir()
        (target / "existing").mkdir()
        (target / "existing" / "target_file").touch()
        (target / "existing" / "common").write_text("target")

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text() == "target"
        assert (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()

    def test_sync_no_target(self, source, tmp_path):
        """Test _sync_dirs utility function if target doesn't exist."""
        target = Path(tmp_path) / "target"

        _sync_dirs(source, target)

        assert (source / "existing" / "source_file").is_file()
        assert (source / "existing" / "common").read_text() == "source"
        assert not (source / "existing" / "target_file").exists()
        assert (source / "new" / "source_file").is_file()

        assert (target / "existing" / "source_file").is_file()
        assert (target / "existing" / "common").read_text() == "source"
        assert not (target / "existing" / "target_file").exists()
        assert (target / "new" / "source_file").is_file()
