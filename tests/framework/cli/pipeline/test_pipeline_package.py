import textwrap
from pathlib import Path
from zipfile import ZipFile

import pytest
import toml
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_wheel_name

PIPELINE_NAME = "my_pipeline"

LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log", "cleanup_dist")
class TestPipelinePackageCommand:
    def assert_wheel_contents_correct(
        self, wheel_location, package_name=PIPELINE_NAME, version="0.1"
    ):
        wheel_name = _get_wheel_name(name=package_name, version=version)
        wheel_file = wheel_location / wheel_name
        assert wheel_file.is_file()
        assert len(list(wheel_location.iterdir())) == 1

        # pylint: disable=consider-using-with
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
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
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

    def test_pipeline_package_same_name_as_package_name(
        self, fake_metadata, fake_project_cli, fake_repo_path
    ):
        """Create modular pipeline with the same name as the
        package name, then package as is. The command should run
        and the resulting wheel should have all expected contents.
        """
        pipeline_name = fake_metadata.package_name
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", pipeline_name], obj=fake_metadata
        )
        assert result.exit_code == 0

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", pipeline_name], obj=fake_metadata
        )
        wheel_location = fake_repo_path / "src" / "dist"

        assert result.exit_code == 0
        assert f"Location: {wheel_location}" in result.output
        self.assert_wheel_contents_correct(
            wheel_location=wheel_location, package_name=pipeline_name
        )

    def test_pipeline_package_same_name_as_package_name_alias(
        self, fake_metadata, fake_project_cli, fake_repo_path
    ):
        """Create modular pipeline, then package under alias
        the same name as the package name. The command should run
        and the resulting wheel should have all expected contents.
        """
        alias = fake_metadata.package_name
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )
        assert result.exit_code == 0

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "package", PIPELINE_NAME, "--alias", alias],
            obj=fake_metadata,
        )
        wheel_location = fake_repo_path / "src" / "dist"

        assert result.exit_code == 0
        assert f"Location: {wheel_location}" in result.output
        self.assert_wheel_contents_correct(
            wheel_location=wheel_location, package_name=alias
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
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
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

    def test_package_pipeline_invalid_module_path(self, fake_project_cli):
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", f"pipelines/{PIPELINE_NAME}"]
        )
        error_message = (
            "The pipeline location you provided is not a valid Python module path"
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
            fake_project_cli, ["pipeline", "package", PIPELINE_NAME], obj=fake_metadata
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

        # pylint: disable=consider-using-with
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
            fake_project_cli, ["pipeline", "package", "non_existing"], obj=fake_metadata
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
            fake_project_cli, ["pipeline", "package", "empty_dir"], obj=fake_metadata
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
            fake_project_cli, ["pipeline", "package", "retail"], obj=fake_metadata
        )

        assert result.exit_code == 0
        assert "Pipeline `retail` packaged!" in result.output

        wheel_location = fake_repo_path / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        wheel_name = _get_wheel_name(name="retail", version="0.1")
        wheel_file = wheel_location / wheel_name
        assert wheel_file.is_file()
        assert len(list(wheel_location.iterdir())) == 1

        # pylint: disable=consider-using-with
        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        assert "retail/config/parameters/retail/params1.yml" in wheel_contents
        assert "retail/config/parameters/retail.yml" in wheel_contents
        assert "retail/config/parameters/retail_banking.yml" not in wheel_contents

    def test_package_pipeline_with_deep_nested_parameters(
        self, fake_repo_path, fake_project_cli, fake_metadata
    ):
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", "retail"], obj=fake_metadata
        )
        deep_nested_param_path = Path(
            fake_repo_path / "conf" / "base" / "parameters" / "deep" / "retail"
        )
        deep_nested_param_path.mkdir(parents=True, exist_ok=True)
        (deep_nested_param_path / "params1.yml").touch()

        deep_nested_param_path2 = Path(
            fake_repo_path / "conf" / "base" / "parameters" / "retail" / "deep"
        )
        deep_nested_param_path2.mkdir(parents=True, exist_ok=True)
        (deep_nested_param_path2 / "params1.yml").touch()

        deep_nested_param_path3 = Path(
            fake_repo_path / "conf" / "base" / "parameters" / "deep"
        )
        deep_nested_param_path3.mkdir(parents=True, exist_ok=True)
        (deep_nested_param_path3 / "retail.yml").touch()

        super_deep_nested_param_path = Path(
            fake_repo_path
            / "conf"
            / "base"
            / "parameters"
            / "a"
            / "b"
            / "c"
            / "d"
            / "retail"
        )
        super_deep_nested_param_path.mkdir(parents=True, exist_ok=True)
        (super_deep_nested_param_path / "params3.yml").touch()
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", "retail"], obj=fake_metadata
        )

        assert result.exit_code == 0
        assert "Pipeline `retail` packaged!" in result.output

        wheel_location = fake_repo_path / "src" / "dist"
        assert f"Location: {wheel_location}" in result.output

        wheel_name = _get_wheel_name(name="retail", version="0.1")
        wheel_file = wheel_location / wheel_name
        assert wheel_file.is_file()
        assert len(list(wheel_location.iterdir())) == 1

        # pylint: disable=consider-using-with
        wheel_contents = set(ZipFile(str(wheel_file)).namelist())
        assert "retail/config/parameters/deep/retail/params1.yml" in wheel_contents
        assert "retail/config/parameters/retail/deep/params1.yml" in wheel_contents
        assert "retail/config/parameters/retail.yml" in wheel_contents
        assert "retail/config/parameters/deep/retail.yml" in wheel_contents
        assert "retail/config/parameters/a/b/c/d/retail/params3.yml" in wheel_contents

    def test_pipeline_package_version(
        self, fake_repo_path, fake_package_path, fake_project_cli, fake_metadata
    ):
        _pipeline_name = "data_engineering"
        # the test version value is set separately in
        # features/steps/test_starter/<repo>/src/<package>/pipelines/data_engineering/__init__.py
        _test_version = "4.20.69"

        pipelines_dir = fake_package_path / "pipelines" / _pipeline_name
        assert pipelines_dir.is_dir()

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "package", _pipeline_name], obj=fake_metadata
        )
        assert result.exit_code == 0

        # test for actual version
        wheel_location = fake_repo_path / "src" / "dist"
        wheel_name = _get_wheel_name(name=_pipeline_name, version=_test_version)
        wheel_file = wheel_location / wheel_name

        assert wheel_file.is_file()
        assert len(list(wheel_location.iterdir())) == 1


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
            first = {{destination = "{other_dest.as_posix()}"}}
            second = {{alias = "ds", env = "local"}}
            third = {{}}
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
