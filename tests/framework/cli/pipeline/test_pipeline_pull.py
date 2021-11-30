import filecmp
import shutil
import textwrap
from pathlib import Path

import pytest
import toml
import yaml
from click import ClickException
from click.testing import CliRunner

from kedro.framework.cli.pipeline import _get_sdist_name
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
        cli,
        ["pipeline", "package", f"pipelines.{pipeline_name}", *options],
        obj=metadata,
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
    @pytest.mark.parametrize(
        "alias, destination",
        [(None, None), ("aliased", None), ("aliased", "pipelines"), (None, "pipelines")],
    )
    def test_pull_local_sdist(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        destination,
        fake_metadata,
    ):
        """Test for pulling a valid sdist file locally."""
        # pylint: disable=too-many-locals
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        config_path = (
            fake_repo_path / settings.CONF_SOURCE / "base" / "pipelines" / PIPELINE_NAME
        )
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the sdist file.
        assert not source_path.exists()
        assert not test_path.exists()
        assert not config_path.exists()

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        options += ["--destination", destination] if destination else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0, result.output
        assert "pulled and unpacked" in result.output

        pipeline_name = alias or PIPELINE_NAME
        destination = destination or Path()
        source_dest = fake_package_path / destination / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / destination / pipeline_name
        config_env = env or "base"
        params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
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
    @pytest.mark.parametrize(
        "alias, destination",
        [
            (None, None),
            ("aliased", None),
            ("aliased", "pipelines"),
            (None, "pipelines"),
        ],
    )
    def test_pull_local_sdist_compare(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_package_path,
        env,
        alias,
        destination,
        fake_metadata,
    ):
        """Test for pulling a valid sdist file locally, unpack it
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
            / settings.CONF_SOURCE
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=pipeline_name, version="0.1")
        )
        assert sdist_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        options += ["--destination", destination] if destination else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0, result.output
        assert "pulled and unpacked" in result.output

        pipeline_name = alias or pipeline_name
        destination = destination or Path()
        source_dest = fake_package_path / destination / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / destination / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
            / config_env
            / "parameters"
            / f"{pipeline_name}.yml"
        )

        assert not filecmp.dircmp(source_path, source_dest).diff_files
        assert not filecmp.dircmp(test_path, test_dest).diff_files
        assert source_params_config.read_bytes() == dest_params_config.read_bytes()

    def test_pipeline_pull_same_alias_package_name(
        self,
        fake_project_cli,
        fake_repo_path,
        fake_metadata,
    ):
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )

        result = CliRunner().invoke(
            fake_project_cli,
            [
                "pipeline",
                "pull",
                str(sdist_file),
                "--destination",
                "tools",
                "--alias",
                PIPELINE_NAME,
            ],
            obj=fake_metadata,
        )
        assert result.exit_code == 0, result.stderr
        assert "pulled and unpacked" in result.output

    def test_pipeline_alias_refactors_imports(  # pylint: disable=too-many-locals
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
        pull_destination = "pipelines/lib"

        call_pipeline_package(
            cli=fake_project_cli, metadata=fake_metadata, alias=package_alias
        )

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=package_alias, version="0.1")
        )
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(sdist_file)], obj=fake_metadata
        )
        CliRunner().invoke(
            fake_project_cli,
            [
                "pipeline",
                "pull",
                str(sdist_file),
                "--alias",
                pull_alias,
                "--destination",
                pull_destination,
            ],
            obj=fake_metadata,
        )
        pull = f"pipelines.lib.{pull_alias}"
        for alias in (package_alias, pull):
            alias_path = Path(*alias.split("."))
            path = fake_package_path / alias_path / "pipeline.py"
            file_content = path.read_text()
            expected_stmt = f"import {fake_metadata.package_name}.{alias}.nodes"
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
        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=package_name, version="0.1")
        )
        assert sdist_file.is_file()

        result = CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(sdist_file)], obj=fake_metadata
        )
        assert result.exit_code == 0, result.output

        path = fake_package_path / package_name / "pipeline.py"
        file_content = path.read_text()
        expected_stmt = f"import {package_name}.{package_name}.nodes"
        assert expected_stmt in file_content

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
        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file), "--alias", package_name],
            obj=fake_metadata,
        )
        assert result.exit_code == 0, result.output
        path = fake_package_path / package_name / "pipeline.py"
        file_content = path.read_text()
        expected_stmt = f"import {package_name}.{package_name}.nodes"
        assert expected_stmt in file_content

    def test_pull_sdist_fs_args(
        self, fake_project_cli, fake_repo_path, mocker, tmp_path, fake_metadata
    ):
        """Test for pulling a sdist file with custom fs_args specified."""
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

        fs_args_config = tmp_path / "fs_args_config.yml"
        with fs_args_config.open(mode="w") as f:
            yaml.dump({"fs_arg_1": 1, "fs_arg_2": {"fs_arg_2_nested_1": 2}}, f)
        mocked_filesystem = mocker.patch("fsspec.filesystem")

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )

        options = ["--fs-args", str(fs_args_config)]
        CliRunner().invoke(
            fake_project_cli, ["pipeline", "pull", str(sdist_file), *options]
        )

        mocked_filesystem.assert_called_once_with(
            "file", fs_arg_1=1, fs_arg_2=dict(fs_arg_2_nested_1=2)
        )

    def test_pull_two_egg_info(
        self, fake_project_cli, fake_repo_path, mocker, tmp_path, fake_metadata
    ):
        """Test for pulling an sdist file with more than one
        dist-info directory.
        """
        call_pipeline_create(fake_project_cli, fake_metadata)
        call_pipeline_package(fake_project_cli, fake_metadata)
        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        (tmp_path / f"{PIPELINE_NAME}-0.1" / "dummy.egg-info").mkdir(parents=True)

        mocker.patch(
            "kedro.framework.cli.pipeline.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file)],
            obj=fake_metadata,
        )
        assert result.exit_code
        assert "Error: More than 1 or no egg-info files found" in result.output

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
        """Test for pulling a valid sdist file locally,
        but `tests` directory is missing from the sdist file.
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
            / settings.CONF_SOURCE
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        # Make sure the files actually deleted before pulling from the sdist file.
        assert not source_path.exists()
        assert not source_params_config.exists()

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / pipeline_name
        config_env = env or "base"
        params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
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
        Test for pulling a valid sdist file locally, but `config` directory is missing
        from the sdist file.
        """
        # pylint: disable=too-many-locals
        call_pipeline_create(fake_project_cli, fake_metadata)
        source_params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
            / "base"
            / "parameters"
            / f"{PIPELINE_NAME}.yml"
        )
        source_params_config.unlink()
        call_pipeline_package(fake_project_cli, fake_metadata)
        call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        # Make sure the files actually deleted before pulling from the sdist file.
        assert not source_path.exists()
        assert not test_path.exists()

        sdist_file = (
            fake_repo_path / "dist" / _get_sdist_name(name=PIPELINE_NAME, version="0.1")
        )
        assert sdist_file.is_file()

        options = ["-e", env] if env else []
        options += ["--alias", alias] if alias else []
        result = CliRunner().invoke(
            fake_project_cli,
            ["pipeline", "pull", str(sdist_file), *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
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
        Test for pulling a valid sdist file from pypi.
        """
        # pylint: disable=too-many-locals
        call_pipeline_create(fake_project_cli, fake_metadata)
        # We mock the `pip download` call, and manually create a package sdist file
        # to simulate the pypi scenario instead
        call_pipeline_package(fake_project_cli, fake_metadata, destination=tmp_path)
        version = "0.1"
        sdist_file = tmp_path / _get_sdist_name(name=PIPELINE_NAME, version=version)
        assert sdist_file.is_file()
        call_pipeline_delete(fake_project_cli, fake_metadata)

        source_path = fake_package_path / "pipelines" / PIPELINE_NAME
        test_path = fake_repo_path / "src" / "tests" / "pipelines" / PIPELINE_NAME
        source_params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
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
            ["pipeline", "pull", f"{PIPELINE_NAME}-{version}", *options],
            obj=fake_metadata,
        )
        assert result.exit_code == 0
        assert "pulled and unpacked" in result.output

        python_call_mock.assert_called_once_with(
            "pip",
            [
                "download",
                "--no-deps",
                "--dest",
                str(tmp_path),
                f"{PIPELINE_NAME}-{version}",
            ],
        )

        pipeline_name = alias or PIPELINE_NAME
        source_dest = fake_package_path / pipeline_name
        test_dest = fake_repo_path / "src" / "tests" / pipeline_name
        config_env = env or "base"
        dest_params_config = (
            fake_repo_path
            / settings.CONF_SOURCE
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

    def test_pull_from_pypi_more_than_one_sdist_file(
        self, fake_project_cli, mocker, tmp_path, fake_metadata
    ):
        """
        Test for pulling a sdist file with `pip download`, but there are more than one sdist
        file to unzip.
        """
        # We mock the `pip download` call, and manually create a package sdist file
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
        assert "Error: More than 1 or no sdist files found:" in result.output

    def test_pull_unsupported_protocol_by_fsspec(
        self, fake_project_cli, fake_metadata, tmp_path, mocker
    ):
        protocol = "unsupported"
        exception_message = f"Protocol not known: {protocol}"
        error_message = "Error: More than 1 or no sdist files found:"
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
        # pylint: disable=import-outside-toplevel, line-too-long
        from kedro.framework.cli import pipeline

        spy = mocker.spy(pipeline, "_pull_package")
        pyproject_toml = fake_repo_path / "pyproject.toml"
        sdist_file = str(fake_repo_path / "dist" / _get_sdist_name("{}", "0.1"))
        project_toml_str = textwrap.dedent(
            f"""
            [tool.kedro.pipeline.pull]
            "{sdist_file.format("first")}" = {{alias = "dp", destination = "pipelines"}}
            "{sdist_file.format("second")}" = {{alias = "ds", destination = "pipelines", env = "local"}}
            "{sdist_file.format("third")}" = {{}}
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
        for sdist_file, pull_specs in pull_manifest.items():
            expected_call = mocker.call(sdist_file, fake_metadata, **pull_specs)
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
