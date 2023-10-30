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
from collections import OrderedDict
from itertools import groupby
from pathlib import Path
from typing import Any, Callable

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

KEDRO_PATH = Path(kedro.__file__).parent
TEMPLATE_PATH = KEDRO_PATH / "templates" / "project"
_STARTERS_REPO = "git+https://github.com/kedro-org/kedro-starters.git"


@define(order=True)
class KedroStarterSpec:  # noqa: too-few-public-methods
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


_OFFICIAL_STARTER_SPECS = [
    KedroStarterSpec("astro-airflow-iris", _STARTERS_REPO, "astro-airflow-iris"),
    # The `astro-iris` was renamed to `astro-airflow-iris`, but old (external)
    # documentation and tutorials still refer to `astro-iris`. We create an alias to
    # check if a user has entered old `astro-iris` as the starter name and changes it
    # to `astro-airflow-iris`.
    KedroStarterSpec("astro-iris", _STARTERS_REPO, "astro-airflow-iris"),
    KedroStarterSpec(
        "standalone-datacatalog", _STARTERS_REPO, "standalone-datacatalog"
    ),
    KedroStarterSpec("pandas-iris", _STARTERS_REPO, "pandas-iris"),
    KedroStarterSpec("pyspark", _STARTERS_REPO, "pyspark"),
    KedroStarterSpec("pyspark-iris", _STARTERS_REPO, "pyspark-iris"),
    KedroStarterSpec("spaceflights-pandas", _STARTERS_REPO, "spaceflights-pandas"),
    KedroStarterSpec(
        "spaceflights-pandas-viz", _STARTERS_REPO, "spaceflights-pandas-viz"
    ),
    KedroStarterSpec("spaceflights-pyspark", _STARTERS_REPO, "spaceflights-pyspark"),
    KedroStarterSpec(
        "spaceflights-pyspark-viz", _STARTERS_REPO, "spaceflights-pyspark-viz"
    ),
    KedroStarterSpec("databricks-iris", _STARTERS_REPO, "databricks-iris"),
]
# Set the origin for official starters
for starter_spec in _OFFICIAL_STARTER_SPECS:
    starter_spec.origin = "kedro"
_OFFICIAL_STARTER_SPECS = {spec.alias: spec for spec in _OFFICIAL_STARTER_SPECS}


CONFIG_ARG_HELP = """Non-interactive mode, using a configuration yaml file. This file
must supply  the keys required by the template's prompts.yml. When not using a starter,
these are `project_name`, `repo_name` and `python_package`."""
STARTER_ARG_HELP = """Specify the starter template to use when creating the project.
This can be the path to a local directory, a URL to a remote VCS repository supported
by `cookiecutter` or one of the aliases listed in ``kedro starter list``.
"""
CHECKOUT_ARG_HELP = (
    "An optional tag, branch or commit to checkout in the starter repository."
)
DIRECTORY_ARG_HELP = (
    "An optional directory inside the repository where the starter resides."
)

# TODO; Insert actual link to the documentation (Visit: kedro.org/{insert-documentation} to find out more about these add-ons.).
ADDON_ARG_HELP = """
Select which add-ons you'd like to include. By default, none are included.\n

Add-Ons\n
1) Linting: Provides a basic linting setup with Black and Ruff\n
2) Testing: Provides basic testing setup with pytest\n
3) Custom Logging: Provides more logging options\n
4) Documentation: Basic documentation setup with Sphinx\n
5) Data Structure: Provides a directory structure for storing data\n
6) Pyspark: Provides a basic PySpark set up\n

Example usage:\n
kedro new --addons=lint,test,log,docs,data,pyspark (or any subset of these options)\n
kedro new --addons=all\n
kedro new --addons=none
"""

ADD_ONS_DICT = {
    "1": "Linting",
    "2": "Testing",
    "3": "Custom Logging",
    "4": "Documentation",
    "5": "Data Structure",
    "6": "Pyspark",
}

