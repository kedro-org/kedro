"""kedro is a CLI for managing Kedro projects.

This module implements commands available from the kedro CLI for creating
projects.
"""

from __future__ import annotations

import os
import re
import shutil
import stat
import sys
import tempfile
import warnings
from itertools import groupby
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

import click
import yaml
from attrs import define, field

import kedro
from kedro import __version__ as version
from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    KedroCliError,
    _clean_pycache,
    _get_entry_points,
    _safe_load_entry_point,
    command_with_verbosity,
)

if TYPE_CHECKING:
    from collections import OrderedDict

    from importlib_metadata import EntryPoints

TOOLS_ARG_HELP = """
Select which tools you'd like to include. By default, none are included.\n

Tools\n
1) Linting: Provides a basic linting setup with Ruff\n
2) Testing: Provides basic testing setup with pytest\n
3) Custom Logging: Provides more logging options\n
4) Documentation: Basic documentation setup with Sphinx\n
5) Data Structure: Provides a directory structure for storing data\n
6) PySpark: Provides set up configuration for working with PySpark\n

Example usage:\n
kedro new --tools=lint,test,log,docs,data,pyspark (or any subset of these options)\n
kedro new --tools=all\n
kedro new --tools=none

For more information on using tools, see https://docs.kedro.org/en/stable/starters/new_project_tools.html
"""
CONFIG_ARG_HELP = """Non-interactive mode, using a configuration yaml file. This file
must supply  the keys required by the template's prompts.yml. When not using a starter,
these are `project_name`, `repo_name` and `python_package`."""
CHECKOUT_ARG_HELP = (
    "An optional tag, branch or commit to checkout in the starter repository."
)
DIRECTORY_ARG_HELP = (
    "An optional directory inside the repository where the starter resides."
)
NAME_ARG_HELP = "The name of your new Kedro project."
STARTER_ARG_HELP = """Specify the starter template to use when creating the project.
This can be the path to a local directory, a URL to a remote VCS repository supported
by `cookiecutter` or one of the aliases listed in ``kedro starter list``.
"""
EXAMPLE_ARG_HELP = "Enter y to enable, n to disable the example pipeline."

TELEMETRY_ARG_HELP = """Allow or not allow Kedro to collect usage analytics.
We cannot see nor store information contained into a Kedro project. Opt in with "yes"
and out with "no".
"""


@define(order=True)
class KedroStarterSpec:
    """Specification of custom kedro starter template
    Args:
        alias: alias of the starter which shows up on `kedro starter list` and is used
        by the starter argument of `kedro new`
        template_path: path to a directory or a URL to a remote VCS repository supported
        by `cookiecutter`
        directory: optional directory inside the repository where the starter resides.
        origin: reserved field used by kedro internally to determine where the starter
        comes from, users do not need to provide this field.
    """

    alias: str
    template_path: str
    directory: str | None = None
    origin: str | None = field(init=False)


KEDRO_PATH = Path(kedro.__file__).parent
TEMPLATE_PATH = KEDRO_PATH / "templates" / "project"
_STARTERS_REPO = "git+https://github.com/kedro-org/kedro-starters.git"


_OFFICIAL_STARTER_SPECS = [
    KedroStarterSpec("astro-airflow-iris", _STARTERS_REPO, "astro-airflow-iris"),
    KedroStarterSpec("spaceflights-pandas", _STARTERS_REPO, "spaceflights-pandas"),
    KedroStarterSpec("spaceflights-pyspark", _STARTERS_REPO, "spaceflights-pyspark"),
    KedroStarterSpec("databricks-iris", _STARTERS_REPO, "databricks-iris"),
]
# Set the origin for official starters
for starter_spec in _OFFICIAL_STARTER_SPECS:
    starter_spec.origin = "kedro"

_OFFICIAL_STARTER_SPECS_DICT = {spec.alias: spec for spec in _OFFICIAL_STARTER_SPECS}

TOOLS_SHORTNAME_TO_NUMBER = {
    "lint": "1",
    "test": "2",
    "tests": "2",
    "log": "3",
    "logs": "3",
    "docs": "4",
    "doc": "4",
    "data": "5",
    "pyspark": "6",
}

NUMBER_TO_TOOLS_NAME = {
    "1": "Linting",
    "2": "Testing",
    "3": "Custom Logging",
    "4": "Documentation",
    "5": "Data Structure",
    "6": "PySpark",
}


