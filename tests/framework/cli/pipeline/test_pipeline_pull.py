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
import textwrap

import pytest
import toml
import yaml
from click import ClickException
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_wheel_name
from kedro.framework.project import settings

PIPELINE_NAME = "my_pipeline"


def call_pipeline_create(cli, metadata, pipeline_name=PIPELINE_NAME):
    result = CliRunner().invoke(
        cli, ["pipeline", "create", pipeline_name], obj=metadata
    )
    assert result.exit_code == 0


def call_pipeline_package(
    cli, metadata, alias=None, destination=None, pipeline_name=PIPELINE_NAME
):
    options = ["--alias", alias] if alias else []
    options += ["--destination", str(destination)] if destination else []
    result = CliRunner().invoke(
        cli, ["pipeline", "package", pipeline_name, *options], obj=metadata
    )
    assert result.exit_code == 0, result.output


def call_pipeline_delete(cli, metadata, pipeline_name=PIPELINE_NAME):
    result = CliRunner().invoke(
        cli, ["pipeline", "delete", "-y", pipeline_name], obj=metadata
    )
    assert result.exit_code == 0


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_dist")
class TestPipelinePullCommand:
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
        """Test for pulling a valid wheel file locally."""
        # pylint: disable=too-many-locals
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

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
        assert result.exit_code == 0, result.output
        assert "pulled and unpacked" in result.output

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
        expected_test_files = {"__init__.py", "test_pipeline.py"}
        assert actual_test_files == expected_test_files

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
        """Test for pulling a valid wheel file locally, unpack it
        into another location and check that unpacked files
        are identical to the ones in the original modular pipeline.
        """
        # pylint: disable=too-many-locals
        pipeline_name = "another_pipeline"
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata, alias=pipeline_name)

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
        assert result.exit_code == 0, result.output
        assert "pulled and unpacked" in result.output

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

    def test_pipeline_alias_refactors_imports(
        self, fake_project_cli, fake_package_path, fake_repo_path, fake_metadata
    ):
        call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_file = fake_package_path / "pipelines" / PIPELINE_NAME / "pipeline.py"
        import_stmt = (
            f"import {fake_metadata.package_name}.pipelines.{PIPELINE_NAME}.nodes"
        )
        with pipeline_file.open("a") as f:
            f.write(import_stmt)

        package_alias = "alpha"
        pull_alias = "beta"

        call_pipeline_package(
            cli=fake_project_cli, metadata=fake_metadata, alias=package_alias
        )

        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=package_alias, version="0.1")
        )
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(wheel_file)], obj=fake_metadata
        )
        CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), "--alias", pull_alias],
            obj=fake_metadata,
        )

        for alias in (package_alias, pull_alias):
            path = fake_package_path / "pipelines" / alias / "pipeline.py"
            file_content = path.read_text()
            expected_stmt = (
                f"import {fake_metadata.package_name}.pipelines.{alias}.nodes"
            )
            assert expected_stmt in file_content

    def test_pipeline_pull_from_aliased_pipeline_conflicting_name(
        self, fake_project_cli, fake_package_path, fake_repo_path, fake_metadata
    ):
        package_name = fake_metadata.package_name
        call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_file = fake_package_path / "pipelines" / PIPELINE_NAME / "pipeline.py"
        import_stmt = f"import {package_name}.pipelines.{PIPELINE_NAME}.nodes"
        with pipeline_file.open("a") as f:
            f.write(import_stmt)

        call_pipeline_package(
            cli=fake_project_cli, metadata=fake_metadata, alias=package_name
        )
        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=package_name, version="0.1")
        )
        assert wheel_file.is_file()

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(wheel_file)], obj=fake_metadata
        )
        assert result.exit_code == 0, result.output
        # TODO: check imports are refactored

    def test_pipeline_pull_as_aliased_pipeline_conflicting_name(
        self, fake_project_cli, fake_package_path, fake_repo_path, fake_metadata
    ):
        package_name = fake_metadata.package_name
        call_pipeline_create(fake_project_cli, fake_metadata)
        pipeline_file = fake_package_path / "pipelines" / PIPELINE_NAME / "pipeline.py"
        import_stmt = f"import {package_name}.pipelines.{PIPELINE_NAME}.nodes"
        with pipeline_file.open("a") as f:
            f.write(import_stmt)

        call_pipeline_package(cli=fake_project_cli, metadata=fake_metadata)
        wheel_file = (
            fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        )
        assert wheel_file.is_file()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(wheel_file), "--alias", package_name],
            obj=fake_metadata,
        )
        assert result.exit_code == 0, result.output
        # TODO: check imports are refactored

    def test_pull_whl_fs_args(
        self, fake_project_cli, fake_repo_path, mocker, tmp_path, fake_metadata
    ):
        """Test for pulling a wheel file with custom fs_args specified."""
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

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
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
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
            fake_project_cli, ["pipeline", "pull", str(wheel_file)], obj=fake_metadata
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
        """Test for pulling a valid wheel file locally,
        but `tests` directory is missing from the wheel file.
        """
        # pylint: disable=too-many-locals
        call_pipeline_create(fake_project_cli, fake_metadata)
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        shutil.rmtree(test_path)
        assert not test_path.exists()
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

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
        call_pipeline_create(fake_project_cli, fake_metadata)
        source_params_config = (
            fake_repo_path
            / settings.CONF_ROOT
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        source_params_config.unlink()
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

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
        call_pipeline_create(fake_project_cli, fake_metadata)
        # We mock the `pip download` call, and manually create a package wheel file
        # to simulate the pypi scenario instead
        call_pipeline_package(fake_project_cli, fake_metadata, destination=tmp_path)
        wheel_file = tmp_path / _get_wheel_name(name=PIPELINE_NAME, version="0.1")
        assert wheel_file.is_file()
        call_pipeline_delete(fake_project_cli, fake_metadata)

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
        assert "pulled and unpacked" in result.output

        python_call_mock.assert_called_once_with(
            "pip", ["download", "--no-deps", "--dest", str(tmp_path), PIPELINE_NAME]
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
            fake_project_cli, ["pipeline", "pull", invalid_pypi_name], obj=fake_metadata
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
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata, destination=tmp_path)
        call_pipeline_package(
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


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "patch_log", "cleanup_dist", "cleanup_pyproject_toml"
)
class TestPipelinePullFromManifest:
    def test_pipeline_pull_all(  # pylint: disable=too-many-locals
        self, fake_repo_path, fake_project_cli, fake_metadata, mocker
    ):
        # pylint: disable=import-outside-toplevel
        from kedro.framework.cli import pipeline

        spy = mocker.spy(pipeline, "_pull_package")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        wheel_file = (
            lambda name: fake_repo_path
            / "src"
            / "dist"
            / _get_wheel_name(name=name, version="0.1")
        )
        project_toml_str = textwrap.dedent(
            f"""
            [tool.kedro.pipeline.pull]
            "{wheel_file("first")}" = {{alias = "dp"}}
            "{wheel_file("second")}" = {{alias = "ds", env = "local"}}
            "{wheel_file("third")}" = {{}}
            """
        )

        with pyproject_toml.open(mode="a") as file:
            file.write(project_toml_str)

        for name in ("first", "second", "third"):
            call_pipeline_create(fake_project_cli, fake_metadata, pipeline_name=name)
            call_pipeline_package(fake_project_cli, fake_metadata, pipeline_name=name)
            call_pipeline_delete(fake_project_cli, fake_metadata, pipeline_name=name)

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        assert "Pipelines pulled and unpacked!" in result.output
        assert spy.call_count == 3

        build_config = toml.loads(project_toml_str)
        pull_manifest = build_config["tool"]["kedro"]["pipeline"]["pull"]
        for wheel_file, pull_specs in pull_manifest.items():
            expected_call = mocker.call(wheel_file, fake_metadata, **pull_specs)
            assert expected_call in spy.call_args_list

    def test_pipeline_pull_all_empty_toml(
        self, fake_repo_path, fake_project_cli, fake_metadata, mocker
    ):
        # pylint: disable=import-outside-toplevel
        from kedro.framework.cli import pipeline

        spy = mocker.spy(pipeline, "_pull_package")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("\n[tool.kedro.pipeline.pull]\n")

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        expected_message = (
            "Nothing to pull. Please update the `pyproject.toml` package "
            "manifest section."
        )
        assert expected_message in result.output
        assert not spy.called

    def test_invalid_toml(self, fake_repo_path, fake_project_cli, fake_metadata):
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("what/toml?")

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", "--all"], obj=fake_metadata
        )

        assert result.exit_code
        assert isinstance(result.exception, toml.TomlDecodeError)

    def test_pipeline_pull_no_arg_provided(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull"], obj=fake_metadata
        )
        assert result.exit_code
        expected_message = (
            "Please specify a package path or add '--all' to pull all pipelines in the"
            " `pyproject.toml` package manifest section."
        )
        assert expected_message in result.output