# noqa: unused-argument
def _remove_readonly(func: Callable, path: Path, excinfo: tuple):  # pragma: no cover
    """Remove readonly files on Windows
    See: https://docs.python.org/3/library/shutil.html?highlight=shutil#rmtree-example
    """
    os.chmod(path, stat.S_IWRITE)
    func(path)


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
    "astro-iris":
        KedroStarterSpec(
            name="astro-iris",
            template_path="git+https://github.com/kedro-org/kedro-starters.git",
            directory="astro-airflow-iris",
            origin="kedro"
        ),
    }
    """
    starter_specs = _OFFICIAL_STARTER_SPECS

    for starter_entry_point in _get_entry_points(name="starters"):
        origin = starter_entry_point.module.split(".")[0]
        specs = _safe_load_entry_point(starter_entry_point) or []
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


def _starter_spec_to_dict(
    starter_specs: dict[str, KedroStarterSpec]
) -> dict[str, dict[str, str]]:
    """Convert a dictionary of starters spec to a nicely formatted dictionary"""
    format_dict: dict[str, dict[str, str]] = {}
    for alias, spec in starter_specs.items():
        format_dict[alias] = {}  # Each dictionary represent 1 starter
        format_dict[alias]["template_path"] = spec.template_path
        if spec.directory:
            format_dict[alias]["directory"] = spec.directory
    return format_dict


def _parse_add_ons_input(add_ons_str: str):
    """Parse the add-ons input string.

    Args:
        add_ons_str: Input string from prompts.yml.

    Returns:
        list: List of selected add-ons as strings.
    """

    def _validate_range(start, end):
        if int(start) > int(end):
            message = f"'{start}-{end}' is an invalid range for project add-ons.\nPlease ensure range values go from smaller to larger."
            click.secho(message, fg="red", err=True)
            sys.exit(1)

    def _validate_selection(add_ons: list[str]):
        for add_on in add_ons:
            if int(add_on) < 1 or int(add_on) > len(ADD_ONS_DICT):
                message = f"'{add_on}' is not a valid selection.\nPlease select from the available add-ons: 1, 2, 3, 4, 5, 6."  # nosec
                click.secho(message, fg="red", err=True)
                sys.exit(1)

    if add_ons_str == "all":
        return list(ADD_ONS_DICT)
    if add_ons_str == "none":
        return []
    # Guard clause if add_ons_str is None, which can happen if prompts.yml is removed
    if not add_ons_str:
        return []  # pragma: no cover

    # Split by comma
    add_ons_choices = add_ons_str.split(",")
    selected: list[str] = []

    for choice in add_ons_choices:
        if "-" in choice:
            start, end = choice.split("-")
            _validate_range(start, end)
            selected.extend(str(i) for i in range(int(start), int(end) + 1))
        else:
            selected.append(choice.strip())

    _validate_selection(selected)
    return selected


# noqa: missing-function-docstring
@click.group(context_settings=CONTEXT_SETTINGS, name="Kedro")
def create_cli():  # pragma: no cover
    pass


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
@click.option("--addons", "-a", "selected_addons", help=ADDON_ARG_HELP)
def new(config_path, starter_alias, selected_addons, checkout, directory, **kwargs):
    """Create a new kedro project."""
    if checkout and not starter_alias:
        raise KedroCliError("Cannot use the --checkout flag without a --starter value.")

    if directory and not starter_alias:
        raise KedroCliError(
            "Cannot use the --directory flag without a --starter value."
        )

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
        directory = spec.directory
        checkout = checkout or version
    elif starter_alias is not None:
        template_path = starter_alias
        checkout = checkout or version
    else:
        template_path = str(TEMPLATE_PATH)

    # Get prompts.yml to find what information the user needs to supply as config.
    tmpdir = tempfile.mkdtemp()
    cookiecutter_dir = _get_cookiecutter_dir(template_path, checkout, directory, tmpdir)
    prompts_required = _get_prompts_required(cookiecutter_dir)

    # Select which prompts will be displayed to the user based on which flags were selected.
    prompts_required = _select_prompts_to_display(prompts_required, selected_addons)

    # We only need to make cookiecutter_context if interactive prompts are needed.
    if not config_path:
        cookiecutter_context = _make_cookiecutter_context_for_prompts(cookiecutter_dir)

    # Cleanup the tmpdir after it's no longer required.
    # Ideally we would want to be able to use tempfile.TemporaryDirectory() context manager
    # but it causes an issue with readonly files on windows
    # see: https://bugs.python.org/issue26660.
    # So on error, we will attempt to clear the readonly bits and re-attempt the cleanup
    shutil.rmtree(tmpdir, onerror=_remove_readonly)

    # Obtain config, either from a file or from interactive user prompts.
    if not prompts_required:
        config = {}
        if config_path:
            config = _fetch_config_from_file(config_path)
            _validate_config_file_inputs(config)

    elif config_path:
        config = _fetch_config_from_file(config_path)
        _validate_config_file_against_prompts(config, prompts_required)
        _validate_config_file_inputs(config)
    else:
        config = _fetch_config_from_user_prompts(prompts_required, cookiecutter_context)

    config = _get_addons_from_cli_input(selected_addons, config)

    cookiecutter_args = _make_cookiecutter_args(config, checkout, directory)

    project_template = fetch_template_based_on_add_ons(template_path, cookiecutter_args)

    _create_project(project_template, cookiecutter_args)


@create_cli.group()
def starter():
    """Commands for working with project starters."""


@starter.command("list")
def list_starters():
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
        sorted(sorted_starters_dict.items(), key=lambda x: x == "kedro")
    )

    for origin, starters_spec in sorted_starters_dict.items():
        click.secho(f"\nStarters from {origin}\n", fg="yellow")
        click.echo(
            yaml.safe_dump(_starter_spec_to_dict(starters_spec), sort_keys=False)
        )


def _get_addons_from_cli_input(
    selected_addons: str, config: dict[str, str]
) -> dict[str, str]:
    """Inserts add-on selection from the CLI input in the project
    configuration, if it exists. Replaces add-on strings with the
    corresponding prompt number.

    Args:
        selected_addons: a string containing the value for the --addons flag,
            or None in case the flag wasn't used.

    Returns:
        Configuration for starting a new project, with the selected add-ons
        from the `--addons` flag.
    """
    string_to_number = {
        "lint": "1",
        "test": "2",
        "log": "3",
        "docs": "4",
        "data": "5",
        "pyspark": "6",
    }

    if selected_addons is not None:
        addons = selected_addons.split(",")
        for i in range(len(addons)):
            addon = addons[i].strip()
            if addon in string_to_number:
                addons[i] = string_to_number[addon]
        config["add_ons"] = ",".join(addons)

    return config


def _select_prompts_to_display(prompts_required: dict, selected_addons: str) -> dict:
    """Selects which prompts an user will receive when creating a new
    Kedro project, based on what information was already made available
    through CLI input.

    Args:
        prompts_required: a dictionary of all the prompts that will be shown to
            the user on project creation.
        selected_addons: a string containing the value for the --addons flag,
            or None in case the flag wasn't used.

    Returns:
        the prompts_required dictionary, with all the redundant information removed.
    """
    valid_addons = ["lint", "test", "log", "docs", "data", "pyspark", "all", "none"]

    if selected_addons is not None:
        addons = re.sub(r"\s", "", selected_addons).split(",")
        for addon in addons:
            if addon not in valid_addons:
                click.secho(
                    "Please select from the available add-ons: lint, test, log, docs, data, pyspark, all, none",
                    fg="red",
                    err=True,
                )
                sys.exit(1)
        if ("none" in addons or "all" in addons) and len(addons) > 1:
            click.secho(
                "Add-on options 'all' and 'none' cannot be used with other options",
                fg="red",
                err=True,
            )
            sys.exit(1)
        del prompts_required["add_ons"]

    return prompts_required


def _fetch_config_from_file(config_path: str) -> dict[str, str]:
    """Obtains configuration for a new kedro project non-interactively from a file.

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
            config = yaml.safe_load(config_file)

        if KedroCliError.VERBOSE_ERROR:
            click.echo(config_path + ":")
            click.echo(yaml.dump(config, default_flow_style=False))
    except Exception as exc:
        raise KedroCliError(
            f"Failed to generate project: could not load config at {config_path}."
        ) from exc

    return config


