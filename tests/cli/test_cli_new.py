# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""This module contains unit test for the cli command 'kedro new'
"""

import json
import os
from pathlib import Path

import pytest
import yaml

from kedro import __version__ as version
from kedro.cli.cli import TEMPLATE_PATH, _fix_user_path, _get_default_config, cli

FILES_IN_TEMPLATE_NO_EXAMPLE = 38
FILES_IN_TEMPLATE_WITH_EXAMPLE = 47


# pylint: disable=too-many-arguments
def _invoke(
    cli_runner,
    args,
    project_name=None,
    repo_name=None,
    python_package=None,
    include_example=None,
):

    click_prompts = (project_name, repo_name, python_package, include_example)
    input_string = "\n".join(x or "" for x in click_prompts)

    return cli_runner.invoke(cli, args, input=input_string)


# pylint: disable=too-many-arguments
def _assert_template_ok(
    result,
    files_in_template,
    repo_name=None,
    project_name="New Kedro Project",
    output_dir=".",
    package_name=None,
):
    print(result.output)
    assert result.exit_code == 0
    assert "Project generated in" in result.output

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
    include_example = "y"

    def test_new_no_example(self, cli_runner):
        """Test new project creation without code example."""
        project_name = "Test"
        result = _invoke(
            cli_runner,
            ["-v", "new"],
            project_name=project_name,
            repo_name=self.repo_name,
            include_example="N",
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE_NO_EXAMPLE,
            repo_name=self.repo_name,
            project_name=project_name,
            package_name="test",
        )

    def test_new_with_example(self, cli_runner):
        """Test new project creation with code example."""
        project_name = "Test"
        result = _invoke(
            cli_runner,
            ["-v", "new"],
            project_name=project_name,
            repo_name=self.repo_name,
            include_example="y",
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE_WITH_EXAMPLE,
            repo_name=self.repo_name,
            project_name=project_name,
            package_name="test",
        )

    def test_new_custom_dir(self, cli_runner):
        """Test that default package name does not change if custom
        repo name was specified."""
        result = _invoke(
            cli_runner,
            ["new"],
            repo_name=self.repo_name,
            include_example=self.include_example,
        )
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE_WITH_EXAMPLE,
            repo_name=self.repo_name,
            package_name="new_kedro_project",
        )

    def test_new_correct_path(self, cli_runner):
        """Test new project creation with the default project name."""
        result = _invoke(
            cli_runner,
            ["new"],
            repo_name=self.repo_name,
            include_example=self.include_example,
        )
        _assert_template_ok(
            result, FILES_IN_TEMPLATE_WITH_EXAMPLE, repo_name=self.repo_name
        )

    def test_fail_if_dir_exists(self, cli_runner):
        """Check the error if the output directory already exists."""
        empty_file = Path(self.repo_name) / "empty_file"
        empty_file.parent.mkdir(parents=True)
        empty_file.touch()

        old_contents = list(Path(self.repo_name).iterdir())

        result = _invoke(
            cli_runner,
            ["-v", "new"],
            repo_name=self.repo_name,
            include_example=self.include_example,
        )

        assert list(Path(self.repo_name).iterdir()) == old_contents
        assert "directory already exists" in result.output
        assert result.exit_code != 0

    @pytest.mark.parametrize("repo_name", [".repo", "re!po", "-repo", "repo-"])
    def test_bad_repo_name(self, cli_runner, repo_name):
        """Check the error if the repository name is invalid."""
        result = _invoke(
            cli_runner,
            ["new"],
            repo_name=repo_name,
            include_example=self.include_example,
        )
        assert result.exit_code == 0
        assert "is not a valid repository name." in result.output

    @pytest.mark.parametrize(
        "pkg_name", ["0package", "_", "package-name", "package name"]
    )
    def test_bad_pkg_name(self, cli_runner, pkg_name):
        """Check the error if the package name is invalid."""
        result = _invoke(
            cli_runner,
            ["new"],
            python_package=pkg_name,
            include_example=self.include_example,
        )
        assert result.exit_code == 0
        assert "is not a valid Python package name." in result.output

    @pytest.mark.parametrize("include_example", ["A", "a", "_", "?"])
    def test_bad_include_example(self, cli_runner, include_example):
        """Check the error include example response is invalid."""
        result = _invoke(
            cli_runner,
            ["new"],
            python_package=self.package_name,
            include_example=include_example,
        )
        assert result.exit_code == 0
        assert "invalid input" in result.output


def _create_config_file(
    config_path, project_name, repo_name, output_dir=None, include_example=False
):
    config = {
        "project_name": project_name,
        "repo_name": repo_name,
        "python_package": repo_name.replace("-", "_"),
        "include_example": include_example,
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
    include_example = True

    def test_config_does_not_exist(self, cli_runner):
        """Check the error if the config file does not exist."""
        result = _invoke(cli_runner, ["new", "-c", "missing.yml"])
        assert result.exit_code != 0
        assert "does not exist" in result.output

    def test_empty_config(self, cli_runner):
        """Check the error if the config file is empty."""
        open("touch", "a").close()
        result = _invoke(cli_runner, ["-v", "new", "-c", "touch"])
        assert result.exit_code != 0
        assert "is empty" in result.output

    def test_new_from_config_no_example(self, cli_runner):
        """Test project created from config without example code."""
        output_dir = "test_dir"
        include_example = False
        Path(output_dir).mkdir(parents=True)
        _create_config_file(
            self.config_path,
            self.project_name,
            self.repo_name,
            output_dir,
            include_example,
        )
        result = _invoke(cli_runner, ["-v", "new", "--config", self.config_path])
        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE_NO_EXAMPLE,
            self.repo_name,
            self.project_name,
            output_dir,
        )

    def test_new_from_config_with_example(self, cli_runner):
        """Test project created from config with example code."""
        output_dir = "test_dir"
        Path(output_dir).mkdir(parents=True)
        _create_config_file(
            self.config_path,
            self.project_name,
            self.repo_name,
            output_dir,
            self.include_example,
        )
        result = _invoke(cli_runner, ["-v", "new", "--config", self.config_path])

        _assert_template_ok(
            result,
            FILES_IN_TEMPLATE_WITH_EXAMPLE,
            self.repo_name,
            self.project_name,
            output_dir,
        )

    def test_wrong_config(self, cli_runner):
        """Check the error if the output directory is invalid."""
        output_dir = "/usr/invalid/dir"
        _create_config_file(
            self.config_path, self.project_name, self.repo_name, output_dir
        )

        result = _invoke(cli_runner, ["new", "-c", self.config_path])

        assert result.exit_code != 0
        assert "is not a valid output directory." in result.output

    def test_bad_yaml(self, cli_runner):
        """Check the error if config YAML is invalid."""
        Path(self.config_path).write_text(
            "output_dir: \nproject_name:\ttest\nrepo_name:\ttest1\n"
        )
        result = _invoke(cli_runner, ["new", "-c", self.config_path])

        assert result.exit_code != 0
        assert "that cannot start any token" in result.output

    def test_output_dir_with_tilde_in_path(self, mocker):
        """Check the error if the output directory contains "~" ."""
        home_dir = os.path.join("/home", "directory")
        output_dir = os.path.join("~", "here")

        expected = os.path.join(home_dir, "here")

        mocker.patch.dict("os.environ", {"HOME": home_dir, "USERPROFILE": home_dir})
        actual = _fix_user_path(output_dir)
        assert actual == expected

    def test_output_dir_with_relative_path(self, mocker):
        """Check the error if the output directory contains a relative path."""
        home_dir = os.path.join("/home", "directory")
        current_dir = os.path.join(home_dir, "current", "directory")
        output_dir = os.path.join("path", "to", "here")

        expected = os.path.join(current_dir, output_dir)

        mocker.patch.dict("os.environ", {"HOME": home_dir, "USERPROFILE": home_dir})
        mocker.patch("os.getcwd", return_value=current_dir)
        actual = _fix_user_path(output_dir)
        assert actual == expected

    def test_missing_output_dir(self, cli_runner):
        """Check the error if config YAML does not contain the output
        directory."""
        _create_config_file(
            self.config_path,
            self.project_name,
            self.repo_name,
            output_dir=None,
            include_example=self.include_example,
        )  # output dir missing
        result = _invoke(cli_runner, ["-v", "new", "--config", self.config_path])

        assert result.exit_code != 0
        assert "[output_dir] not found in" in result.output
        assert not Path(self.repo_name).exists()

    def test_missing_include_example(self, cli_runner):
        """Check the error if config YAML does not contain include example."""
        output_dir = "test_dir"
        Path(output_dir).mkdir(parents=True)
        _create_config_file(
            self.config_path,
            self.project_name,
            self.repo_name,
            output_dir,
            include_example=None,
        )  # include_example missing
        result = _invoke(cli_runner, ["-v", "new", "--config", self.config_path])

        assert result.exit_code != 0
        assert "It must be a boolean value" in result.output
        assert not Path(self.repo_name).exists()


def test_default_config_up_to_date():
    """Validate the contents of the default config file."""
    cookie_json_path = Path(TEMPLATE_PATH) / "cookiecutter.json"
    cookie = json.loads(cookie_json_path.read_text("utf-8"))

    cookie_keys = [
        key for key in cookie if not key.startswith("_") and key != "kedro_version"
    ]
    cookie_keys.append("output_dir")
    default_config_keys = _get_default_config().keys()

    assert set(cookie_keys) == set(default_config_keys)
