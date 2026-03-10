"""Tests for starters flow: starter list command and starter-specific tests."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.starters import (
    _OFFICIAL_STARTER_SPECS_DICT,
    KedroStarterSpec,
)
from tests.framework.cli.starters.utils import (
    _assert_template_ok,
    _make_cli_prompt_input,
)


def test_starter_list(fake_kedro_cli):
    """Check that `kedro starter list` prints out all starter aliases."""
    result = CliRunner().invoke(fake_kedro_cli, ["starter", "list"])

    assert result.exit_code == 0, result.output
    for alias in _OFFICIAL_STARTER_SPECS_DICT:
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
class TestNewWithStarterValid:
    """Tests for using starters with mocked git interactions."""

    def test_absolute_path(self, fake_kedro_cli, template_in_cwd):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(template_in_cwd)],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_relative_path(self, fake_kedro_cli, template_in_cwd):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_relative_path_directory(self, fake_kedro_cli, template_in_cwd):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", ".", "--directory", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)

    def test_alias(self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter):
        """Test starter alias with mocked git interactions."""
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights-pandas"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/kedro-org/kedro-starters.git",
            "directory": "spaceflights-pandas",
        }
        starters_version = mock_determine_repo_dir.call_args[1].pop("checkout", None)

        assert starters_version in [version, "main"]
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_alias_custom_checkout(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
        """Test starter alias with custom checkout, mocked git interactions."""
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights-pandas", "--checkout", "my_checkout"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/kedro-org/kedro-starters.git",
            "checkout": "my_checkout",
            "directory": "spaceflights-pandas",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_git_repo(self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter):
        """Test git repo starter with mocked git interactions."""
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "git+https://github.com/fake/fake.git"],
            input=_make_cli_prompt_input(),
        )

        kwargs = {
            "template": "git+https://github.com/fake/fake.git",
            "directory": None,
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        del kwargs["directory"]
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_git_repo_custom_checkout(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
        """Test git repo starter with custom checkout, mocked git interactions."""
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
        """Test git repo starter with custom directory, mocked git interactions."""
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
            "directory": "my_directory",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_no_hint(self, fake_kedro_cli, template_in_cwd):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(template_in_cwd)],
            input=_make_cli_prompt_input(),
        )
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            not in result.output
        )
        assert "You have selected" not in result.output
        _assert_template_ok(result)


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
            ("spaceflights-pandas", "https://github.com/kedro-org/kedro-starters.git"),
            (
                "git+https://github.com/fake/fake.git",
                "https://github.com/fake/fake.git",
            ),
        ],
    )
    def test_invalid_checkout(self, starter, repo, fake_kedro_cli):
        """Test invalid checkout with mocked git interactions."""
        with (
            patch(
                "cookiecutter.repository.determine_repo_dir",
                side_effect=RepositoryCloneFailed,
            ),
            patch("git.cmd.Git") as mock_git,
        ):
            mock_ls_remote = mock_git.return_value.ls_remote
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