def _make_cookiecutter_args(
    config: dict[str, str | list[str]],
    checkout: str,
    directory: str,
) -> dict[str, Any]:
    """Creates a dictionary of arguments to pass to cookiecutter.

    Args:
        config: Configuration for starting a new project. This is passed as
            ``extra_context`` to cookiecutter and will overwrite the cookiecutter.json
            defaults.
        checkout: The tag, branch or commit in the starter repository to checkout.
            Maps directly to cookiecutter's ``checkout`` argument. Relevant only when
            using a starter.
        directory: The directory of a specific starter inside a repository containing
            multiple starters. Maps directly to cookiecutter's ``directory`` argument.
            Relevant only when using a starter.
            https://cookiecutter.readthedocs.io/en/1.7.2/advanced/directories.html

    Returns:
        Arguments to pass to cookiecutter.
    """
    config.setdefault("kedro_version", version)

    # Map the selected add on lists to readable name
    add_ons = config.get("add_ons")
    if add_ons:
        config["add_ons"] = [
            ADD_ONS_DICT[add_on] for add_on in _parse_add_ons_input(add_ons)  # type: ignore
        ]
        config["add_ons"] = str(config["add_ons"])

    cookiecutter_args = {
        "output_dir": config.get("output_dir", str(Path.cwd().resolve())),
        "no_input": True,
        "extra_context": config,
    }

    if checkout:
        cookiecutter_args["checkout"] = checkout
    if directory:
        cookiecutter_args["directory"] = directory

    return cookiecutter_args