def _validate_flag_inputs(flag_inputs: dict[str, Any]) -> None:
    if flag_inputs.get("checkout") and not flag_inputs.get("starter"):
        raise KedroCliError("Cannot use the --checkout flag without a --starter value.")

    if flag_inputs.get("directory") and not flag_inputs.get("starter"):
        raise KedroCliError(
            "Cannot use the --directory flag without a --starter value."
        )

    if (flag_inputs.get("tools") or flag_inputs.get("example")) and flag_inputs.get(
        "starter"
    ):
        raise KedroCliError(
            "Cannot use the --starter flag with the --example and/or --tools flag."
        )


def _validate_input_with_regex_pattern(pattern_name: str, input: str) -> None:
    VALIDATION_PATTERNS = {
        "yes_no": {
            "regex": r"(?i)^\s*(y|yes|n|no)\s*$",
            "error_message": f"'{input}' is an invalid value for example pipeline. It must contain only y, n, YES, or NO (case insensitive).",
        },
        "project_name": {
            "regex": r"^[\w -]{2,}$",
            "error_message": f"'{input}' is an invalid value for project name. It must contain only alphanumeric symbols, spaces, underscores and hyphens and be at least 2 characters long",
        },
        "tools": {
            "regex": r"""^(
                all|none|                        # A: "all" or "none" or
                (\ *\d+                          # B: any number of spaces followed by one or more digits
                (\ *-\ *\d+)?                    # C: zero or one instances of: a hyphen followed by one or more digits, spaces allowed
                (\ *,\ *\d+(\ *-\ *\d+)?)*       # D: any number of instances of: a comma followed by B and C, spaces allowed
                \ *)?)                           # E: zero or one instances of (B,C,D) as empty strings are also permissible
                $""",
            "error_message": f"'{input}' is an invalid value for project tools. Please select valid options for tools using comma-separated values, ranges, or 'all/none'.",
        },
    }

    if not re.match(VALIDATION_PATTERNS[pattern_name]["regex"], input, flags=re.X):
        click.secho(
            VALIDATION_PATTERNS[pattern_name]["error_message"],
            fg="red",
            err=True,
        )
        sys.exit(1)


def _parse_yes_no_to_bool(value: str) -> Any:
    return value.strip().lower() in ["y", "yes"] if value is not None else None


def _validate_selected_tools(selected_tools: str | None) -> None:
    valid_tools = [*list(TOOLS_SHORTNAME_TO_NUMBER), "all", "none"]

    if selected_tools is not None:
        tools = re.sub(r"\s", "", selected_tools).split(",")
        for tool in tools:
            if tool not in valid_tools:
                message = "Please select from the available tools: lint, test, log, docs, data, pyspark, all, none."
                if tool == "viz":
                    message += " Kedro Viz is automatically included in the project. Please remove 'viz' from your tool selection."
                click.secho(
                    message,
                    fg="red",
                    err=True,
                )
                sys.exit(1)
        if ("none" in tools or "all" in tools) and len(tools) > 1:
            click.secho(
                "Tools options 'all' and 'none' cannot be used with other options",
                fg="red",
                err=True,
            )
            sys.exit(1)


def _print_selection_and_prompt_info(
    selected_tools: str, example_pipeline: str, interactive: bool
) -> None:
    # Confirm tools selection
    if selected_tools == "['None']":
        click.secho(
            "You have selected no project tools",
            fg="green",
        )
    else:
        click.secho(
            f"You have selected the following project tools: {selected_tools}",
            fg="green",
        )

    # Confirm example selection
    if example_pipeline == "True":
        click.secho(
            "It has been created with an example pipeline.",
            fg="green",
        )
    else:
        warnings.warn(
            "Your project does not contain any pipelines with nodes. "
            "Please ensure that at least one pipeline has been defined before "
            "executing 'kedro run'.",
            UserWarning,
        )

    # Give hint for skipping interactive flow
    if interactive:
        click.secho(
            "\nTo skip the interactive flow you can run `kedro new` with"
            "\nkedro new --name=<your-project-name> --tools=<your-project-tools> --example=<yes/no>",
            fg="green",
        )


@click.group(context_settings=CONTEXT_SETTINGS, name="kedro")
def create_cli() -> None:  # pragma: no cover
    pass


