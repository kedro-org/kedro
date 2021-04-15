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

import pytest
import yaml
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.starters import _STARTER_ALIASES, TEMPLATE_PATH

FILES_IN_TEMPLATE = 37


def _make_cli_prompt_input(
    project_name=None, repo_name="repo_name", python_package="python_package",
):
    prompts = (project_name, repo_name, python_package)
    return "\n".join(prompt or "" for prompt in prompts)


# pylint: disable=too-many-arguments
def _assert_template_ok(
    result,
    files_in_template,
    project_name="New Kedro Project",
    repo_name=None,
    python_package="python_package",
    output_dir=".",
):
    assert result.exit_code == 0, result.output
    assert "Change directory to the project generated in" in result.output

    if repo_name:
        full_path = (Path(output_dir) / repo_name).absolute()
        generated_files = [
            p for p in full_path.rglob("*") if p.is_file() and p.name != ".DS_Store"
        ]

        assert len(generated_files) == files_in_template
        assert full_path.exists()
        assert (full_path / ".gitignore").is_file()

        if project_name:
            with (full_path / "README.md").open() as file:
                assert project_name in file.read()

        with (full_path / ".gitignore").open() as file:
            assert "KEDRO" in file.read()

        with (full_path / "src" / "requirements.txt").open() as file:
            assert version in file.read()

        if python_package:
            assert (full_path / "src" / python_package / "__init__.py").is_file()


@pytest.fixture(autouse=True)
def chdir_to_tmp(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)


class TestInteractiveNew:
    """Tests for running `kedro new` interactively."""

    repo_name = "project-test"
    package_name = "package_test"

    def test_new(self, fake_kedro_cli):
        """Test new project creation without code example."""
        project_name = "Test"
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v"],
            input=_make_cli_prompt_input(
                project_name=project_name, repo_name=self.repo_name,
            ),
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            project_name=project_name,
            repo_name=self.repo_name,
        )

    def test_new_custom_dir(self, fake_kedro_cli):
        """Test that default package name does not change if custom
        repo name was specified."""
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(repo_name=self.repo_name),
        )
        _assert_template_ok(result, FILES_IN_TEMPLATE, repo_name=self.repo_name)

    def test_fail_if_dir_exists(self, fake_kedro_cli):
        """Check the error if the output directory already exists."""
        empty_file = Path(self.repo_name) / "empty_file"
        empty_file.parent.mkdir(parents=True)
        empty_file.touch()

        old_contents = list(Path(self.repo_name).iterdir())

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v"],
            input=_make_cli_prompt_input(repo_name=self.repo_name),
        )

        assert list(Path(self.repo_name).iterdir()) == old_contents
        assert "directory already exists" in result.output
        assert result.exit_code != 0

    @pytest.mark.parametrize(
        "repo_name", [".repo\nvalid", "re!po\nvalid", "-repo\nvalid", "repo-\nvalid"]
    )
    def test_bad_repo_name(self, fake_kedro_cli, repo_name):
        """Check the error if the repository name is invalid."""
        result = CliRunner().invoke(
            fake_kedro_cli, ["new"], input=_make_cli_prompt_input(repo_name=repo_name)
        )
        assert (
            "is an invalid value.\nIt must contain only word symbols" in result.output
        )
        assert result.exit_code != 0

    @pytest.mark.parametrize(
        "pkg_name",
        ["0package\nvalid", "_\nvalid", "package-name\nvalid", "package name\nvalid"],
    )
    def test_bad_pkg_name(self, fake_kedro_cli, pkg_name):
        """Check the error if the package name is invalid."""
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(python_package=pkg_name),
        )
        assert "is an invalid value.\nIt must start with a letter" in result.output
        assert result.exit_code != 0


def _create_config_file(config_path, project_name, repo_name, output_dir=None):
    config = {
        "project_name": project_name,
        "repo_name": repo_name,
        "python_package": repo_name.replace("-", "_"),
    }

    if output_dir is not None:
        config["output_dir"] = output_dir

    with open(config_path, "w+") as config_file:
        yaml.dump(config, config_file)

    return config


