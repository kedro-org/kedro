"""This module contains unit test for the cli command 'kedro new'
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.starters import (
    _OFFICIAL_STARTER_SPECS,
    TEMPLATE_PATH,
    KedroStarterSpec,
)

FILES_IN_TEMPLATE = 28


@pytest.fixture
def chdir_to_tmp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


@pytest.fixture
def mock_determine_repo_dir(mocker):
    return mocker.patch(
        "cookiecutter.repository.determine_repo_dir",
        return_value=(str(TEMPLATE_PATH), None),
    )


@pytest.fixture
def mock_cookiecutter(mocker):
    return mocker.patch("cookiecutter.main.cookiecutter")


def _write_yaml(filepath: Path, config: dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _make_cli_prompt_input(project_name="", repo_name="", python_package=""):
    return "\n".join([project_name, repo_name, python_package])


# noqa: too-many-arguments
def _assert_template_ok(
    result,
    project_name="New Kedro Project",
    repo_name="new-kedro-project",
    python_package="new_kedro_project",
    kedro_version=version,
    output_dir=".",
):
    assert result.exit_code == 0, result.output
    assert "Change directory to the project generated in" in result.output

    full_path = (Path(output_dir) / repo_name).resolve()
    generated_files = [
        p for p in full_path.rglob("*") if p.is_file() and p.name != ".DS_Store"
    ]

    assert len(generated_files) == FILES_IN_TEMPLATE
    assert full_path.exists()
    assert (full_path / ".gitignore").is_file()
    assert project_name in (full_path / "README.md").read_text(encoding="utf-8")
    assert "KEDRO" in (full_path / ".gitignore").read_text(encoding="utf-8")
    assert kedro_version in (full_path / "src" / "requirements.txt").read_text(
        encoding="utf-8"
    )
    assert (full_path / "src" / python_package / "__init__.py").is_file()


def test_starter_list(fake_kedro_cli):
    """Check that `kedro starter list` prints out all starter aliases."""
    result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])

    assert result.exit_code == 0, result.output
    for alias in _OFFICIAL_STARTER_SPECS:
        assert alias in result.output


def test_starter_list_with_starter_plugin(fake_kedro_cli, entry_point):
    """Check that `kedro starter list` prints out the plugin starters."""
    entry_point.load.return_value = [KedroStarterSpec("valid_starter", "valid_path")]
    entry_point.module = "valid_starter_module"
    result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])
    assert result.exit_code == 0, result.output
    assert "valid_starter_module" in result.output


@pytest.mark.parametrize(
    "specs,expected",
    [
        (
            [{"alias": "valid_starter", "template_path": "valid_path"}],
            "should be a 'KedroStarterSpec'",
        ),
        (
            [
                KedroStarterSpec("duplicate", "duplicate"),
                KedroStarterSpec("duplicate", "duplicate"),
            ],
            "has been ignored as it is already defined by",
        ),
    ],
)
def test_starter_list_with_invalid_starter_plugin(
    fake_kedro_cli, entry_point, specs, expected
):
    """Check that `kedro starter list` prints out the plugin starters."""
    entry_point.load.return_value = specs
    entry_point.module = "invalid_starter"
    result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])
    assert result.exit_code == 0, result.output
    assert expected in result.output


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromUserPromptsValid:
    """Tests for running `kedro new` interactively."""

    def test_default(self, fake_kedro_cli):
        """Test new project creation using default New Kedro Project options."""
        result = CliRunner().invoke(
            fake_kedro_cli, ["new"], input=_make_cli_prompt_input()
        )
        _assert_template_ok(result)

    def test_custom_project_name(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(project_name="My Project"),
        )
        _assert_template_ok(
            result,
            project_name="My Project",
            repo_name="my-project",
            python_package="my_project",
        )

    def test_custom_project_name_with_hyphen_and_underscore_and_number(
        self, fake_kedro_cli
    ):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(project_name="My-Project_ 1"),
        )
        _assert_template_ok(
            result,
            project_name="My-Project_ 1",
            repo_name="my-project--1",
            python_package="my_project__1",
        )

    def test_no_prompts(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        (Path("template") / "prompts.yml").unlink()
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        _assert_template_ok(result)

    def test_empty_prompts(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(Path("template") / "prompts.yml", {})
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        _assert_template_ok(result)

    def test_custom_prompt_valid_input(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(
            Path("template") / "prompts.yml",
            {
                "project_name": {"title": "Project Name"},
                "custom_value": {
                    "title": "Custom Value",
                    "regex_validator": "^\\w+(-*\\w+)*$",
                },
            },
        )
        custom_input = "\n".join(["my-project", "My Project"])
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "template"],
            input=custom_input,
        )
        _assert_template_ok(
            result,
            project_name="My Project",
            repo_name="my-project",
            python_package="my_project",
        )

    def test_custom_prompt_for_essential_variable(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(
            Path("template") / "prompts.yml",
            {
                "project_name": {"title": "Project Name"},
                "repo_name": {
                    "title": "Custom Repo Name",
                    "regex_validator": "^[a-zA-Z_]\\w{1,}$",
                },
            },
        )
        custom_input = "\n".join(["My Project", "my_custom_repo"])
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "template"],
            input=custom_input,
        )
        _assert_template_ok(
            result,
            project_name="My Project",
            repo_name="my_custom_repo",
            python_package="my_project",
        )


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromUserPromptsInvalid:
    def test_fail_if_dir_exists(self, fake_kedro_cli):
        """Check the error if the output directory already exists."""
        Path("new-kedro-project").mkdir()
        (Path("new-kedro-project") / "empty_file").touch()
        old_contents = list(Path("new-kedro-project").iterdir())
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v"], input=_make_cli_prompt_input()
        )
        assert list(Path("new-kedro-project").iterdir()) == old_contents
        assert result.exit_code != 0
        assert "directory already exists" in result.output

    def test_prompt_no_title(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(Path("template") / "prompts.yml", {"repo_name": {}})
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        assert result.exit_code != 0
        assert "Each prompt must have a title field to be valid" in result.output

    def test_prompt_bad_yaml(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        (Path("template") / "prompts.yml").write_text("invalid\tyaml", encoding="utf-8")
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        assert result.exit_code != 0
        assert "Failed to generate project: could not load prompts.yml" in result.output

    def test_invalid_project_name_special_characters(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(project_name="My $Project!"),
        )
        assert result.exit_code != 0
        assert (
            "is an invalid value for Project Name.\nIt must contain only alphanumeric symbols"
            in result.output
        )

    def test_invalid_project_name_too_short(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(project_name="P"),
        )
        assert result.exit_code != 0
        assert (
            "is an invalid value for Project Name.\nIt must contain only alphanumeric symbols"
            in result.output
        )

    def test_custom_prompt_invalid_input(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(
            Path("template") / "prompts.yml",
            {
                "project_name": {"title": "Project Name"},
                "custom_value": {
                    "title": "Custom Value",
                    "regex_validator": "^\\w+(-*\\w+)*$",
                },
            },
        )
        custom_input = "\n".join(["My Project", "My Project"])
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "template"],
            input=custom_input,
        )
        assert result.exit_code != 0
        assert "'My Project' is an invalid value" in result.output


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileValid:
    """Test `kedro new` with config file provided."""

    def test_required_keys_only(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_required_keys(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "project_name": "Project X",
            "repo_name": "projectx",
            "python_package": "proj_x",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_kedro_version(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
            "kedro_version": "my_version",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_output_dir(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
            "output_dir": "my_output_dir",
        }
        _write_yaml(Path("config.yml"), config)
        Path("my_output_dir").mkdir()
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_extra_keys_allowed(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), {**config, "extra_key": "my_extra_key"})
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_no_prompts(self, fake_kedro_cli):
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        shutil.copytree(TEMPLATE_PATH, "template")
        (Path("template") / "prompts.yml").unlink()
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "--starter", "template", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_empty_prompts(self, fake_kedro_cli):
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(Path("template") / "prompts.yml", {})
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "--starter", "template", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileInvalid:
    def test_output_dir_does_not_exist(self, fake_kedro_cli):
        """Check the error if the output directory is invalid."""
        config = {
            "project_name": "My Project",
            "repo_name": "my-project",
            "python_package": "my_project",
            "output_dir": "does_not_exist",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "is not a valid output directory." in result.output

    def test_config_missing_key(self, fake_kedro_cli):
        """Check the error if keys are missing from config file."""
        config = {
            "python_package": "my_project",
            "repo_name": "my-project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "project_name not found in config file" in result.output

    def test_config_does_not_exist(self, fake_kedro_cli):
        """Check the error if the config file does not exist."""
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-c", "missing.yml"])
        assert result.exit_code != 0
        assert "Path 'missing.yml' does not exist" in result.output

    def test_config_empty(self, fake_kedro_cli):
        """Check the error if the config file is empty."""
        Path("config.yml").touch()
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "Config file is empty" in result.output

    def test_config_bad_yaml(self, fake_kedro_cli):
        """Check the error if config YAML is invalid."""
        Path("config.yml").write_text("invalid\tyaml", encoding="utf-8")
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "Failed to generate project: could not load config" in result.output


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewWithStarterValid:
    def test_absolute_path(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(Path("./template").resolve())],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_relative_path(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_relative_path_directory(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", ".", "--directory", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_alias(self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter):
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/kedro-org/kedro-starters.git",
            "checkout": version,
            "directory": "spaceflights",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_alias_custom_checkout(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights", "--checkout", "my_checkout"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/kedro-org/kedro-starters.git",
            "checkout": "my_checkout",
            "directory": "spaceflights",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_git_repo(self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter):
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "git+https://github.com/fake/fake.git"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/fake/fake.git",
            "checkout": version,
            "directory": None,
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        del kwargs["directory"]
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_git_repo_custom_checkout(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
        CliRunner().invoke(
            fake_kedro_cli,
            [
                "new",
                "--starter",
                "git+https://github.com/fake/fake.git",
                "--checkout",
                "my_checkout",
            ],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/fake/fake.git",
            "checkout": "my_checkout",
            "directory": None,
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        del kwargs["directory"]
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_git_repo_custom_directory(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
        CliRunner().invoke(
            fake_kedro_cli,
            [
                "new",
                "--starter",
                "git+https://github.com/fake/fake.git",
                "--directory",
                "my_directory",
            ],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/fake/fake.git",
            "checkout": version,
            "directory": "my_directory",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()


class TestNewWithStarterInvalid:
    def test_invalid_starter(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", "invalid"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert "Kedro project template not found at invalid" in result.output

    @pytest.mark.parametrize(
        "starter, repo",
        [
            ("spaceflights", "https://github.com/kedro-org/kedro-starters.git"),
            (
                "git+https://github.com/fake/fake.git",
                "https://github.com/fake/fake.git",
            ),
        ],
    )
    def test_invalid_checkout(self, starter, repo, fake_kedro_cli, mocker):
        mocker.patch(
            "cookiecutter.repository.determine_repo_dir",
            side_effect=RepositoryCloneFailed,
        )
        mock_ls_remote = mocker.patch("git.cmd.Git").return_value.ls_remote
        mock_ls_remote.return_value = "tag1\ntag2"
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", starter, "--checkout", "invalid"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert (
            "Specified tag invalid. The following tags are available: tag1, tag2"
            in result.output
        )
        mock_ls_remote.assert_called_with("--tags", repo)


class TestFlagsNotAllowed:
    def test_checkout_flag_without_starter(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--checkout", "some-checkout"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --checkout flag without a --starter value." in result.output
        )

    def test_directory_flag_without_starter(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--directory", "some-directory"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --directory flag without a --starter value."
            in result.output
        )

    def test_directory_flag_with_starter_alias(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "pyspark-iris", "--directory", "some-dir"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert "Cannot use the --directory flag with a --starter alias" in result.output