@create_cli.group()
def starter() -> None:
    """Commands for working with project starters."""


@command_with_verbosity(create_cli, short_help="Create a new kedro project.")
@click.option(
    "--config",
    "-c",
    "config_path",
    type=click.Path(exists=True),
    help=CONFIG_ARG_HELP,
)
@click.option("--starter", "-s", "starter_alias", help=STARTER_ARG_HELP)
@click.option("--checkout", help=CHECKOUT_ARG_HELP)
@click.option("--directory", help=DIRECTORY_ARG_HELP)
@click.option(
    "--name",
    "-n",
    "project_name",
    help=NAME_ARG_HELP,
)
@click.option(
    "--tools",
    "-t",
    "selected_tools",
    help=TOOLS_ARG_HELP,
)
@click.option(
    "--example",
    "-e",
    "example_pipeline",
    help=EXAMPLE_ARG_HELP,
)
@click.option(
    "--telemetry",
    "-tc",
    "telemetry_consent",
    help=TELEMETRY_ARG_HELP,
    type=click.Choice(["yes", "no", "y", "n"], case_sensitive=False),
)
def new(  # noqa: PLR0913
    config_path: str,
    starter_alias: str,
    selected_tools: str,
    project_name: str,
    checkout: str,
    directory: str,
    example_pipeline: str,
    telemetry_consent: str,
    **kwargs: Any,
) -> None:
    """Create a new kedro project."""
    flag_inputs = {
        "config": config_path,
        "starter": starter_alias,
        "tools": selected_tools,
        "name": project_name,
        "checkout": checkout,
        "directory": directory,
        "example": example_pipeline,
        "telemetry_consent": telemetry_consent,
    }

    _validate_flag_inputs(flag_inputs)
    starters_dict = _get_starters_dict()

    if starter_alias in starters_dict:
        if directory:
            raise KedroCliError(
                "Cannot use the --directory flag with a --starter alias."
            )
        spec = starters_dict[starter_alias]
        template_path = spec.template_path
        # "directory" is an optional key for starters from plugins, so if the key is
        # not present we will use "None".
        directory = spec.directory  # type: ignore[assignment]
        checkout = _select_checkout_branch_for_cookiecutter(checkout)
    elif starter_alias is not None:
        template_path = starter_alias
    else:
        template_path = str(TEMPLATE_PATH)

    # Format user input where necessary
    if selected_tools is not None:
        selected_tools = selected_tools.lower()

    # Get prompts.yml to find what information the user needs to supply as config.
    tmpdir = tempfile.mkdtemp()
    cookiecutter_dir = _get_cookiecutter_dir(template_path, checkout, directory, tmpdir)
    prompts_required = _get_prompts_required_and_clear_from_CLI_provided(
        cookiecutter_dir, selected_tools, project_name, example_pipeline
    )

    # We only need to make cookiecutter_context if interactive prompts are needed.
    cookiecutter_context = None

    if not config_path:
        cookiecutter_context = _make_cookiecutter_context_for_prompts(cookiecutter_dir)

    # Cleanup the tmpdir after it's no longer required.
    # Ideally we would want to be able to use tempfile.TemporaryDirectory() context manager
    # but it causes an issue with readonly files on windows
    # see: https://bugs.python.org/issue26660.
    # So on error, we will attempt to clear the readonly bits and re-attempt the cleanup
    shutil.rmtree(tmpdir, onerror=_remove_readonly)  # type: ignore[arg-type]

    # Obtain config, either from a file or from interactive user prompts.

    extra_context = _get_extra_context(
        prompts_required=prompts_required,
        config_path=config_path,
        cookiecutter_context=cookiecutter_context,
        selected_tools=selected_tools,
        project_name=project_name,
        example_pipeline=example_pipeline,
        starter_alias=starter_alias,
    )

    cookiecutter_args, project_template = _make_cookiecutter_args_and_fetch_template(
        config=extra_context,
        checkout=checkout,
        directory=directory,
        template_path=template_path,
    )

    if telemetry_consent is not None:
        telemetry_consent = (
            "true" if _parse_yes_no_to_bool(telemetry_consent) else "false"
        )

    _create_project(project_template, cookiecutter_args, telemetry_consent)

    # If not a starter, print tools and example selection
    if not starter_alias:
        # If interactive flow used, print hint
        interactive_flow = prompts_required and not config_path
        _print_selection_and_prompt_info(
            extra_context["tools"],
            extra_context["example_pipeline"],
            interactive_flow,
        )