class TestNewFromConfig:
    """Test `kedro new` with config option provided."""

    project_name = "test1"
    repo_name = "project-test1"
    config_path = "config.yml"

    def test_config_does_not_exist(self, fake_kedro_cli):
        """Check the error if the config file does not exist."""
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-c", "missing.yml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_empty_config(self, fake_kedro_cli):
        """Check the error if the config file is empty."""
        open("touch", "a").close()
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "touch"])
        assert result.exit_code != 0
        assert "is empty" in result.output

    def test_new_from_config(self, fake_kedro_cli):
        """Test project created from config without example code."""
        output_dir = "test_dir"
        Path(output_dir).mkdir(parents=True)
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir
        )
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", self.config_path]
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            self.project_name,
            self.repo_name,
            self.repo_name.replace("-", "_"),
            output_dir,
        )

    def test_wrong_config(self, fake_kedro_cli):
        """Check the error if the output directory is invalid."""
        output_dir = "/usr/invalid/dir"
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir
        )

        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "-c", self.config_path]
        )
        assert result.exit_code != 0
        assert "is not a valid output directory." in result.output

    def test_config_missing_key(self, fake_kedro_cli, tmp_path):
        """Check the error if keys are missing from config file."""
        output_dir = tmp_path / "test_dir"
        output_dir.mkdir(parents=True)

        _create_config_file(
            self.config_path, self.project_name, self.repo_name, str(output_dir)
        )

        starter_path = tmp_path / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))
        with (starter_path / "prompts.yml").open(mode="a+") as prompts_file:
            yaml.dump({"extra_key": {"title": "extra_key"}}, prompts_file)

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "-c", self.config_path, "-s", str(starter_path)],
        )

        assert result.exit_code != 0
        assert "extra_key not found" in result.output

    def test_bad_yaml(self, fake_kedro_cli):
        """Check the error if config YAML is invalid."""
        Path(self.config_path).write_text(
            "output_dir: \nproject_name:\ttest\nrepo_name:\ttest1\n"
        )
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "-c", self.config_path]
        )
        assert result.exit_code != 0
        assert "Failed to generate project: could not load config" in result.output


def test_default_config_up_to_date():
    """Validate the contents of the default config file."""
    cookie_json_path = Path(TEMPLATE_PATH) / "cookiecutter.json"
    cookie = json.loads(cookie_json_path.read_text("utf-8"))

    cookie_keys = [
        key for key in cookie if not key.startswith("_") and key != "kedro_version"
    ]
    with open(TEMPLATE_PATH / "prompts.yml") as prompts:
        default_config_keys = yaml.safe_load(prompts)

    assert set(cookie_keys) == set(default_config_keys)


