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

import click
import pytest
import yaml
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.cli import cli
from kedro.framework.cli.starters import (
    _STARTER_ALIASES,
    TEMPLATE_PATH,
    _get_prompts_config,
    create_cli,
)

FILES_IN_TEMPLATE = 37


def _invoke(
    cli_runner,
    args,
    project_name=None,
    repo_name="repo_name",
    python_package="python_package",
):

    click_prompts = (project_name, repo_name, python_package)
    input_string = "\n".join(x or "" for x in click_prompts)
    # This is needed just for the tests, those CLI groups are merged in our
    # code when invoking `kedro` but when imported, they still need to be merged
    kedro_cli = click.CommandCollection(sources=[cli, create_cli])
    return cli_runner.invoke(kedro_cli, args, input=input_string)


# pylint: disable=too-many-arguments
def _assert_template_ok(
    result,
    files_in_template,
    repo_name=None,
    project_name="New Kedro Project",
    output_dir=".",
    package_name="python_package",
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

        if package_name:
            assert (full_path / "src" / package_name / "__init__.py").is_file()


class TestInteractiveNew:
    """Tests for running `kedro new` interactively."""

    repo_name = "project-test"
    package_name = "package_test"

    def test_new(self, cli_runner):
        """Test new project creation without code example."""
        project_name = "Test"
        result = _invoke(
            cli_runner,
            ["new", "-v"],
            project_name=project_name,
            repo_name=self.repo_name,
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            repo_name=self.repo_name,
            project_name=project_name,
        )

    def test_new_custom_dir(self, cli_runner):
        """Test that default package name does not change if custom
        repo name was specified."""
        result = _invoke(cli_runner, ["new"], repo_name=self.repo_name)
        _assert_template_ok(
            result, FILES_IN_TEMPLATE, repo_name=self.repo_name,
        )

    def test_new_correct_path(self, cli_runner):
        """Test new project creation with the default project name."""
        result = _invoke(cli_runner, ["new"], repo_name=self.repo_name)
        _assert_template_ok(result, FILES_IN_TEMPLATE, repo_name=self.repo_name)

    def test_fail_if_dir_exists(self, cli_runner):
        """Check the error if the output directory already exists."""
        empty_file = Path(self.repo_name) / "empty_file"
        empty_file.parent.mkdir(parents=True)
        empty_file.touch()

        old_contents = list(Path(self.repo_name).iterdir())

        result = _invoke(cli_runner, ["new", "-v"], repo_name=self.repo_name)

        assert list(Path(self.repo_name).iterdir()) == old_contents
        assert "directory already exists" in result.output
        assert result.exit_code != 0

    @pytest.mark.parametrize(
        "repo_name", [".repo\nvalid", "re!po\nvalid", "-repo\nvalid", "repo-\nvalid"]
    )
    def test_bad_repo_name(self, cli_runner, repo_name):
        """Check the error if the repository name is invalid."""
        result = _invoke(cli_runner, ["new"], repo_name=repo_name)
        assert (
            "is an invalid value.\nIt must contain only word symbols" in result.output
        )
        assert result.exit_code != 0

    @pytest.mark.parametrize(
        "pkg_name",
        ["0package\nvalid", "_\nvalid", "package-name\nvalid", "package name\nvalid"],
    )
    def test_bad_pkg_name(self, cli_runner, pkg_name):
        """Check the error if the package name is invalid."""
        result = _invoke(cli_runner, ["new"], python_package=pkg_name)
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

    def test_config_does_not_exist(self, cli_runner):
        """Check the error if the config file does not exist."""
        result = _invoke(cli_runner, ["new", "-c", "missing.yml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_empty_config(self, cli_runner):
        """Check the error if the config file is empty."""
        open("touch", "a").close()
        result = _invoke(cli_runner, ["new", "-v", "-c", "touch"])
        assert result.exit_code != 0
        assert "is empty" in result.output

    def test_new_from_config(self, cli_runner):
        """Test project created from config without example code."""
        output_dir = "test_dir"
        Path(output_dir).mkdir(parents=True)
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir
        )
        result = _invoke(cli_runner, ["new", "-v", "--config", self.config_path])
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            self.repo_name,
            self.project_name,
            output_dir,
            self.repo_name.replace("-", "_"),
        )

    def test_wrong_config(self, cli_runner):
        """Check the error if the output directory is invalid."""
        output_dir = "/usr/invalid/dir"
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir
        )

        result = _invoke(cli_runner, ["new", "-v", "-c", self.config_path])
        assert result.exit_code != 0
        assert "is not a valid output directory." in result.output

    def test_bad_yaml(self, cli_runner):
        """Check the error if config YAML is invalid."""
        Path(self.config_path).write_text(
            "output_dir: \nproject_name:\ttest\nrepo_name:\ttest1\n"
        )
        result = _invoke(cli_runner, ["new", "-v", "-c", self.config_path])
        assert result.exit_code != 0
        assert "that cannot start any token" in result.output

    def test_missing_output_dir(self, cli_runner):
        """Check the error if config YAML does not contain the output
        directory."""
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir=None
        )  # output dir missing
        result = _invoke(cli_runner, ["new", "-v", "--config", self.config_path])

        assert result.exit_code != 0
        assert "[output_dir] not found in" in result.output
        assert not Path(self.repo_name).exists()