@starter.command("list")
def list_starters() -> None:
    """List all official project starters available."""
    starters_dict = _get_starters_dict()

    # Group all specs by origin as nested dict and sort it.
    sorted_starters_dict: dict[str, dict[str, KedroStarterSpec]] = {
        origin: dict(sorted(starters_dict_by_origin))
        for origin, starters_dict_by_origin in groupby(
            starters_dict.items(), lambda item: item[1].origin
        )
    }

    # ensure kedro starters are listed first
    sorted_starters_dict = dict(
        sorted(sorted_starters_dict.items(), key=lambda x: x == "kedro")  # type: ignore[comparison-overlap]
    )

    for origin, starters_spec in sorted_starters_dict.items():
        click.secho(f"\nStarters from {origin}\n", fg="yellow")
        click.echo(
            yaml.safe_dump(_starter_spec_to_dict(starters_spec), sort_keys=False)
        )


def _get_cookiecutter_dir(
    template_path: str, checkout: str, directory: str, tmpdir: str
) -> Path:
    """Gives a path to the cookiecutter directory. If template_path is a repo then
    clones it to ``tmpdir``; if template_path is a file path then directly uses that
    path without copying anything.
    """
    from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound
    from cookiecutter.repository import determine_repo_dir  # for performance reasons

    try:
        cookiecutter_dir, _ = determine_repo_dir(
            template=template_path,
            abbreviations={},
            clone_to_dir=Path(tmpdir).resolve(),
            checkout=checkout,
            no_input=True,
            directory=directory,
        )
    except (RepositoryNotFound, RepositoryCloneFailed) as exc:
        error_message = f"Kedro project template not found at {template_path}."

        if checkout:
            error_message += (
                f" Specified tag {checkout}. The following tags are available: "
                + ", ".join(_get_available_tags(template_path))
            )
        official_starters = sorted(_OFFICIAL_STARTER_SPECS_DICT)
        raise KedroCliError(
            f"{error_message}. The aliases for the official Kedro starters are: \n"
            f"{yaml.safe_dump(official_starters, sort_keys=False)}"
        ) from exc

    return Path(cookiecutter_dir)


def _get_prompts_required_and_clear_from_CLI_provided(
    cookiecutter_dir: Path,
    selected_tools: str,
    project_name: str,
    example_pipeline: str,
) -> Any:
    """Finds the information a user must supply according to prompts.yml,
    and clear it from what has already been provided via the CLI(validate it before)"""
    prompts_yml = cookiecutter_dir / "prompts.yml"
    if not prompts_yml.is_file():
        return {}

    try:
        with prompts_yml.open("r") as prompts_file:
            prompts_required = yaml.safe_load(prompts_file)
    except Exception as exc:
        raise KedroCliError(
            "Failed to generate project: could not load prompts.yml."
        ) from exc

    if selected_tools is not None:
        _validate_selected_tools(selected_tools)
        del prompts_required["tools"]

    if project_name is not None:
        _validate_input_with_regex_pattern("project_name", project_name)
        del prompts_required["project_name"]

    if example_pipeline is not None:
        _validate_input_with_regex_pattern("yes_no", example_pipeline)
        del prompts_required["example_pipeline"]

    return prompts_required


def _get_available_tags(template_path: str) -> list:
    # Not at top level so that kedro CLI works without a working git executable.
    import git

    try:
        tags = git.cmd.Git().ls_remote("--tags", template_path.replace("git+", ""))

        unique_tags = {
            tag.split("/")[-1].replace("^{}", "") for tag in tags.split("\n")
        }
        # Remove git ref "^{}" and duplicates. For example,
        # tags: ['/tags/version', '/tags/version^{}']
        # unique_tags: {'version'}

    except git.GitCommandError:  # pragma: no cover
        return []
    return sorted(unique_tags)


