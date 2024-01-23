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
            ["new", "--starter", "spaceflights-pandas", "--directory", "some-dir"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert "Cannot use the --directory flag with a --starter alias" in result.output

    def test_starter_flag_with_tools_flag(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--tools", "all", "--starter", "spaceflights-pandas"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --starter flag with the --example and/or --tools flag."
            in result.output
        )

    def test_starter_flag_with_example_flag(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--starter", "spaceflights-pandas", "--example", "no"],
            input=_make_cli_prompt_input(),
        )
        assert result.exit_code != 0
        assert (
            "Cannot use the --starter flag with the --example and/or --tools flag."
            in result.output
        )


@pytest.mark.usefixtures("chdir_to_tmp", "patch_cookiecutter_args")
class TestToolsAndExampleFromCLI:
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
    def test_valid_tools_flag(self, fake_kedro_cli, tools, example_pipeline):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--tools", tools, "--example", example_pipeline],
            input=_make_cli_prompt_input_without_tools(),
        )

        tools = _convert_tool_short_names_to_numbers(selected_tools=tools)
        tools = ",".join(tools) if tools != [] else "none"

        _assert_template_ok(result, tools=tools, example_pipeline=example_pipeline)
        _assert_requirements_ok(result, tools=tools, repo_name="new-kedro-project")
        if tools not in ("none", "NONE"):
            assert "You have selected the following project tools:" in result.output
        else:
            assert "You have selected no project tools" in result.output
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            in result.output
        )
        _clean_up_project(Path("./new-kedro-project"))

    def test_invalid_tools_flag(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--tools", "bad_input"],
            input=_make_cli_prompt_input_without_tools(),
        )

        assert result.exit_code != 0
        assert (
            "Please select from the available tools: lint, test, log, docs, data, pyspark, viz, all, none"
            in result.output
        )

    @pytest.mark.parametrize(
        "tools",
        ["lint,all", "test,none", "all,none"],
    )
    def test_invalid_tools_flag_combination(self, fake_kedro_cli, tools):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--tools", tools],
            input=_make_cli_prompt_input_without_tools(),
        )

        assert result.exit_code != 0
        assert (
            "Tools options 'all' and 'none' cannot be used with other options"
            in result.output
        )

    def test_flags_skip_interactive_flow(self, fake_kedro_cli):
        result = CliRunner().invoke(
            fake_kedro_cli,
            [
                "new",
                "--name",
                "New Kedro Project",
                "--tools",
                "none",
                "--example",
                "no",
            ],
        )

        assert result.exit_code == 0
        assert (
            "To skip the interactive flow you can run `kedro new` with\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>"
            not in result.output
        )
        _clean_up_project(Path("./new-kedro-project"))


@pytest.mark.usefixtures("chdir_to_tmp")
class TestNameFromCLI:
    @pytest.mark.parametrize(
        "name",
        [
            "readable_name",
            "Readable Name",
            "Readable-name",
            "readable_name_12233",
            "123ReadableName",
        ],
    )
    def test_valid_names(self, fake_kedro_cli, name):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--name", name],
            input=_make_cli_prompt_input_without_name(),
        )

        repo_name = name.lower().replace(" ", "_").replace("-", "_")
        assert result.exit_code == 0
        _assert_name_ok(result, project_name=name)
        _clean_up_project(Path("./" + repo_name))

    @pytest.mark.parametrize(
        "name",
        ["bad_name$%!", "Bad.Name", ""],
    )
    def test_invalid_names(self, fake_kedro_cli, name):
        result = CliRunner().invoke(
            fake_kedro_cli,
            ["new", "--name", name],
            input=_make_cli_prompt_input_without_name(),
        )

        assert result.exit_code != 0
        assert (
            "is an invalid value for project name. It must contain only alphanumeric symbols, spaces, underscores and hyphens and be at least 2 characters long"
            in result.output
        )
