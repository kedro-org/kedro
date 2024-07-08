import tarfile
import textwrap
from pathlib import Path

import pytest
import toml
from click.testing import CliRunner

from kedro.framework.cli.micropkg import _get_sdist_name

PIPELINE_NAME = "my_pipeline"

LETTER_ERROR = "It must contain only letters, digits, and/or underscores."
FIRST_CHAR_ERROR = "It must start with a letter or underscore."
TOO_SHORT_ERROR = "It must be at least 2 characters long."


@pytest.mark.usefixtures("chdir_to_dummy_project", "cleanup_dist")
class TestMicropkgPackageCommand:
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
            f"{package_name}-{version}/{package_name}/nodes.py",
            f"{package_name}-{version}/{package_name}/pipeline.py",
            f"{package_name}-{version}/{package_name}/config/parameters_{package_name}.yml",
            f"{package_name}-{version}/tests/__init__.py",
            f"{package_name}-{version}/tests/test_pipeline.py",
        }
        assert expected_files <= sdist_contents

    @pytest.mark.parametrize(
        "options,package_name,success_message",
        [
            ([], PIPELINE_NAME, f"'dummy_package.pipelines.{PIPELINE_NAME}' packaged!"),
            (
                ["--alias", "alternative"],
                "alternative",
                f"'dummy_package.pipelines.{PIPELINE_NAME}' packaged as 'alternative'!",
            ),
        ],
    )
    def test_package_micropkg(
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
            ["micropkg", "package", f"pipelines.{PIPELINE_NAME}"] + options,
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert success_message in result.output

        sdist_location = fake_repo_path / "dist"
        assert f"Location: {sdist_location}" in result.output

        self.assert_sdist_contents_correct(
            sdist_location=sdist_location, package_name=package_name, version="0.1"
        )

    def test_micropkg_package_same_name_as_package_name(
        self, fake_metadata, fake_project_cli, fake_repo_path
    ):
        """Create modular pipeline with the same name as the
        package name, then package as is. The command should run
        and the resulting sdist should have all expected contents.
        """
        pipeline_name = fake_metadata.package_name
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", pipeline_name], obj=fake_metadata
        )
        assert result.exit_code == 0

        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", f"pipelines.{pipeline_name}"],
            obj=fake_metadata,
        )
        sdist_location = fake_repo_path / "dist"

        assert result.exit_code == 0
        assert f"Location: {sdist_location}" in result.output
        self.assert_sdist_contents_correct(
            sdist_location=sdist_location, package_name=pipeline_name
        )

    def test_micropkg_package_same_name_as_package_name_alias(
        self, fake_metadata, fake_project_cli, fake_repo_path
    ):
        """Create modular pipeline, then package under alias
        the same name as the package name. The command should run
        and the resulting sdist should have all expected contents.
        """
        alias = fake_metadata.package_name
        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "create", PIPELINE_NAME], obj=fake_metadata
        )
        assert result.exit_code == 0

        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", f"pipelines.{PIPELINE_NAME}", "--alias", alias],
            obj=fake_metadata,
        )
        sdist_location = fake_repo_path / "dist"

        assert result.exit_code == 0
        assert f"Location: {sdist_location}" in result.output
        self.assert_sdist_contents_correct(
            sdist_location=sdist_location, package_name=alias
        )

    @pytest.mark.parametrize("existing_dir", [True, False])
    def test_micropkg_package_to_destination(
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
                "micropkg",
                "package",
                f"pipelines.{PIPELINE_NAME}",
                "--destination",
                str(destination),
            ],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        success_message = (
            f"'dummy_package.pipelines.{PIPELINE_NAME}' packaged! "
            f"Location: {destination}"
        )
        assert success_message in result.output

        self.assert_sdist_contents_correct(sdist_location=destination)

    def test_micropkg_package_overwrites_sdist(
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
                "micropkg",
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
            f"'dummy_package.pipelines.{PIPELINE_NAME}' packaged! "
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
    def test_package_micropkg_bad_alias(
        self, fake_project_cli, bad_alias, error_message
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", f"pipelines.{PIPELINE_NAME}", "--alias", bad_alias],
        )
        assert result.exit_code
        assert error_message in result.output

    def test_package_micropkg_invalid_module_path(self, fake_project_cli):
        result = CliRunner().invoke(
            fake_project_cli, ["micropkg", "package", f"pipelines/{PIPELINE_NAME}"]
        )
        error_message = (
            "The micro-package location you provided is not a valid Python module path"
        )

        assert result.exit_code
        assert error_message in result.output

    def test_package_micropkg_no_config(
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
            ["micropkg", "package", f"pipelines.{PIPELINE_NAME}"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert f"'dummy_package.pipelines.{PIPELINE_NAME}' packaged!" in result.output

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
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/nodes.py",
            f"{PIPELINE_NAME}-{version}/{PIPELINE_NAME}/pipeline.py",
            f"{PIPELINE_NAME}-{version}/tests/__init__.py",
            f"{PIPELINE_NAME}-{version}/tests/test_pipeline.py",
        }
        assert expected_files <= sdist_contents
        assert f"{PIPELINE_NAME}/config/parameters.yml" not in sdist_contents

    def test_package_non_existing_micropkg_dir(
        self, fake_package_path, fake_project_cli, fake_metadata
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", "pipelines.non_existing"],
            obj=fake_metadata,
        )
        assert result.exit_code == 1
        pipeline_dir = fake_package_path / "pipelines" / "non_existing"
        error_message = f"Error: Directory '{pipeline_dir}' doesn't exist."
        assert error_message in result.output

    def test_package_empty_micropkg_dir(
        self, fake_project_cli, fake_package_path, fake_metadata
    ):
        pipeline_dir = fake_package_path / "pipelines" / "empty_dir"
        pipeline_dir.mkdir()

        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", "pipelines.empty_dir"],
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
        when calling `kedro micropkg package` for a specific pipeline.

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
            ["micropkg", "package", "pipelines.retail"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert "'dummy_package.pipelines.retail' packaged!" in result.output

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
        assert "retail-0.1/retail/config/parameters_retail.yml" in sdist_contents
        assert (
            "retail-0.1/retail/config/parameters_retail_banking.yml"
            not in sdist_contents
        )

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
            fake_project_cli,
            ["micropkg", "package", "pipelines.retail"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0
        assert "'dummy_package.pipelines.retail' packaged!" in result.output

        sdist_location = fake_repo_path / "dist"
        assert f"Location: {sdist_location}" in result.output

        sdist_name = _get_sdist_name(name="retail", version="0.1")
        sdist_file = sdist_location / sdist_name
        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

        with tarfile.open(sdist_file, "r") as tar:
            sdist_contents = set(tar.getnames())
        assert (
            "retail-0.1/retail/config/parameters/deep/retail/params1.yml"
            in sdist_contents
        )
        assert (
            "retail-0.1/retail/config/parameters/retail/deep/params1.yml"
            in sdist_contents
        )
        assert "retail-0.1/retail/config/parameters_retail.yml" in sdist_contents
        assert "retail-0.1/retail/config/parameters/deep/retail.yml" in sdist_contents
        assert (
            "retail-0.1/retail/config/parameters/a/b/c/d/retail/params3.yml"
            in sdist_contents
        )

    def test_micropkg_package_default(
        self, fake_repo_path, fake_package_path, fake_project_cli, fake_metadata
    ):
        _pipeline_name = "data_engineering"

        pipelines_dir = fake_package_path / "pipelines" / _pipeline_name
        assert pipelines_dir.is_dir()

        result = CliRunner().invoke(
            fake_project_cli,
            ["micropkg", "package", f"pipelines.{_pipeline_name}"],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        # test for actual version
        sdist_location = fake_repo_path / "dist"
        sdist_name = _get_sdist_name(name=_pipeline_name, version="0.1")
        sdist_file = sdist_location / sdist_name

        assert sdist_file.is_file()
        assert len(list(sdist_location.iterdir())) == 1

    def test_micropkg_package_nested_module(
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
            ["micropkg", "package", f"pipelines.{PIPELINE_NAME}.utils"],
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
    "chdir_to_dummy_project", "cleanup_dist", "cleanup_pyproject_toml"
)
class TestMicropkgPackageFromManifest:
    def test_micropkg_package_all(
        self, fake_repo_path, fake_project_cli, fake_metadata, tmp_path, mocker
    ):
        from kedro.framework.cli import micropkg

        spy = mocker.spy(micropkg, "_package_micropkg")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        other_dest = tmp_path / "here"
        other_dest.mkdir()
        project_toml_str = textwrap.dedent(
            f"""
            [tool.kedro.micropkg.package]
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
            fake_project_cli, ["micropkg", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        assert "Micro-packages packaged!" in result.output
        assert spy.call_count == 3

        build_config = toml.loads(project_toml_str)
        package_manifest = build_config["tool"]["kedro"]["micropkg"]["package"]
        for pipeline_name, packaging_specs in package_manifest.items():
            expected_call = mocker.call(pipeline_name, fake_metadata, **packaging_specs)
            assert expected_call in spy.call_args_list

    def test_micropkg_package_all_empty_toml(
        self, fake_repo_path, fake_project_cli, fake_metadata, mocker
    ):
        from kedro.framework.cli import micropkg

        spy = mocker.spy(micropkg, "_package_micropkg")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("\n[tool.kedro.micropkg.package]\n")

        result = CliRunner().invoke(
            fake_project_cli, ["micropkg", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code == 0
        expected_message = (
            "Nothing to package. Please update the 'pyproject.toml' "
            "package manifest section."
        )
        assert expected_message in result.output
        assert not spy.called

    def test_invalid_toml(self, fake_repo_path, fake_project_cli, fake_metadata):
        pyproject_toml = fake_repo_path / "pyproject.toml"
        with pyproject_toml.open(mode="a") as file:
            file.write("what/toml?")

        result = CliRunner().invoke(
            fake_project_cli, ["micropkg", "package", "--all"], obj=fake_metadata
        )

        assert result.exit_code
        assert isinstance(result.exception, toml.TomlDecodeError)

    def test_micropkg_package_no_arg_provided(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli, ["micropkg", "package"], obj=fake_metadata
        )
        assert result.exit_code
        expected_message = (
            "Please specify a micro-package name or add '--all' to package all micro-packages in "
            "the 'pyproject.toml' package manifest section."
        )
        assert expected_message in result.output