def _get_starters_dict() -> dict[str, KedroStarterSpec]:
    """This function lists all the starter aliases declared in
    the core repo and in plugins entry points.

    For example, the output for official kedro starters looks like:
    {"astro-airflow-iris":
        KedroStarterSpec(
            name="astro-airflow-iris",
            template_path="git+https://github.com/kedro-org/kedro-starters.git",
            directory="astro-airflow-iris",
            origin="kedro"
        ),
    }
    """
    starter_specs = _OFFICIAL_STARTER_SPECS_DICT

    for starter_entry_point in _get_entry_points(name="starters"):
        origin = starter_entry_point.module.split(".")[0]
        specs: EntryPoints | list = _safe_load_entry_point(starter_entry_point) or []
        for spec in specs:
            if not isinstance(spec, KedroStarterSpec):
                click.secho(
                    f"The starter configuration loaded from module {origin}"
                    f"should be a 'KedroStarterSpec', got '{type(spec)}' instead",
                    fg="red",
                )
            elif spec.alias in starter_specs:
                click.secho(
                    f"Starter alias `{spec.alias}` from `{origin}` "
                    f"has been ignored as it is already defined by"
                    f"`{starter_specs[spec.alias].origin}`",
                    fg="red",
                )
            else:
                spec.origin = origin
                starter_specs[spec.alias] = spec
    return starter_specs


def _get_extra_context(  # noqa: PLR0913
    prompts_required: dict,
    config_path: str,
    cookiecutter_context: OrderedDict | None,
    selected_tools: str | None,
    project_name: str | None,
    example_pipeline: str | None,
    starter_alias: str | None,
) -> dict[str, str]:
    """Generates a config dictionary that will be passed to cookiecutter as `extra_context`, based
    on CLI flags, user prompts, configuration file or Default values.
    It is crucial to return a dictionary with string values, otherwise, there will be issues with Cookiecutter.

    Args:
        prompts_required: a dictionary of all the prompts that will be shown to
            the user on project creation.
        config_path: a string containing the value for the --config flag, or
            None in case the flag wasn't used.
        cookiecutter_context: the context for Cookiecutter templates.
        selected_tools: a string containing the value for the --tools flag,
            or None in case the flag wasn't used.
        project_name: a string containing the value for the --name flag, or
            None in case the flag wasn't used.
        example_pipeline: a string containing the value for the --example flag,
            or None in case the flag wasn't used
        starter_alias: a string containing the value for the --starter flag, or
            None in case the flag wasn't used

    Returns:
        Config dictionary, passed the necessary processing, with default values if needed.
    """
    if config_path:
        extra_context = _fetch_validate_parse_config_from_file(
            config_path, prompts_required, starter_alias
        )
    else:
        extra_context = _fetch_validate_parse_config_from_user_prompts(
            prompts_required, cookiecutter_context
        )

    # Update extra_context, if CLI inputs are available
    if selected_tools is not None:
        tools_numbers = _convert_tool_short_names_to_numbers(selected_tools)
        extra_context["tools"] = _convert_tool_numbers_to_readable_names(tools_numbers)
    if project_name is not None:
        extra_context["project_name"] = project_name
    if example_pipeline is not None:
        extra_context["example_pipeline"] = str(_parse_yes_no_to_bool(example_pipeline))

    # set defaults for required fields, will be used mostly for starters
    extra_context.setdefault("kedro_version", version)
    extra_context.setdefault("tools", str(["None"]))
    extra_context.setdefault("example_pipeline", "False")

    return extra_context


def _convert_tool_short_names_to_numbers(selected_tools: str) -> list:
    """Prepares tools selection from the CLI or config input to the correct format
    to be put in the project configuration, if it exists.
    Replaces tool strings with the corresponding prompt number.

    Args:
        selected_tools: a string containing the value for the --tools flag or config file,
            or None in case none were provided, i.e. lint,docs.

    Returns:
        String with the numbers corresponding to the desired tools, or
        None in case the --tools flag was not used.
    """
    if selected_tools.lower() == "none":
        return []
    if selected_tools.lower() == "all":
        return list(NUMBER_TO_TOOLS_NAME.keys())

    tools = []
    for tool in selected_tools.lower().split(","):
        tool_short_name = tool.strip()
        if tool_short_name in TOOLS_SHORTNAME_TO_NUMBER:
            tools.append(TOOLS_SHORTNAME_TO_NUMBER[tool_short_name])

    # Remove duplicates if any
    tools = sorted(list(set(tools)))

    return tools


