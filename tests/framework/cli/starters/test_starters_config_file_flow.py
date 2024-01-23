from __future__ import annotations

import shutil
from pathlib import Path

import pytest
from click.testing import CliRunner

from kedro.framework.cli.starters import (
    TEMPLATE_PATH,
    _convert_tool_short_names_to_numbers,
)
from tests.framework.cli.starters.conftest import (
    _assert_requirements_ok,
    _assert_template_ok,
    _clean_up_project,
    _write_yaml,
)

FILES_IN_TEMPLATE_WITH_NO_TOOLS = 15


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileValid:
    """Test `kedro new` with config file provided."""

    def test_required_keys_only(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)
        _clean_up_project(Path("./my-project"))

    def test_custom_required_keys(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "Project X",
            "example_pipeline": "no",
            "repo_name": "projectx",
            "python_package": "proj_x",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)
        _clean_up_project(Path("./projectx"))

    def test_custom_kedro_version(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
            "kedro_version": "my_version",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)
        _clean_up_project(Path("./my-project"))

    def test_custom_output_dir(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": "no",
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
        _clean_up_project(Path("./my-project"))

    def test_extra_keys_allowed(self, fake_kedro_cli):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), {**config, "extra_key": "my_extra_key"})
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)
        _clean_up_project(Path("./my-project"))

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
        _clean_up_project(Path("./my-project"))

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
        _clean_up_project(Path("./my-project"))

    def test_config_with_no_tools_example(self, fake_kedro_cli):
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
        _clean_up_project(Path("./my-project"))


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileInvalid:
    def test_output_dir_does_not_exist(self, fake_kedro_cli):
        """Check the error if the output directory is invalid."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": "no",
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
            "tools": "none",
            "example_pipeline": "no",
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

    def test_invalid_project_name_special_characters(self, fake_kedro_cli):
        config = {
            "tools": "none",
            "project_name": "My $Project!",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "is an invalid value for project name. It must contain only alphanumeric symbols, spaces, underscores and hyphens and be at least 2 characters long"
            in result.output
        )

    def test_invalid_project_name_too_short(self, fake_kedro_cli):
        config = {
            "tools": "none",
            "project_name": "P",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        assert result.exit_code != 0
        assert (
            "is an invalid value for project name. It must contain only alphanumeric symbols, spaces, underscores and hyphens and be at least 2 characters long"
            in result.output
        )


@pytest.mark.usefixtures("chdir_to_tmp", "patch_cookiecutter_args")
class TestToolsAndExampleFromConfigFile:
    @pytest.mark.parametrize(
        "tools",
        [
            "lint",
            "test",
            "tests",
            "log",
            "logs",
            "docs",
            "doc",
            "data",
            "pyspark",
            "viz",
            "tests,logs,doc",
            "test,data,lint",
            "log,docs,data,test,lint",
            "log, docs, data, test, lint",
            "log,       docs,     data,   test,     lint",
            "all",
            "LINT",
            "ALL",
            "TEST, LOG, DOCS",
            "test, DATA, liNt",
            "none",
            "NONE",
        ],
    )
    @pytest.mark.parametrize("example_pipeline", ["Yes", "No"])
    def test_valid_tools_and_example(self, fake_kedro_cli, tools, example_pipeline):
        """Test project created from config."""
        config = {
            "tools": tools,
            "project_name": "New Kedro Project",
            "example_pipeline": example_pipeline,
            "repo_name": "new-kedro-project",
            "python_package": "new_kedro_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        tools = _convert_tool_short_names_to_numbers(selected_tools=tools)
        tools = ",".join(tools) if tools != [] else "none"

        _assert_template_ok(result, tools=tools, example_pipeline=example_pipeline)
        _assert_requirements_ok(result, tools=tools, repo_name="new-kedro-project")
        if tools not in ("none", "NONE", ""):
            assert "You have selected the following project tools:" in result.output
        else:
            assert "You have selected no project tools" in result.output
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            not in result.output
        )
        _clean_up_project(Path("./new-kedro-project"))

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "0,3,5", "1,3,9", "llint", "tes", "test, lin"],
    )
    def test_invalid_tools(self, fake_kedro_cli, bad_input):
        """Test project created from config."""
        config = {
            "tools": bad_input,
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "Please select from the available tools: lint, test, log, docs, data, pyspark, viz, all, none"
            in result.output
        )

    def test_invalid_tools_with_starter(self, fake_kedro_cli):
        """Test project created from config with tools and example used with --starter"""
        config = {
            "tools": "all",
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        shutil.copytree(TEMPLATE_PATH, "template")
        result = CliRunner().invoke(
            fake_kedro_cli,
            [
                "new",
                "-v",
                "--config",
                "config.yml",
                "--starter=template",
            ],
        )

        assert result.exit_code != 0
        assert (
            "The --starter flag can not be used with `example_pipeline` and/or `tools` keys in the config file.\n"
            in result.output
        )

    @pytest.mark.parametrize(
        "input",
        ["lint,all", "test,none", "all,none"],
    )
    def test_invalid_tools_flag_combination(self, fake_kedro_cli, input):
        config = {
            "tools": input,
            "project_name": "My Project",
            "example_pipeline": "no",
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "Tools options 'all' and 'none' cannot be used with other options"
            in result.output
        )

    @pytest.mark.parametrize("example_pipeline", ["y", "n", "N", "YEs", "    yeS   "])
    def test_valid_example(self, fake_kedro_cli, example_pipeline):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "New Kedro Project",
            "example_pipeline": example_pipeline,
            "repo_name": "new-kedro-project",
            "python_package": "new_kedro_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        _assert_template_ok(result, **config)
        _clean_up_project(Path("./new-kedro-project"))

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "Not", "ye", "True", "t"],
    )
    def test_invalid_example(self, fake_kedro_cli, bad_input):
        """Test project created from config."""
        config = {
            "tools": "none",
            "project_name": "My Project",
            "example_pipeline": bad_input,
            "repo_name": "my-project",
            "python_package": "my_project",
        }
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "It must contain only y, n, YES, NO, case insensitive.\n" in result.output
        )
