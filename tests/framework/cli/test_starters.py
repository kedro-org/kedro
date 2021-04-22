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

"""This module contains unit test for the cli command 'kedro new'
"""

import json
import shutil
from pathlib import Path
from typing import Dict

import pytest
import yaml
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.starters import _STARTER_ALIASES, TEMPLATE_PATH

FILES_IN_TEMPLATE = 37


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


def _write_yaml(filepath: Path, config: Dict):
    filepath.parent.mkdir(parents=True, exist_ok=True)
    yaml_str = yaml.dump(config)
    filepath.write_text(yaml_str)


def _make_cli_prompt_input(project_name="", repo_name="", python_package=""):
    return "\n".join([project_name, repo_name, python_package])


# pylint: disable=too-many-arguments
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
    assert project_name in (full_path / "README.md").read_text()
    assert "KEDRO" in (full_path / ".gitignore").read_text()
    assert kedro_version in (full_path / "src" / "requirements.txt").read_text()
    assert (full_path / "src" / python_package / "__init__.py").is_file()


def test_starter_list(fake_kedro_cli):
    """Check that `kedro starter list` prints out all starter aliases."""
    result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])

    assert result.exit_code == 0, result.output
    for alias in _STARTER_ALIASES:
        assert alias in result.output


def test_cookiecutter_json_matches_prompts_yml():
    """Validate the contents of the default config file."""
    cookiecutter_json = json.loads((TEMPLATE_PATH / "cookiecutter.json").read_text())
    prompts_yml = yaml.safe_load((TEMPLATE_PATH / "prompts.yml").read_text())
    assert set(cookiecutter_json) == set(prompts_yml) | {"kedro_version"}


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

    def test_custom_repo_name(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli, ["new"], input=_make_cli_prompt_input(repo_name="my-repo"),
        )
        _assert_template_ok(
            result,
            project_name="New Kedro Project",
            repo_name="my-repo",
            python_package="new_kedro_project",
        )

    def test_custom_python_package(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(python_package="my_package"),
        )
        _assert_template_ok(
            result,
            project_name="New Kedro Project",
            repo_name="new-kedro-project",
            python_package="my_package",
        )

    def test_custom_all(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(
                project_name="My Project",
                repo_name="my-repo",
                python_package="my_package",
            ),
        )
        _assert_template_ok(
            result,
            project_name="My Project",
            repo_name="my-repo",
            python_package="my_package",
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

    @pytest.mark.parametrize(
        "repo_name", [".repo\nvalid", "re!po\nvalid", "-repo\nvalid", "repo-\nvalid"]
    )
    def test_bad_repo_name(self, fake_kedro_cli, repo_name):
        """Check the error if the repository name is invalid."""
        result = CliRunner().invoke(
            fake_kedro_cli, ["new"], input=_make_cli_prompt_input(repo_name=repo_name)
        )
        assert result.exit_code != 0
        assert (
            "is an invalid value.\nIt must contain only word symbols" in result.output
        )

    @pytest.mark.parametrize(
        "python_package",
        ["0package\nvalid", "_\nvalid", "package-name\nvalid", "package name\nvalid"],
    )
    def test_bad_python_package(self, fake_kedro_cli, python_package):
        """Check the error if the package name is invalid."""
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(python_package=python_package),
        )
        assert result.exit_code != 0
        assert "is an invalid value.\nIt must start with a letter" in result.output

    def test_prompt_no_title(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(Path("template") / "prompts.yml", {"repo_name": {}})
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        assert result.exit_code != 0
        assert "Each prompt must have a title field to be valid" in result.output

    def test_prompt_bad_yaml(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        (Path("template") / "prompts.yml").write_text("invalid\tyaml")
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        assert result.exit_code != 0
        assert "Failed to generate project: could not load prompts.yml" in result.output


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
        _assert_template_ok(result)

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
        _assert_template_ok(result)


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
            "project_name": "My Project",
            "repo_name": "my-project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "python_package not found in config file" in result.output

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
        Path("config.yml").write_text("invalid\tyaml")
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
            "template": "git+https://github.com/quantumblacklabs/kedro-starters.git",
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
            "template": "git+https://github.com/quantumblacklabs/kedro-starters.git",
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
            ("spaceflights", "https://github.com/quantumblacklabs/kedro-starters.git"),
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