def _convert_tool_numbers_to_readable_names(tools_numbers: list) -> str:
    """Transform the list of tool numbers into a list of readable names, using 'None' for empty lists.
    Then, convert the result into a string format to prevent issues with Cookiecutter.
    """
    tools_names = [NUMBER_TO_TOOLS_NAME[tool] for tool in tools_numbers]
    if tools_names == []:
        tools_names = ["None"]
    return str(tools_names)


def _fetch_validate_parse_config_from_file(
    config_path: str, prompts_required: dict, starter_alias: str | None
) -> dict[str, str]:
    """Obtains configuration for a new kedro project non-interactively from a file.
    Validates that:
    1. All keys specified in prompts_required are retrieved from the configuration.
    2. The options 'tools' and 'example_pipeline' are not used in the configuration when any starter option is selected.
    3. Variables sourced from the configuration file adhere to the expected format.

    Parse tools from short names to list of numbers

    Args:
        config_path: The path of the config.yml which should contain the data required
            by ``prompts.yml``.

    Returns:
        Configuration for starting a new project. This is passed as ``extra_context``
            to cookiecutter and will overwrite the cookiecutter.json defaults.

    Raises:
        KedroCliError: If the file cannot be parsed.

    """
    try:
        with open(config_path, encoding="utf-8") as config_file:
            config: dict[str, str] = yaml.safe_load(config_file)

        if KedroCliError.VERBOSE_ERROR:
            click.echo(config_path + ":")
            click.echo(yaml.dump(config, default_flow_style=False))
    except Exception as exc:
        raise KedroCliError(
            f"Failed to generate project: could not load config at {config_path}."
        ) from exc

    if starter_alias and ("tools" in config or "example_pipeline" in config):
        raise KedroCliError(
            "The --starter flag can not be used with `example_pipeline` and/or `tools` keys in the config file."
        )

    _validate_config_file_against_prompts(config, prompts_required)

    _validate_input_with_regex_pattern(
        "project_name", config.get("project_name", "New Kedro Project")
    )

    example_pipeline = config.get("example_pipeline", "no")
    _validate_input_with_regex_pattern("yes_no", example_pipeline)
    config["example_pipeline"] = str(_parse_yes_no_to_bool(example_pipeline))

    tools_short_names = config.get("tools", "none").lower()
    _validate_selected_tools(tools_short_names)
    tools_numbers = _convert_tool_short_names_to_numbers(tools_short_names)
    config["tools"] = _convert_tool_numbers_to_readable_names(tools_numbers)

    return config


def _fetch_validate_parse_config_from_user_prompts(
    prompts: dict[str, Any],
    cookiecutter_context: OrderedDict | None,
) -> dict[str, str]:
    """Interactively obtains information from user prompts.

    Args:
        prompts: Prompts from prompts.yml.
        cookiecutter_context: Cookiecutter context generated from cookiecutter.json.

    Returns:
        Configuration for starting a new project. This is passed as ``extra_context``
            to cookiecutter and will overwrite the cookiecutter.json defaults.
    """
    if not cookiecutter_context:
        raise Exception("No cookiecutter context available.")

    config: dict[str, str] = {}

    for variable_name, prompt_dict in prompts.items():
        prompt = _Prompt(**prompt_dict)

        # render the variable on the command line
        default_value = cookiecutter_context.get(variable_name) or ""

        # read the user's input for the variable
        user_input = click.prompt(
            str(prompt),
            default=default_value,
            show_default=True,
            type=str,
        ).strip()

        if user_input:
            prompt.validate(user_input)
            config[variable_name] = user_input

    if "tools" in config:
        # convert tools input to list of numbers and validate
        tools_numbers = _parse_tools_input(config["tools"])
        _validate_tool_selection(tools_numbers)
        config["tools"] = _convert_tool_numbers_to_readable_names(tools_numbers)
    if "example_pipeline" in config:
        example_pipeline_bool = _parse_yes_no_to_bool(config["example_pipeline"])
        config["example_pipeline"] = str(example_pipeline_bool)

    return config


def _make_cookiecutter_context_for_prompts(cookiecutter_dir: Path) -> OrderedDict:
    from cookiecutter.generate import generate_context

    cookiecutter_context = generate_context(cookiecutter_dir / "cookiecutter.json")
    return cookiecutter_context.get("cookiecutter", {})  # type: ignore[no-any-return]


def _select_checkout_branch_for_cookiecutter(checkout: str | None) -> str:
    if checkout:
        return checkout
    else:
        return version