def test_default_config_up_to_date():
    """Validate the contents of the default config file."""
    cookie_json_path = Path(TEMPLATE_PATH) / "cookiecutter.json"
    cookie = json.loads(cookie_json_path.read_text("utf-8"))

    cookie_keys = [
        key for key in cookie if not key.startswith("_") and key != "kedro_version"
    ]
    default_config_keys = _get_prompts_config().keys()

    assert set(cookie_keys) == set(default_config_keys)


class TestNewWithStarter:

    repo_name = "project-test"
    package_name = "package_test"
    project_name = "Test"

    def test_new_with_valid_starter(self, cli_runner, tmpdir):
        starter_path = tmpdir / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))

        result = _invoke(
            cli_runner,
            ["new", "-v", "--starter", str(starter_path)],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE,
            repo_name=self.repo_name,
            project_name=self.project_name,
            package_name=self.package_name,
        )

    def test_new_with_invalid_starter_path_should_raise(self, cli_runner):
        invalid_starter_path = "/foo/bar"
        result = _invoke(
            cli_runner,
            ["new", "-v", "--starter", invalid_starter_path],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
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
        self, alias, expected_starter_repo, cli_runner, mocker, tmp_path
    ):
        mocker.patch(
            "kedro.framework.cli.starters.tempfile.TemporaryDirectory",
            return_value=tmp_path,
        )
        mocked_cookie = mocker.patch("cookiecutter.main.cookiecutter")
        _invoke(
            cli_runner,
            ["new", "--starter", alias],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        actual_starter_repo = mocked_cookie.call_args[0][0]
        starter_directory = mocked_cookie.call_args[1]["directory"]
        assert actual_starter_repo == expected_starter_repo
        assert starter_directory == alias

    def test_new_starter_with_checkout(self, cli_runner, mocker):
        starter_path = "some-starter"
        checkout_version = "some-version"
        output_dir = str(Path.cwd())
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocked_cookiecutter = mocker.patch(
            "cookiecutter.main.cookiecutter", return_value=starter_path
        )
        result = _invoke(
            cli_runner,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code == 0, result.output
        mocked_cookiecutter.assert_called_once_with(
            starter_path,
            checkout=checkout_version,
            extra_context={"kedro_version": version},
            no_input=True,
            output_dir=output_dir,
        )

    def test_new_starter_with_checkout_invalid_checkout(self, cli_runner, mocker):
        starter_path = "some-starter"
        checkout_version = "some-version"
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocked_cookiecutter = mocker.patch(
            "cookiecutter.main.cookiecutter", side_effect=RepositoryCloneFailed
        )
        result = _invoke(
            cli_runner,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code
        assert (
            f"Kedro project template not found at {starter_path} with tag {checkout_version}"
            in result.output
        )
        output_dir = str(Path.cwd())
        mocked_cookiecutter.assert_called_once_with(
            starter_path,
            checkout=checkout_version,
            extra_context={"kedro_version": version},
            no_input=True,
            output_dir=output_dir,
        )

    @pytest.mark.parametrize("starter_path", ["some-starter", "git+some-starter"])
    def test_new_starter_with_checkout_invalid_checkout_alternative_tags(
        self, cli_runner, mocker, starter_path
    ):
        checkout_version = "some-version"
        mocker.patch("cookiecutter.repository.repository_has_cookiecutter_json")
        mocker.patch(
            "cookiecutter.main.cookiecutter", side_effect=RepositoryCloneFailed
        )
        mocked_git = mocker.patch("kedro.framework.cli.starters.git")
        alternative_tags = "version1\nversion2"
        mocked_git.cmd.Git.return_value.ls_remote.return_value = alternative_tags

        result = _invoke(
            cli_runner,
            ["new", "--starter", starter_path, "--checkout", checkout_version],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code
        tags = sorted(set(alternative_tags.split("\n")))
        pattern = (
            f"Kedro project template not found at {starter_path} with tag {checkout_version}. "
            f"The following tags are available: {', '.join(tags)}"
        )
        assert pattern in result.output
        mocked_git.cmd.Git.return_value.ls_remote.assert_called_once_with(
            "--tags", starter_path.replace("git+", "")
        )

    def test_checkout_flag_without_starter(self, cli_runner):
        result = _invoke(
            cli_runner,
            ["new", "--checkout", "some-version"],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --checkout flag without a --starter value." in result.output
        )

    def test_directory_flag_without_starter(self, cli_runner):
        result = _invoke(
            cli_runner,
            ["new", "--directory", "some-dir"],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --directory flag without a --starter value."
            in result.output
        )

    def test_directory_flag_with_starter_alias(self, cli_runner):
        result = _invoke(
            cli_runner,
            ["new", "--starter", "pyspark-iris", "--directory", "some-dir"],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --directory flag with a --starter alias." in result.output
        )

    def test_prompt_user_for_config(self, cli_runner, mocker):
        starter_path = Path(__file__).parents[3].resolve()
        starter_path = starter_path / "features" / "steps" / "test_starter"

        output_dir = str(Path.cwd())
        mocked_cookiecutter = mocker.patch(
            "cookiecutter.main.cookiecutter", return_value=starter_path
        )
        result = _invoke(
            cli_runner,
            ["new", "--starter", starter_path],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code == 0, result.output
        mocked_cookiecutter.assert_called_once_with(
            str(starter_path),
            checkout=version,
            extra_context={
                "kedro_version": version,
                "output_dir": output_dir,
                "project_name": self.project_name,
                "python_package": self.package_name,
                "repo_name": self.repo_name,
            },
            no_input=True,
            output_dir=output_dir,
        )

    def test_raise_error_when_prompt_invalid(self, cli_runner, tmpdir):
        starter_path = tmpdir / "starter"
        shutil.copytree(TEMPLATE_PATH, str(starter_path))
        with open(starter_path / "prompts.yml", "w+") as prompts_file:
            yaml.dump({"repo_name": {}}, prompts_file)

        result = _invoke(
            cli_runner,
            ["new", "-v", "--starter", str(starter_path)],
            project_name=self.project_name,
            python_package=self.package_name,
            repo_name=self.repo_name,
        )
        assert result.exit_code != 0
        assert (
            "Each prompt must have a title field to be valid" in result.output
        ), result.output

    def test_starter_list(self, cli_runner):
        """Check that `kedro starter list` prints out all starter aliases."""
        result = _invoke(cli_runner, ["starter", "list"])

        assert result.exit_code == 0, result.output
        for alias in _STARTER_ALIASES:
            assert alias in result.output
