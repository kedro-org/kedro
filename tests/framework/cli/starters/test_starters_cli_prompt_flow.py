from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
    _fetch_validate_parse_config_from_user_prompts,
)
from tests.framework.cli.starters.conftest import (
    _assert_requirements_ok,
    _assert_template_ok,
    _clean_up_project,
    _make_cli_prompt_input,
    _write_yaml,
)


@pytest.mark.usefixtures("chdir_to_tmp", "patch_cookiecutter_args")
class TestNewFromUserPromptsValid:
    """Tests for running `kedro new` interactively."""

    def test_default(self, fake_kedro_cli):
        """Test new project creation using default New Kedro Project options."""
        result = CliRunner().invoke(
            fake_kedro_cli, ["new"], input=_make_cli_prompt_input()
        )
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))

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
        _clean_up_project(Path("./my-project"))

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
        _clean_up_project(Path("./my-project--1"))

    def test_no_prompts(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        (Path("template") / "prompts.yml").unlink()
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))

    def test_empty_prompts(self, fake_kedro_cli):
        shutil.copytree(TEMPLATE_PATH, "template")
        _write_yaml(Path("template") / "prompts.yml", {})
        result = CliRunner().invoke(fake_kedro_cli, ["new", "--starter", "template"])
        _assert_template_ok(result)
        _clean_up_project(Path("./new-kedro-project"))

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
        _clean_up_project(Path("./my-project"))

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
        _clean_up_project(Path("./my_custom_repo"))

    def test_fetch_validate_parse_config_from_user_prompts_without_context(self):
        required_prompts = {}
        message = "No cookiecutter context available."
        with pytest.raises(Exception, match=message):
            _fetch_validate_parse_config_from_user_prompts(
                prompts=required_prompts, cookiecutter_context=None
            )

    @pytest.mark.parametrize(
        "tools",
        [
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "2,3,4",
            "3-5",
            "1,2,4-6",
            "1,2,4-6,7",
            "4-6,7",
            "1, 2 ,4 - 6, 7",
            "1-3, 5-7",
            "all",
            "1, 2, 3",
            "  1,  2, 3  ",
            "ALL",
            "none",
            "",
        ],
    )
    @pytest.mark.parametrize("example_pipeline", ["Yes", "No"])
    def test_valid_tools_and_example(self, fake_kedro_cli, tools, example_pipeline):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(
                tools=tools, example_pipeline=example_pipeline
            ),
        )

        _assert_template_ok(result, tools=tools, example_pipeline=example_pipeline)
        _assert_requirements_ok(result, tools=tools)
        if tools not in ("none", ""):
            assert "You have selected the following project tools:" in result.output
        else:
            assert "You have selected no project tools" in result.output
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            in result.output
        )
        _clean_up_project(Path("./new-kedro-project"))

    @pytest.mark.parametrize("example_pipeline", ["y", "n", "N", "YEs", "    yeS   "])
    def test_valid_example(self, fake_kedro_cli, example_pipeline):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(example_pipeline=example_pipeline),
        )

        _assert_template_ok(result, example_pipeline=example_pipeline)
        _clean_up_project(Path("./new-kedro-project"))


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
            "is an invalid value for project name.\nIt must contain only alphanumeric symbols"
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
            "is an invalid value for project name.\nIt must contain only alphanumeric symbols"
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

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "-1", "3-", "1 1"],
    )
    def test_invalid_tools(self, fake_kedro_cli, bad_input):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(tools=bad_input),
        )

        assert result.exit_code != 0
        assert "is an invalid value for project tools." in result.output
        assert (
            "Invalid input. Please select valid options for project tools using comma-separated values, ranges, or 'all/none'.\n"
            in result.output
        )

    @pytest.mark.parametrize(
        "input,last_invalid",
        [
            ("0,3,5", "0"),
            ("1,3,9", "9"),
            ("0-4", "0"),
            ("99", "99"),
            ("3-9", "9"),
            ("3-10000", "10000"),
        ],
    )
    def test_invalid_tools_selection(self, fake_kedro_cli, input, last_invalid):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(tools=input),
        )

        assert result.exit_code != 0
        message = f"'{last_invalid}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6, 7."
        assert message in result.output

    @pytest.mark.parametrize(
        "input",
        ["5-2", "3-1"],
    )
    def test_invalid_tools_range(self, fake_kedro_cli, input):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(tools=input),
        )

        assert result.exit_code != 0
        message = f"'{input}' is an invalid range for project tools.\nPlease ensure range values go from smaller to larger."
        assert message in result.output

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "Not", "ye", "True", "t"],
    )
    def test_invalid_example(self, fake_kedro_cli, bad_input):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new"],
            input=_make_cli_prompt_input(example_pipeline=bad_input),
        )

        assert result.exit_code != 0
        assert "is an invalid value for example pipeline." in result.output
        assert (
            "It must contain only y, n, YES, NO, case insensitive.\n" in result.output
        )