class TestNewWithStarter:

    repo_name = "project-test"
    package_name = "package_test"
    project_name = "Test"

    def test_new_with_valid_starter_absolute_path(self, fake_kedro_cli, tmp_path):
        starter_path = tmp_path / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(starter_path)],
            _make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            project_name=self.project_name,
            repo_name=self.repo_name,
            python_package=self.package_name,
        )

    def test_new_with_valid_starter_relative_path(self, fake_kedro_cli, tmp_path):
        starter_path = tmp_path / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", "starter"],
            _make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            project_name=self.project_name,
            repo_name=self.repo_name,
            python_package=self.package_name,
        )

    def test_new_with_invalid_starter_path_should_raise(self, fake_kedro_cli):
        invalid_starter_path = "/foo/bar"
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", invalid_starter_path],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code != 0
        assert (
            f"Kedro project template not found at {invalid_starter_path}"
            in result.output
        )

    @pytest.mark.parametrize(
        "alias,expected_starter_repo",
        [
            (
                "pyspark-iris",
                "git+https://github.com/quantumblacklabs/kedro-starters.git",
            ),
        ],
    )
    def test_new_with_starter_alias(
        self, alias, expected_starter_repo, fake_kedro_cli, mocker
    ):
        mocked_cookie = mocker.patch("cookiecutter.main.cookiecutter")
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", alias],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        actual_starter_repo = mocked_cookie.call_args[0][0]
        starter_directory = mocked_cookie.call_args[1]["directory"]
        assert actual_starter_repo == expected_starter_repo
        assert starter_directory == alias

    def test_new_starter_with_checkout(self, fake_kedro_cli, mocker):
        starter_path = "some-starter"
        checkout_version = "some-version"
        output_dir = str(Path.cwd())
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocker.patch("cookiecutter.generate.generate_context")
        mocked_cookiecutter = mocker.patch(
            "cookiecutter.main.cookiecutter", return_value=starter_path
        )
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code == 0, result.output
        mocked_cookiecutter.assert_called_once_with(
            starter_path,
            checkout=checkout_version,
            extra_context={"kedro_version": version},
            no_input=True,
            output_dir=output_dir,
        )

    def test_new_starter_with_checkout_invalid_checkout(self, fake_kedro_cli, mocker):
        starter_path = "some-starter"
        checkout_version = "some-version"
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocker.patch(
            "cookiecutter.repository.determine_repo_dir",
            side_effect=RepositoryCloneFailed,
        )
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code
        pattern = (
            f"Kedro project template not found at {starter_path}. "
            f"Specified tag {checkout_version}"
        )
        assert pattern in result.output

    @pytest.mark.parametrize("starter_path", ["some-starter", "git+some-starter"])
    def test_new_starter_with_checkout_invalid_checkout_alternative_tags(
        self, fake_kedro_cli, mocker, starter_path
    ):
        checkout_version = "some-version"
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocker.patch(
            "cookiecutter.repository.determine_repo_dir",
            side_effect=RepositoryCloneFailed,
        )

        mocked_git = mocker.patch("kedro.framework.cli.starters.git")
        alternative_tags = "version1\nversion2"
        mocked_git.cmd.Git.return_value.ls_remote.return_value = alternative_tags

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code
        tags = sorted(set(alternative_tags.split("\n")))
        pattern = (
            f"Kedro project template not found at {starter_path}. "
            f"Specified tag {checkout_version}. The following tags are available: {', '.join(tags)}"
        )
        assert pattern in result.output
        mocked_git.cmd.Git.return_value.ls_remote.assert_called_once_with(
            "--tags", starter_path.replace("git+", "")
        )

    def test_checkout_flag_without_starter(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--checkout", "some-version"],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --checkout flag without a --starter value." in result.output
        )

    def test_directory_flag_without_starter(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--directory", "some-dir"],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
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
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --directory flag with a --starter alias." in result.output
        )

    def test_prompt_user_for_config(self, fake_kedro_cli, mocker):
        starter_path = Path(__file__).parents[3].resolve()
        starter_path = str(starter_path / "features" / "steps" / "test_starter")

        output_dir = str(Path.cwd())
        mocked_cookiecutter = mocker.patch(
            "cookiecutter.main.cookiecutter", return_value=starter_path
        )
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", starter_path],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code == 0, result.output
        mocked_cookiecutter.assert_called_once_with(
            starter_path,
            extra_context={
                "kedro_version": version,
                "project_name": self.project_name,
                "python_package": self.package_name,
                "repo_name": self.repo_name,
            },
            no_input=True,
            output_dir=output_dir,
            checkout=version,
        )

    def test_raise_error_when_prompt_no_title(self, fake_kedro_cli, tmp_path):
        starter_path = tmp_path / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))
        with open(starter_path / "prompts.yml", "w+") as prompts_file:
            yaml.dump({"repo_name": {}}, prompts_file)

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(starter_path)],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code != 0
        assert (
            "Each prompt must have a title field to be valid" in result.output
        ), result.output

    def test_raise_error_when_prompt_invalid_yaml(self, fake_kedro_cli, tmp_path):
        starter_path = tmp_path / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))
        (starter_path / "prompts.yml").write_text("invalid\tyaml")

        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(starter_path)],
            input=_make_cli_prompt_input(
                project_name=self.project_name,
                python_package=self.package_name,
                repo_name=self.repo_name,
            ),
        )
        assert result.exit_code != 0
        assert (
            "Failed to generate project: could not load prompts.yml." in result.output
        ), result.output

    def test_starter_list(self, fake_kedro_cli):
        """Check that `kedro starter list` prints out all starter aliases."""
        result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])

        assert result.exit_code == 0, result.output
        for alias in _STARTER_ALIASES:
            assert alias in result.output
