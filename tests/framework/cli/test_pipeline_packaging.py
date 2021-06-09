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
import filecmp
import shutil
from pathlib import Path
from zipfile import ZipFile

import pytest
import yaml
from click import ClickException
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_wheel_name
from kedro.framework.project import settings

PIPELINE_NAME = "my_pipeline"

LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture(autouse=True)
def cleanup_pipelines(fake_repo_path, fake_package_path):
    pipes_path = fake_package_path / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = fake_repo_path / settings.CONF_ROOT
        for each in confs.rglob(f"*{pipeline}*"):  # clean all pipeline config files
            if each.is_file():
                each.unlink()

        dirs_to_delete = (
            dirpath
            for pattern in ("parameters", "catalog")
            for dirpath in confs.rglob(pattern)
            if dirpath.is_dir() and not any(dirpath.iterdir())
        )
        for dirpath in dirs_to_delete:
            dirpath.rmdir()

        tests = fake_repo_path / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))


@pytest.fixture(autouse=True)
def cleanup_dist(fake_repo_path):
    yield
    dist_dir = fake_repo_path / "src" / "dist"
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelinePackageCommand:
    def assert_wheel_contents_correct(
        self, wheel_location, package_name=PIPELINE_NAME, version="0.1"
    ):
        wheel_name = _get_wheel_name(name=package_name, version=version)
        wheel_file = wheel_location / wheel_name
        assert wheel_file.is_file()
        assert len(list((wheel_location).iterdir())) == 1

        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        expected_files = {
            f"{package_name}/__init__.py",
            f"{package_name}/README.md",
            f"{package_name}/nodes.py",
            f"{package_name}/pipeline.py",
            f"{package_name}/config/parameters/{package_name}.yml",
            "tests/__init__.py",
            "tests/test_pipeline.py",
        }
        assert expected_files <= wheel_contents

    @pytest.mark.parametrize(
        "options,package_name,version,success_message",
        [
            ([], PIPELINE_NAME, "0.1", f"Pipeline `{PIPELINE_NAME}` packaged!"),
            (
                ["--alias", "alternative"],
                "alternative",
                "0.1",
                f"Pipeline `{PIPELINE_NAME}` packaged as `alternative`!",
            ),
            (
                ["--version", "0.3"],
                PIPELINE_NAME,
                "0.3",
                f"Pipeline `{PIPELINE_NAME}` packaged!",
            ),
        ],
    )
    def test_package_pipeline(
        self,
        fake_repo_path,
        fake_project_cli,
        options,
        package_name,
        version,
        success_message,
        fake_metadata,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", PIPELINE_NAME],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME] + options,
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert success_message in result.output

        wheel_location = fake_repo_path / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        self.assert_wheel_contents_correct(
            wheel_location=wheel_location, package_name=package_name, version=version
        )

    @pytest.mark.parametrize("existing_dir", [True, False])
    def test_pipeline_package_to_destination(
        self, fake_project_cli, existing_dir, tmp_path, fake_metadata
    ):
        destination = (tmp_path / "in" / "here").resolve()
        if existing_dir:
            destination.mkdir(parents=True)

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", PIPELINE_NAME],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME, "--destination", str(destination)],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        success_message = (
            f"Pipeline `{PIPELINE_NAME}` packaged! Location: {destination}"
        )
        assert success_message in result.output

        self.assert_wheel_contents_correct(wheel_location=destination)

    def test_pipeline_package_overwrites_wheel(
        self, fake_project_cli, tmp_path, fake_metadata
    ):
        destination = (tmp_path / "in" / "here").resolve()
        destination.mkdir(parents=True)
        wheel_file = destination / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        wheel_file.touch()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", PIPELINE_NAME],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME, "--destination", str(destination)],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        warning_message = f"Package file {wheel_file} will be overwritten!"
        success_message = (
            f"Pipeline `{PIPELINE_NAME}` packaged! Location: {destination}"
        )
        assert warning_message in result.output
        assert success_message in result.output

        self.assert_wheel_contents_correct(wheel_location=destination)

    @pytest.mark.parametrize(
        "bad_alias,error_message",
        [
            ("bad name", LETTER_ERROR),
            ("bad%name", LETTER_ERROR),
            ("1bad", FIRST_CHAR_ERROR),
            ("a", TOO_SHORT_ERROR),
        ],
    )
    def test_package_pipeline_bad_alias(
        self, fake_project_cli, bad_alias, error_message
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME, "--alias", bad_alias],
        )
        assert result.exit_code
        assert error_message in result.output

    def test_package_pipeline_no_config(
        self, fake_repo_path, fake_project_cli, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", PIPELINE_NAME, "--skip-config"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert f"Pipeline `{PIPELINE_NAME}` packaged!" in result.output

        wheel_location = fake_repo_path / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        # the wheel contents are slightly different (config shouldn't be included),
        # which is why we can't call self.assert_wheel_contents_correct here
        wheel_file = wheel_location / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        assert wheel_file.is_file()
        assert len(list((fake_repo_path / "src" / "dist").iterdir())) == 1

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

    def test_package_non_existing_pipeline_dir(
        self, fake_package_path, fake_project_cli, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", "non_existing"],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        pipeline_dir = fake_package_path / "pipelines" / "non_existing"
        error_message = f"Error: Directory '{pipeline_dir}' doesn't exist."
        assert error_message in result.output

    def test_package_empty_pipeline_dir(
        self, fake_project_cli, fake_package_path, fake_metadata
    ):
        pipeline_dir = fake_package_path / "pipelines" / "empty_dir"
        pipeline_dir.mkdir()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", "empty_dir"],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        error_message = f"Error: '{pipeline_dir}' is an empty directory."
        assert error_message in result.output

    def test_package_modular_pipeline_with_nested_parameters(
        self,
        fake_repo_path,
        fake_project_cli,
        fake_metadata,
    ):
        """
        The setup for the test is as follows:

        Create two modular pipelines, to verify that only the parameter file with matching pipeline
        name will be packaged.

        Add a directory with a parameter file to verify that if a project has parameters structured
        like below, that the ones inside a directory with the pipeline name are packaged as well
        when calling `kedro pipeline package` for a specific pipeline.

        parameters
            └── retail
                └── params1.ym
        """
        CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", "retail"],
            obj=fake_metadata,
        )
        CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", "retail_banking"],
            obj=fake_metadata,
        )
        nested_param_path = Path(
            fake_repo_path / "conf" / "base" / "parameters" / "retail"
        )
        nested_param_path.mkdir(parents=True, exist_ok=True)
        (nested_param_path / "params1.yml").touch()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", "retail"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert "Pipeline `retail` packaged!" in result.output

        wheel_location = fake_repo_path / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        wheel_name = _get_wheel_name(name="retail", version="0.1")
        wheel_file = wheel_location / wheel_name
        assert wheel_file.is_file()
        assert len(list(wheel_location.iterdir())) == 1

        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        assert "retail/config/parameters/retail/params1.yml" in wheel_contents
        assert "retail/config/parameters/retail.yml" in wheel_contents
        assert "retail/config/parameters/retail_banking.yml" not in wheel_contents


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestPipelinePullCommand:
    def call_pipeline_create(self, cli, metadata):
        result = CliRunner().invoke(
            cli, ["pipeline", "create", PIPELINE_NAME], obj=metadata
        )
        assert result.exit_code == 0

    def call_pipeline_package(
        self, fake_kedro_cli, metadata, alias=None, destination=None
    ):
        options = ["--alias", alias] if alias else []
        options += ["--destination", str(destination)] if destination else []
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["pipeline", "package", PIPELINE_NAME, *options],
            obj=metadata,
        )
        assert result.exit_code == 0

    def call_pipeline_delete(self, cli, metadata):
        result = CliRunner().invoke(
            cli, ["pipeline", "delete", "-y", PIPELINE_NAME], obj=metadata
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
    def test_pull_local_whl(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        fake_metadata,
    ):
        """
        Test for pulling a valid wheel file locally.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        config_path = (
            fake_repo_path / settings.CONF_ROOT / "base" / "pipelines" / PIPELINE_NAME
        )
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not test_path.exists()
        assert not config_path.exists()

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / "pipelines" / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / "pipelines" / pipeline_name
        config_env = env or "base"
        params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        self.assert_package_files_exist(source_dest)
        assert params_config.is_file()
        actual_test_files = {f.name for f in test_dest.iterdir()}
        extected_test_files = {"__init__.py", "test_pipeline.py"}
        assert actual_test_files == extected_test_files

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_local_whl_compare(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        fake_metadata,
    ):
        """
        Test for pulling a valid wheel file locally, unpack it into another location and
        check that unpacked files are identical to the ones in the original modular pipeline.
        """
        # pylint: disable=too-many-locals
        pipeline_name = "another_pipeline"
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata, pipeline_name)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        source_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=pipeline_name, version="0.1")
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or pipeline_name
        source_dest = fake_package_path / "pipelines" / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / "pipelines" / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        assert not filecmp.dircmp(source_path, source_dest).diff_files
        assert not filecmp.dircmp(test_path, test_dest).diff_files
        assert source_params_config.read_bytes() == dest_params_config.read_bytes()

    def test_pull_whl_fs_args(
        self, fake_project_cli, fake_repo_path, mocker, tmp_path, fake_metadata
    ):
        """
        Test for pulling a wheel file with custom fs_args specified.
        """
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)

        fs_args_config = tmp_path / "fs_args_config.yml"
        with fs_args_config.open(mode="w") as f:
            yaml.dump({"fs_arg_1": 1, "fs_arg_2": {"fs_arg_2_nested_1": 2}}, f)
        mocked_filesystem = mocker.patch("fsspec.filesystem")

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )

        options = ["--fs-args", str(fs_args_config)]
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(wheel_file), *options]
        )

        mocked_filesystem.assert_called_once_with(
            "file", fs_arg_1=1, fs_arg_2=dict(fs_arg_2_nested_1=2)
        )

    def test_pull_two_dist_info(
        self, fake_project_cli, fake_repo_path, mocker, tmp_path, fake_metadata
    ):
        """
        Test for pulling a wheel file with more than one dist-info directory.
        """
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        (tmp_path / "dummy.dist-info").mkdir()

        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file)],
            obj=fake_metadata,
        )
        assert result.exit_code
        assert "Error: More than 1 or no dist-info files found" in result.output

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_tests_missing(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        fake_metadata,
    ):
        """
        Test for pulling a valid wheel file locally, but `tests` directory is missing
        from the wheel file.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        shutil.rmtree(test_path)
        assert not test_path.exists()
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        source_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not source_params_config.exists()

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / "pipelines" / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / "pipelines" / pipeline_name
        config_env = env or "base"
        params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        self.assert_package_files_exist(source_dest)
        assert params_config.is_file()
        assert not test_dest.exists()

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_config_missing(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        fake_metadata,
    ):
        """
        Test for pulling a valid wheel file locally, but `config` directory is missing
        from the wheel file.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        source_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        source_params_config.unlink()
        self.call_pipeline_package(fake_project_cli, fake_metadata)
        self.call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the wheel file.
        assert not source_path.exists()
        assert not test_path.exists()

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / "pipelines" / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / "pipelines" / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        self.assert_package_files_exist(source_dest)
        assert not dest_params_config.exists()
        actual_test_files = {f.name for f in test_dest.iterdir()}
        expected_test_files = {"__init__.py", "test_pipeline.py"}
        assert actual_test_files == expected_test_files

    @pytest.mark.parametrize("env", [None, "local"])
    @pytest.mark.parametrize("alias", [None, "alias_path"])
    def test_pull_from_pypi(
        self,
        fake_project_cli,
        fake_repo_path,
        mocker,
        tmp_path,
        fake_package_path,
        env,
        alias,
        fake_metadata,
    ):
        """
        Test for pulling a valid wheel file from pypi.
        """
        # pylint: disable=too-many-locals
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        # We mock the `pip download` call, and manually create a package wheel file
        # to simulate the pypi scenario instead
        self.call_pipeline_package(
            fake_project_cli, fake_metadata, destination=tmp_path
        )
        wheel_file = tmp_path / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        assert wheel_file.is_file()
        self.call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        source_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        # Make sure the files actually deleted before pulling from pypi.
        assert not source_path.exists()
        assert not test_path.exists()
        assert not source_params_config.exists()

        python_call_mock = mocker.patch("kedro.framework.cli.pipeline.python_call")
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", PIPELINE_NAME, *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        python_call_mock.assert_called_once_with(
            "pip",
            ["download", "--no-deps", "--dest", str(tmp_path), PIPELINE_NAME],
        )

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / "pipelines" / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / "pipelines" / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        self.assert_package_files_exist(source_dest)
        assert dest_params_config.is_file()
        actual_test_files = {f.name for f in test_dest.iterdir()}
        expected_test_files = {"__init__.py", "test_pipeline.py"}
        assert actual_test_files == expected_test_files

    def test_invalid_pull_from_pypi(
        self, fake_project_cli, mocker, tmp_path, fake_metadata
    ):
        """
        Test for pulling package from pypi, and it cannot be found.
        """

        pypi_error_message = (
            "ERROR: Could not find a version that satisfies the requirement"
        )
        python_call_mock = mocker.patch(
            "kedro.framework.cli.pipeline.python_call",
            side_effect=ClickException(pypi_error_message),
        )
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )

        invalid_pypi_name = "non_existent"
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", invalid_pypi_name],
            obj=fake_metadata,
        )
        assert result.exit_code

        python_call_mock.assert_called_once_with(
            "pip", ["download", "--no-deps", "--dest", str(tmp_path), invalid_pypi_name]
        )

        assert pypi_error_message in result.stdout

    def test_pull_from_pypi_more_than_one_wheel_file(
        self, fake_project_cli, mocker, tmp_path, fake_metadata
    ):
        """
        Test for pulling a wheel file with `pip download`, but there are more than one wheel
        file to unzip.
        """
        # We mock the `pip download` call, and manually create a package wheel file
        # to simulate the pypi scenario instead
        self.call_pipeline_create(fake_project_cli, fake_metadata)
        self.call_pipeline_package(
            fake_project_cli, fake_metadata, destination=tmp_path
        )
        self.call_pipeline_package(
            fake_project_cli, fake_metadata, alias="another", destination=tmp_path
        )
        mocker.patch("kedro.framework.cli.pipeline.python_call")
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", PIPELINE_NAME], obj=fake_metadata
        )

        assert result.exit_code
        assert "Error: More than 1 or no wheel files found:" in result.output

    def test_pull_unsupported_protocol_by_fsspec(
        self, fake_project_cli, fake_metadata, tmp_path, mocker
    ):
        protocol = "unsupported"
        exception_message = f"Protocol not known: {protocol}"
        error_message = "Error: More than 1 or no wheel files found:"
        package_path = f"{protocol}://{PIPELINE_NAME}"

        python_call_mock = mocker.patch("kedro.framework.cli.pipeline.python_call")
        filesystem_mock = mocker.patch(
            "fsspec.filesystem", side_effect=ValueError(exception_message)
        )
        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", package_path], obj=fake_metadata
        )

        assert result.exit_code
        filesystem_mock.assert_called_once_with(protocol)
        python_call_mock.assert_called_once_with(
            "pip", ["download", "--no-deps", "--dest", str(tmp_path), package_path]
        )
        assert exception_message in result.output
        assert "Trying to use 'pip download'..." in result.output
        assert error_message in result.output