def fetch_template_based_on_add_ons(template_path, cookiecutter_args: dict[str, Any]):
    extra_context = cookiecutter_args["extra_context"]
    add_ons = extra_context.get("add_ons")
    if add_ons and "Pyspark" in add_ons:
        cookiecutter_args["directory"] = "spaceflights-pyspark"
        pyspark_path = "git+https://github.com/kedro-org/kedro-starters.git"
        return pyspark_path
    return template_path


def _create_project(template_path: str, cookiecutter_args: dict[str, Any]):
    """Creates a new kedro project using cookiecutter.

    Args:
        template_path: The path to the cookiecutter template to create the project.
            It could either be a local directory or a remote VCS repository
            supported by cookiecutter. For more details, please see:
            https://cookiecutter.readthedocs.io/en/latest/usage.html#generate-your-project
        cookiecutter_args: Arguments to pass to cookiecutter.

    Raises:
        KedroCliError: If it fails to generate a project.
    """
    # noqa: import-outside-toplevel
    from cookiecutter.main import cookiecutter  # for performance reasons

    try:
        result_path = cookiecutter(template=template_path, **cookiecutter_args)
    except Exception as exc:
        raise KedroCliError(
            "Failed to generate project when running cookiecutter."
        ) from exc

    _clean_pycache(Path(result_path))
    extra_context = cookiecutter_args["extra_context"]
    project_name = extra_context.get("project_name", "New Kedro Project")
    python_package = extra_context.get(
        "python_package", project_name.lower().replace(" ", "_").replace("-", "_")
    )
    add_ons = extra_context.get("add_ons")

    # Only core template and spaceflights-pyspark have configurable add-ons
    if (
        template_path == str(TEMPLATE_PATH)
        or add_ons is not None
        and "Pyspark" in add_ons
    ):
        if add_ons == "[]":  # TODO: This should be a list
            click.secho("\nYou have selected no add-ons")
        else:
            click.secho(f"\nYou have selected the following add-ons: {add_ons}")

    click.secho(
        f"\nThe project name '{project_name}' has been applied to: "
        f"\n- The project title in {result_path}/README.md "
        f"\n- The folder created for your project in {result_path} "
        f"\n- The project's python package in {result_path}/src/{python_package}"
    )
    click.secho(
        "\nA best-practice setup includes initialising git and creating "
        "a virtual environment before running 'pip install -r requirements.txt' to install "
        "project-specific dependencies. Refer to the Kedro documentation: "
        "https://kedro.readthedocs.io/"
    )
    click.secho(
        f"\nChange directory to the project generated in {result_path} by "
        f"entering 'cd {result_path}'",
        fg="green",
    )


def _get_cookiecutter_dir(
    template_path: str, checkout: str, directory: str, tmpdir: str
) -> Path:
    """Gives a path to the cookiecutter directory. If template_path is a repo then
    clones it to ``tmpdir``; if template_path is a file path then directly uses that
    path without copying anything.
    """
    # noqa: import-outside-toplevel
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
        official_starters = sorted(_OFFICIAL_STARTER_SPECS)
        raise KedroCliError(
            f"{error_message}. The aliases for the official Kedro starters are: \n"
            f"{yaml.safe_dump(official_starters, sort_keys=False)}"
        ) from exc

    return Path(cookiecutter_dir)


def _get_prompts_required(cookiecutter_dir: Path) -> dict[str, Any] | None:
    """Finds the information a user must supply according to prompts.yml."""
    prompts_yml = cookiecutter_dir / "prompts.yml"
    if not prompts_yml.is_file():
        return None

    try:
        with prompts_yml.open("r") as prompts_file:
            return yaml.safe_load(prompts_file)
    except Exception as exc:
        raise KedroCliError(
            "Failed to generate project: could not load prompts.yml."
        ) from exc


