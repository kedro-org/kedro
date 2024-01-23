"""This module contains unit test for the cli command 'kedro new'
"""
from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner
from cookiecutter.exceptions import RepositoryCloneFailed

from kedro import __version__ as version
from kedro.framework.cli.starters import (
    _OFFICIAL_STARTER_SPECS_DICT,
    TEMPLATE_PATH,
    KedroStarterSpec,
    _convert_tool_short_names_to_numbers,
    _parse_tools_input,
    _parse_yes_no_to_bool,
    _validate_tool_selection,
)
from tests.framework.cli.starters.conftest import (
    _assert_template_ok,
    _clean_up_project,
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


class TestParseToolsInput:
    @pytest.mark.parametrize(
        "input,expected",
        [
            ("1", ["1"]),
            ("1,2,3", ["1", "2", "3"]),
            ("2-4", ["2", "3", "4"]),
            ("3-3", ["3"]),
            ("all", ["1", "2", "3", "4", "5", "6", "7"]),
            ("none", []),
        ],
    )
    def test_parse_tools_valid(self, input, expected):
        result = _parse_tools_input(input)
        assert result == expected

    @pytest.mark.parametrize(
        "input",
        ["5-2", "3-1"],
    )
    def test_parse_tools_invalid_range(self, input, capsys):
        with pytest.raises(SystemExit):
            _parse_tools_input(input)
        message = f"'{input}' is an invalid range for project tools.\nPlease ensure range values go from smaller to larger."
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        "input,right_border",
        [("3-9", "9"), ("3-10000", "10000")],
    )
    def test_parse_tools_range_too_high(self, input, right_border, capsys):
        with pytest.raises(SystemExit):
            _parse_tools_input(input)
        message = f"'{right_border}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in capsys.readouterr().err

    @pytest.mark.parametrize(
        "input,last_invalid",
        [("0,3,5", "0"), ("1,3,8", "8"), ("0-4", "0")],
    )
    def test_parse_tools_invalid_selection(self, input, last_invalid, capsys):
        with pytest.raises(SystemExit):
            selected = _parse_tools_input(input)
            _validate_tool_selection(selected)
        message = f"'{last_invalid}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in capsys.readouterr().err


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
        _clean_up_project(Path("./new-kedro-project"))

    def test_relative_path(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))

    def test_relative_path_directory(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", ".", "--directory", "template"],
            input=_make_cli_prompt_input(),
        )
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))

    def test_alias(self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter):
        CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights-pandas"],
            input=_make_cli_prompt_input(),
        )
        kwargs = {
            "template": "git+https://github.com/kedro-org/kedro-starters.git",
            "checkout": version,
            "directory": "spaceflights-pandas",
        }
        assert kwargs.items() <= mock_determine_repo_dir.call_args[1].items()
        assert kwargs.items() <= mock_cookiecutter.call_args[1].items()

    def test_alias_custom_checkout(
        self, fake_kedro_cli, mock_determine_repo_dir, mock_cookiecutter
    ):
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

    def test_no_hint(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "-v", "--starter", str(Path("./template").resolve())],
            input=_make_cli_prompt_input(),
        )
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            not in result.output
        )
        assert "You have selected" not in result.output
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))


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


class TestParseYesNoToBools:
    @pytest.mark.parametrize(
        "input",
        ["yes", "YES", "y", "Y", "yEs"],
    )
    def parse_yes_no_to_bool_responds_true(self, input):
        assert _parse_yes_no_to_bool(input) is True

    @pytest.mark.parametrize(
        "input",
        ["no", "NO", "n", "N", "No", ""],
    )
    def parse_yes_no_to_bool_responds_false(self, input):
        assert _parse_yes_no_to_bool(input) is False

    def parse_yes_no_to_bool_responds_none(self):
        assert _parse_yes_no_to_bool(None) is None


class TestValidateSelection:
    def test_validate_tool_selection_valid(self):
        tools = ["1", "2", "3", "4"]
        assert _validate_tool_selection(tools) is None

    def test_validate_tool_selection_invalid_single_tool(self, capsys):
        tools = ["8"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_invalid_multiple_tools(self, capsys):
        tools = ["8", "10", "15"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_mix_valid_invalid_tools(self, capsys):
        tools = ["1", "8", "3", "15"]
        with pytest.raises(SystemExit):
            _validate_tool_selection(tools)
        message = "is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in capsys.readouterr().err

    def test_validate_tool_selection_empty_list(self):
        tools = []
        assert _validate_tool_selection(tools) is None


class TestConvertToolNamesToNumbers:
    @pytest.mark.parametrize(
        "tool_names, expected_conversion",
        [
            ("lint,test,docs", ["1", "2", "4"]),
            ("all", ["1", "2", "3", "4", "5", "6", "7"]),
            (" lint , test , docs ", ["1", "2", "4"]),
            ("Lint,TEST,Docs", ["1", "2", "4"]),
            ("lint,test,tests", ["1", "2"]),
            ("lint,invalid_tool,docs", ["1", "4"]),
            ("invalid_tool1,invalid_tool2", []),
            ("none", []),
            ("", []),
        ],
    )
    def test_convert_tool_short_names_to_numbers_or_empty(
        self, tool_names, expected_conversion
    ):
        result = _convert_tool_short_names_to_numbers(tool_names)
        assert result == expected_conversion