def _make_cookiecutter_args_and_fetch_template(
    config: dict[str, str],
    checkout: str,
    directory: str,
    template_path: str,
) -> tuple[dict[str, object], str]:
    """Creates a dictionary of arguments to pass to cookiecutter and returns project template path.

    Args:
        config: Configuration for starting a new project. This is passed as
            ``extra_context`` to cookiecutter and will overwrite the cookiecutter.json
            defaults.
        checkout: The tag, branch or commit in the starter repository to checkout.
            Maps directly to cookiecutter's ``checkout`` argument.
        directory: The directory of a specific starter inside a repository containing
            multiple starters. Maps directly to cookiecutter's ``directory`` argument.
            Relevant only when using a starter.
            https://cookiecutter.readthedocs.io/en/1.7.2/advanced/directories.html
        template_path: Starter path or kedro template path

    Returns:
        Arguments to pass to cookiecutter, project template path
    """

    cookiecutter_args = {
        "output_dir": config.get("output_dir", str(Path.cwd().resolve())),
        "no_input": True,
        "extra_context": config,
    }

    if directory:
        cookiecutter_args["directory"] = directory
    cookiecutter_args["checkout"] = checkout

    tools = config["tools"]
    example_pipeline = config["example_pipeline"]
    starter_path = "git+https://github.com/kedro-org/kedro-starters.git"

    if "PySpark" in tools:
        # Use the spaceflights-pyspark starter if only PySpark is chosen.
        cookiecutter_args["directory"] = "spaceflights-pyspark"
        cookiecutter_args["checkout"] = _select_checkout_branch_for_cookiecutter(
            checkout
        )
    elif example_pipeline == "True":
        # Use spaceflights-pandas starter if example was selected, but PySpark wasn't
        cookiecutter_args["directory"] = "spaceflights-pandas"
        cookiecutter_args["checkout"] = _select_checkout_branch_for_cookiecutter(
            checkout
        )
    else:
        # Use the default template path for non PySpark or example options:
        starter_path = template_path

    return cookiecutter_args, starter_path


def _validate_config_file_against_prompts(
    config: dict[str, str], prompts: dict[str, Any]
) -> None:
    """Checks that the configuration file contains all needed variables.

    Args:
        config: The config as a dictionary.
        prompts: Prompts from prompts.yml.

    Raises:
        KedroCliError: If the config file is empty or does not contain all the keys
            required in prompts, or if the output_dir specified does not exist.
    """
    if not config:
        raise KedroCliError("Config file is empty.")
    additional_keys = {"tools": "none", "example_pipeline": "no"}
    missing_keys = set(prompts) - set(config)
    missing_mandatory_keys = missing_keys - set(additional_keys)
    if missing_mandatory_keys:
        click.echo(yaml.dump(config, default_flow_style=False))
        raise KedroCliError(
            f"{', '.join(missing_mandatory_keys)} not found in config file."
        )
    for key, default_value in additional_keys.items():
        if key in missing_keys:
            click.secho(
                f"The `{key}` key not found in the config file, default value '{default_value}' is being used.",
                fg="yellow",
            )

    if "output_dir" in config and not Path(config["output_dir"]).exists():
        raise KedroCliError(
            f"'{config['output_dir']}' is not a valid output directory. "
            "It must be a relative or absolute path to an existing directory."
        )


def _validate_tool_selection(tools: list[str]) -> None:
    # start validating from the end, when user select 1-20, it will generate a message
    # '20' is not a valid selection instead of '8'
    for tool in tools[::-1]:
        if tool not in NUMBER_TO_TOOLS_NAME:
            message = f"'{tool}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."  # nosec
            if tool == "7":
                message += "\nKedro Viz is automatically included in the project. Please remove 7 from your tool selection."
            click.secho(message, fg="red", err=True)
            sys.exit(1)