def _fetch_config_from_user_prompts(
    prompts: dict[str, Any], cookiecutter_context: OrderedDict
) -> dict[str, str]:
    """Interactively obtains information from user prompts.

    Args:
        prompts: Prompts from prompts.yml.
        cookiecutter_context: Cookiecutter context generated from cookiecutter.json.

    Returns:
        Configuration for starting a new project. This is passed as ``extra_context``
            to cookiecutter and will overwrite the cookiecutter.json defaults.
    """
    # noqa: import-outside-toplevel
    from cookiecutter.environment import StrictEnvironment
    from cookiecutter.prompt import read_user_variable, render_variable

    config: dict[str, str] = {}

    for variable_name, prompt_dict in prompts.items():
        prompt = _Prompt(**prompt_dict)

        # render the variable on the command line
        cookiecutter_variable = render_variable(
            env=StrictEnvironment(context=cookiecutter_context),
            raw=cookiecutter_context.get(variable_name),
            cookiecutter_dict=config,
        )

        # read the user's input for the variable
        user_input = read_user_variable(str(prompt), cookiecutter_variable)
        if user_input:
            prompt.validate(user_input)
            config[variable_name] = user_input
    return config


def _make_cookiecutter_context_for_prompts(cookiecutter_dir: Path):
    # noqa: import-outside-toplevel
    from cookiecutter.generate import generate_context

    cookiecutter_context = generate_context(cookiecutter_dir / "cookiecutter.json")
    return cookiecutter_context.get("cookiecutter", {})


class _Prompt:
    """Represent a single CLI prompt for `kedro new`"""

    def __init__(self, *args, **kwargs) -> None:  # noqa: unused-argument
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
        title = self.title.strip().title()
        title = click.style(title + "\n" + "=" * len(title), bold=True)
        prompt_lines = [title] + [self.text]
        prompt_text = "\n".join(str(line).strip() for line in prompt_lines)
        return f"\n{prompt_text}\n"

    def validate(self, user_input: str) -> None:
        """Validate a given prompt value against the regex validator"""
        if self.regexp and not re.match(self.regexp, user_input):
            message = f"'{user_input}' is an invalid value for {(self.title).lower()}."
            click.secho(message, fg="red", err=True)
            click.secho(self.error_message, fg="red", err=True)
            sys.exit(1)


def _get_available_tags(template_path: str) -> list:
    # Not at top level so that kedro CLI works without a working git executable.
    # noqa: import-outside-toplevel
    import git

    try:
        tags = git.cmd.Git().ls_remote("--tags", template_path.replace("git+", ""))

        unique_tags = {
            tag.split("/")[-1].replace("^{}", "") for tag in tags.split("\n")
        }
        # Remove git ref "^{}" and duplicates. For example,
        # tags: ['/tags/version', '/tags/version^{}']
        # unique_tags: {'version'}

    except git.GitCommandError:
        return []
    return sorted(unique_tags)


def _validate_config_file_against_prompts(
    config: dict[str, str], prompts: dict[str, Any]
):
    """Checks that the configuration file contains all needed variables.

    Args:
        config: The config as a dictionary.
        prompts: Prompts from prompts.yml.

    Raises:
        KedroCliError: If the config file is empty or does not contain all the keys
            required in prompts, or if the output_dir specified does not exist.
    """
    if config is None:
        raise KedroCliError("Config file is empty.")
    missing_keys = set(prompts) - set(config)
    if missing_keys:
        click.echo(yaml.dump(config, default_flow_style=False))
        raise KedroCliError(f"{', '.join(missing_keys)} not found in config file.")

    if "output_dir" in config and not Path(config["output_dir"]).exists():
        raise KedroCliError(
            f"'{config['output_dir']}' is not a valid output directory. "
            "It must be a relative or absolute path to an existing directory."
        )


def _validate_config_file_inputs(config: dict[str, str]):
    """Checks that variables provided through the config file are of the expected format.

    Args:
        config: The config as a dictionary.

    Raises:
        SystemExit: If the provided variables are not properly formatted.
    """
    project_name_reg_ex = r"^[\w -]{2,}$"
    input_project_name = config.get("project_name", "New Kedro Project")
    if not re.match(project_name_reg_ex, input_project_name):
        message = f"'{input_project_name}' is an invalid value for project name. It must contain only alphanumeric symbols, spaces, underscores and hyphens and be at least 2 characters long"
        click.secho(message, fg="red", err=True)
        sys.exit(1)

    add_on_reg_ex = r"^(all|none|(\d(,\d)*|(\d-\d)))$"
    input_add_ons = config.get("add_ons", "none")
    if not re.match(add_on_reg_ex, input_add_ons):
        message = f"'{input_add_ons}' is an invalid value for project add-ons. Please select valid options for add-ons using comma-separated values, ranges, or 'all/none'."
        click.secho(message, fg="red", err=True)
        sys.exit(1)
