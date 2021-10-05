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
import tarfile
import textwrap
from pathlib import Path

import pytest
import toml
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_sdist_name

PIPELINE_NAME = "my_pipeline"

LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_dist")
class TestPipelinePackageCommand:
    def assert_sdist_contents_correct(
        self, sdist_location, package_name=PIPELINE_NAME, version="0.1"
    ):
        sdist_name = _get_sdist_name(name=package_name, version=version)
        sdist_file = sdist_location / sdist_name
        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

        with tarfile.open(sdist_file, "r") as tar:
            sdist_contents = set(tar.getnames())

        expected_files = {
            f"{package_name}-{version}/{package_name}/__init__.py",
            f"{package_name}-{version}/{package_name}/README.md",
            f"{package_name}-{version}/{package_name}/nodes.py",
            f"{package_name}-{version}/{package_name}/pipeline.py",
            f"{package_name}-{version}/{package_name}/config/parameters/{package_name}.yml",
            f"{package_name}-{version}/tests/__init__.py",
            f"{package_name}-{version}/tests/test_pipeline.py",
        }
        assert expected_files <= sdist_contents

    @pytest.mark.parametrize(
        "options,package_name,success_message",
        [
            ([], PIPELINE_NAME, f"`dummy_package.pipelines.{PIPELINE_NAME}` packaged!"),
            (
                ["--alias", "alternative"],
                "alternative",
                f"`dummy_package.pipelines.{PIPELINE_NAME}` packaged as `alternative`!",
            ),
        ],
    )
    def test_package_pipeline(
        self,
        fake_repo_path,
        fake_project_cli,
        options,
        package_name,
        success_message,
        fake_metadata,
    ):
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}"] + options,
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert success_message in result.output

        sdist_location = fake_repo_path / "dist"
        assert f"Location: {sdist_location}" in result.output

        self.assert_sdist_contents_correct(
            sdist_location=sdist_location, package_name=package_name, version="0.1"
        )

    @pytest.mark.parametrize("existing_dir", [True, False])
    def test_pipeline_package_to_destination(
        self, fake_project_cli, existing_dir, tmp_path, fake_metadata
    ):
        destination = (tmp_path / "in" / "here").resolve()
        if existing_dir:
            destination.mkdir(parents=True)

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            [
                "pipeline",
                "package",
                f"pipelines.{PIPELINE_NAME}",
                "--destination",
                str(destination),
            ],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        success_message = (
            f"`dummy_package.pipelines.{PIPELINE_NAME}` packaged! "
            f"Location: {destination}"
        )
        assert success_message in result.output

        self.assert_sdist_contents_correct(sdist_location=destination)

    def test_pipeline_package_overwrites_sdist(
        self, fake_project_cli, tmp_path, fake_metadata
    ):
        destination = (tmp_path / "in" / "here").resolve()
        destination.mkdir(parents=True)
        sdist_file = destination / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        sdist_file.touch()

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            [
                "pipeline",
                "package",
                f"pipelines.{PIPELINE_NAME}",
                "--destination",
                str(destination),
            ],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        warning_message = f"Package file {sdist_file} will be overwritten!"
        success_message = (
            f"`dummy_package.pipelines.{PIPELINE_NAME}` packaged! "
            f"Location: {destination}"
        )
        assert warning_message in result.output
        assert success_message in result.output

        self.assert_sdist_contents_correct(sdist_location=destination)

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
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}", "--alias", bad_alias],
        )
        assert result.exit_code
        assert error_message in result.output

    def test_package_pipeline_no_config(
        self, fake_repo_path, fake_project_cli, fake_metadata
    ):
        version = "0.1"
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "create", PIPELINE_NAME, "--skip-config"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert f"`dummy_package.pipelines.{PIPELINE_NAME}` packaged!" in result.output

        sdist_location = fake_repo_path / "dist"
        assert f"Location: {sdist_location}" in result.output

        # the sdist contents are slightly different (config shouldn't be included),
        # which is why we can't call self.assert_sdist_contents_correct here
        sdist_file = sdist_location / _get_sdist_name(
            name=PIPELINE_NAME, version=version
        )
        assert sdist_file.is_file()
        assert len(list((fake_repo_path / "dist").iterdir())) == 1

        with tarfile.open(sdist_file, "r") as tar:
            sdist_contents = set(tar.getnames())

        expected_files = {
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/__init__.py",
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/README.md",
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/nodes.py",
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/pipeline.py",
            f"{PIPELINE_NAME}-{version}/tests/__init__.py",
            f"{PIPELINE_NAME}-{version}/tests/test_pipeline.py",
        }
        assert expected_files <= sdist_contents
        assert f"{PIPELINE_NAME}/config/parameters.yml" not in sdist_contents

    def test_package_non_existing_pipeline_dir(
        self, fake_package_path, fake_project_cli, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", "pipelines.non_existing"],
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
            ["pipeline", "package", "pipelines.empty_dir"],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        error_message = f"Error: '{pipeline_dir}' is an empty directory."
        assert error_message in result.output

    def test_package_modular_pipeline_with_nested_parameters(
        self, fake_repo_path, fake_project_cli, fake_metadata
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
            fake_project_cli, ["pipeline", "create", "retail"], obj=fake_metadata
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
            ["pipeline", "package", "pipelines.retail"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert "`dummy_package.pipelines.retail` packaged!" in result.output

        sdist_location = fake_repo_path / "dist"
        assert f"Location: {sdist_location}" in result.output

        sdist_name = _get_sdist_name(name="retail", version="0.1")
        sdist_file = sdist_location / sdist_name
        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

        with tarfile.open(sdist_file, "r") as tar:
            sdist_contents = set(tar.getnames())

        assert (
            "retail-0.1/retail/config/parameters/retail/params1.yml" in sdist_contents
        )
        assert "retail-0.1/retail/config/parameters/retail.yml" in sdist_contents
        assert (
            "retail-0.1/retail/config/parameters/retail_banking.yml"
            not in sdist_contents
        )

    def test_pipeline_package_default(
        self, fake_repo_path, fake_package_path, fake_project_cli, fake_metadata
    ):
        _pipeline_name = "data_engineering"

        pipelines_dir = fake_package_path / "pipelines" / _pipeline_name
        assert pipelines_dir.is_dir()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", f"pipelines.{_pipeline_name}"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        # test for actual version
        sdist_location = fake_repo_path / "dist"
        sdist_name = _get_sdist_name(name=_pipeline_name, version="0.1")
        sdist_file = sdist_location / sdist_name

        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

    def test_pipeline_package_nested_module(
        self, fake_project_cli, fake_metadata, fake_repo_path, fake_package_path
    ):
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )

        nested_utils = fake_package_path / "pipelines" / PIPELINE_NAME / "utils"
        nested_utils.mkdir(parents=True)
        (nested_utils / "__init__.py").touch()
        (nested_utils / "useful.py").touch()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", f"pipelines.{PIPELINE_NAME}.utils"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        sdist_location = fake_repo_path / "dist"
        sdist_name = _get_sdist_name(name="utils", version="0.1")
        sdist_file = sdist_location / sdist_name

        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

        with tarfile.open(sdist_file, "r") as tar:
            sdist_contents = set(tar.getnames())
        expected_files = {
            "utils-0.1/utils/__init__.py",
            "utils-0.1/utils/useful.py",
        }
        assert expected_files <= sdist_contents
        assert f"{PIPELINE_NAME}/pipeline.py" not in sdist_contents


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "patch_log", "cleanup_dist", "cleanup_pyproject_toml"
)
class TestPipelinePackageFromManifest:
    def test_pipeline_package_all(  # pylint: disable=too-many-locals
        self, fake_repo_path, fake_project_cli, fake_metadata, tmp_path, mocker
    ):
        # pylint: disable=import-outside-toplevel
        from kedro.framework.cli import pipeline

        spy = mocker.spy(pipeline, "_package_pipeline")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        other_dest = tmp_path / "here"
        other_dest.mkdir()
        project_toml_str = textwrap.dedent(
            f"""
            [tool.kedro.pipeline.package]
            "pipelines.first" = {{destination = "{other_dest.as_posix()}"}}
            "pipelines.second" = {{alias = "ds", env = "local"}}
            "pipelines.third" = {{}}
            """
        )
        with pyproject_toml.open(mode="a") as file:
            file.write(project_toml_str)

        for name in ("first", "second", "third"):
            CliRunner().invoke(
                fake_project_cli, ["pipeline", "create", name], obj=fake_metadata
            )

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        assert "Pipelines packaged!" in result.output
        assert spy.call_count == 3

        build_config = toml.loads(project_toml_str)
        package_manifest = build_config["tool"]["kedro"]["pipeline"]["package"]
        for pipeline_name, packaging_specs in package_manifest.items():
            expected_call = mocker.call(pipeline_name, fake_metadata, **packaging_specs)
            assert expected_call in spy.call_args_list

    def test_pipeline_package_all_empty_toml(
        self, fake_repo_path, fake_project_cli, fake_metadata, mocker
    ):
        # pylint: disable=import-outside-toplevel
        from kedro.framework.cli import pipeline

        spy = mocker.spy(pipeline, "_package_pipeline")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("\n[tool.kedro.pipeline.package]\n")

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        expected_message = (
            "Nothing to package. Please update the `pyproject.toml` "
            "package manifest section."
        )
        assert expected_message in result.output
        assert not spy.called

    def test_invalid_toml(self, fake_repo_path, fake_project_cli, fake_metadata):
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("what/toml?")

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code
        assert isinstance(result.exception, toml.TomlDecodeError)

    def test_pipeline_package_no_arg_provided(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package"], obj=fake_metadata
        )
        assert result.exit_code
        expected_message = (
            "Please specify a pipeline name or add '--all' to package all pipelines in "
            "the `pyproject.toml` package manifest section."
        )
        assert expected_message in result.output