def _parse_tools_input(tools_str: str | None) -> list[str]:
    """Parse the tools input string.

    Args:
        tools_str: Input string from prompts.yml.

    Returns:
        list: List of selected tools as strings.
    """

    def _validate_range(start: Any, end: Any) -> None:
        if int(start) > int(end):
            message = f"'{start}-{end}' is an invalid range for project tools.\nPlease ensure range values go from smaller to larger."
            click.secho(message, fg="red", err=True)
            sys.exit(1)
        # safeguard to prevent passing of excessively large intervals that could cause freezing:
        if int(end) > len(NUMBER_TO_TOOLS_NAME):
            message = f"'{end}' is not a valid selection.\nPlease select from the available tools: 1, 2, 3, 4, 5, 6."  # nosec
            if end == "7":
                message += "\nKedro Viz is automatically included in the project. Please remove 7 from your tool selection."
            click.secho(message, fg="red", err=True)
            sys.exit(1)

    if not tools_str:
        return []  # pragma: no cover

    tools_str = tools_str.lower()
    if tools_str == "all":
        return list(NUMBER_TO_TOOLS_NAME)
    if tools_str == "none":
        return []

    # Split by comma
    tools_choices = tools_str.replace(" ", "").split(",")
    selected: list[str] = []

    for choice in tools_choices:
        if "-" in choice:
            start, end = choice.split("-")
            _validate_range(start, end)
            selected.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            selected.append(choice.strip())

    return selected


def _create_project(
    template_path: str, cookiecutter_args: dict[str, Any], telemetry_consent: str | None
) -> None:
    """Creates a new kedro project using cookiecutter.

    Args:
        template_path: The path to the cookiecutter template to create the project.
            It could either be a local directory or a remote VCS repository
            supported by cookiecutter. For more details, please see:
            https://cookiecutter.readthedocs.io/en/stable/usage.html#generate-your-project
        cookiecutter_args: Arguments to pass to cookiecutter.

    Raises:
        KedroCliError: If it fails to generate a project.
    """
    from cookiecutter.main import cookiecutter  # for performance reasons

    try:
        result_path = cookiecutter(template=template_path, **cookiecutter_args)

        if telemetry_consent is not None:
            with open(result_path + "/.telemetry", "w") as telemetry_file:
                telemetry_file.write("consent: " + telemetry_consent)
    except Exception as exc:
        raise KedroCliError(
            "Failed to generate project when running cookiecutter."
        ) from exc

    _clean_pycache(Path(result_path))
    extra_context = cookiecutter_args["extra_context"]
    project_name = extra_context.get("project_name", "New Kedro Project")

    # Print success message
    click.secho(
        "\nCongratulations!"
        f"\nYour project '{project_name}' has been created in the directory \n{result_path}\n"
    )


class _Prompt:
    """Represent a single CLI prompt for `kedro new`"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        try:
            self.title = kwargs["title"]
        except KeyError as exc:
            raise KedroCliError(
                "Each prompt must have a title field to be valid."
            ) from exc

        self.text = kwargs.get("text", "")
        self.regexp = kwargs.get("regex_validator", None)
        self.error_message = kwargs.get("error_message", "")

    def __str__(self) -> str:
        # Format the title with optional color
        title = self.title.strip().title()
        title = click.style(title, fg="cyan", bold=True)
        title_line = "=" * len(self.title)
        title_line = click.style(title_line, fg="cyan", bold=True)

        # Format the main text
        text = self.text.strip()

        # Combine everything
        prompt_lines = [title, title_line, text]
        prompt_text = "\n".join(str(line).strip() for line in prompt_lines)
        return f"\n{prompt_text}\n"

    def validate(self, user_input: str) -> None:
        """Validate a given prompt value against the regex validator"""
        if self.regexp and not re.match(self.regexp, user_input):
            message = f"'{user_input}' is an invalid value for {(self.title).lower()}."
            click.secho(message, fg="red", err=True)
            click.secho(self.error_message, fg="red", err=True)
            sys.exit(1)


def _remove_readonly(
    func: Callable, path: Path, excinfo: tuple
) -> None:  # pragma: no cover
    """Remove readonly files on Windows
    See: https://docs.python.org/3/library/shutil.html?highlight=shutil#rmtree-example
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


def _starter_spec_to_dict(
    starter_specs: dict[str, KedroStarterSpec],
) -> dict[str, dict[str, str]]:
    """Convert a dictionary of starters spec to a nicely formatted dictionary"""
    format_dict: dict[str, dict[str, str]] = {}
    for alias, spec in starter_specs.items():
        format_dict[alias] = {}  # Each dictionary represent 1 starter
        format_dict[alias]["template_path"] = spec.template_path
        if spec.directory:
            format_dict[alias]["directory"] = spec.directory
    return format_dict
