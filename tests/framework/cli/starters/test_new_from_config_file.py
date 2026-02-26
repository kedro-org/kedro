"""Tests for project creation through config.yml file."""

from __future__ import annotations

from pathlib import Path

import pytest
from click.testing import CliRunner

from kedro.framework.cli.starters import _convert_tool_short_names_to_numbers
from tests.framework.cli.starters.conftest import (
    _assert_requirements_ok,
    _assert_template_ok,
    _default_config,
    _write_yaml,
)


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileValid:
    """Test `kedro new` with config file provided."""

    def test_required_keys_only(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config()
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_required_keys(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config(
            project_name="Project X",
            repo_name="projectx",
            python_package="proj_x",
        )
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_kedro_version(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config(kedro_version="my_version")
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_custom_output_dir(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config(output_dir="my_output_dir")
        _write_yaml(Path("config.yml"), config)
        Path("my_output_dir").mkdir()
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)

    def test_extra_keys_allowed(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config(extra_key="my_extra_key")
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(
            result, **{k: v for k, v in config.items() if k != "extra_key"}
        )

    def test_no_prompts(self, fake_kedro_cli, template_in_cwd):
        config = _default_config()
        del config["tools"]
        del config["example_pipeline"]
        _write_yaml(Path("config.yml"), config)
        (template_in_cwd / "prompts.yml").unlink()
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "template", "--config", "config.yml"],
        )
        _assert_template_ok(result, **config)

    def test_empty_prompts(self, fake_kedro_cli, template_in_cwd):
        config = _default_config()
        del config["tools"]
        del config["example_pipeline"]
        _write_yaml(Path("config.yml"), config)
        _write_yaml(template_in_cwd / "prompts.yml", {})
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "template", "--config", "config.yml"],
        )
        _assert_template_ok(result, **config)

    def test_config_with_no_tools_example(self, fake_kedro_cli):
        """Test project created from config."""
        config = _default_config()
        del config["tools"]
        del config["example_pipeline"]
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )
        _assert_template_ok(result, **config)


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNewFromConfigFileInvalid:
    def test_output_dir_does_not_exist(self, fake_kedro_cli):
        """Check the error if the output directory is invalid."""
        config = _default_config(output_dir="does_not_exist")
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(fake_kedro_cli, ["new", "-v", "-c", "config.yml"])
        assert result.exit_code != 0
        assert "is not a valid output directory." in result.output

    def test_config_missing_key(self, fake_kedro_cli):
        """Check the error if keys are missing from config file."""
        config = _default_config()
        del config["project_name"]
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
        config = _default_config(project_name="My $Project!")
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
        config = _default_config(project_name="P")
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
        config = _default_config(
            tools=tools,
            project_name="New Kedro Project",
            example_pipeline=example_pipeline,
            repo_name="new-kedro-project",
            python_package="new_kedro_project",
        )
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        tools_normalized = _convert_tool_short_names_to_numbers(selected_tools=tools)
        tools_str = ",".join(tools_normalized) if tools_normalized else "none"

        _assert_template_ok(result, tools=tools_str, example_pipeline=example_pipeline)
        _assert_requirements_ok(result, tools=tools_str, repo_name="new-kedro-project")
        if tools_str != "none":
            assert "You have selected the following project tools:" in result.output
        else:
            assert "You have selected no project tools" in result.output
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            not in result.output
        )

    @pytest.mark.parametrize(
        "bad_input",
        ["viz"],
    )
    def test_viz_tool(self, fake_kedro_cli, bad_input):
        """Test project created from config with 'viz' tool."""
        config = _default_config(tools=bad_input)
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "Please select from the available tools: lint, test, log, docs, data, pyspark, all, none. Kedro Viz is automatically included in the project. Please remove 'viz' from your tool selection."
            in result.output
        )

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "0,3,5", "1,3,9", "llint", "tes", "test, lin"],
    )
    def test_invalid_tools(self, fake_kedro_cli, bad_input):
        """Test project created from config."""
        config = _default_config(tools=bad_input)
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "Please select from the available tools: lint, test, log, docs, data, pyspark, all, none"
            in result.output
        )

    def test_invalid_tools_with_starter(self, fake_kedro_cli, template_in_cwd):
        """Test project created from config with tools and example used with --starter"""
        config = _default_config(tools="all")
        _write_yaml(Path("config.yml"), config)
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
        config = _default_config(tools=input)
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            "Tools options 'all' and 'none' cannot be used with other options"
            in result.output
        )

    @pytest.mark.parametrize("example_pipeline", ["y", "n", "N", "YEs", "   yEs   "])
    def test_valid_example(self, fake_kedro_cli, example_pipeline):
        """Test project created from config."""
        config = _default_config(
            project_name="New Kedro Project",
            example_pipeline=example_pipeline,
            repo_name="new-kedro-project",
            python_package="new_kedro_project",
        )
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        _assert_template_ok(result, **config)

    @pytest.mark.parametrize(
        "bad_input",
        ["bad input", "Not", "ye", "True", "t"],
    )
    def test_invalid_example(self, fake_kedro_cli, bad_input):
        """Test project created from config."""
        config = _default_config(example_pipeline=bad_input)
        _write_yaml(Path("config.yml"), config)
        result = CliRunner().invoke(
            fake_kedro_cli, ["new", "-v", "--config", "config.yml"]
        )

        assert result.exit_code != 0
        assert (
            f"'{bad_input}' is an invalid value for example pipeline." in result.output
        )
        assert (
            "It must contain only y, n, YES, or NO (case insensitive).\n"
            in result.output
        )
