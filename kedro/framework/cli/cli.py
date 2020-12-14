# Copyright 2020 QuantumBlack Visual Analytics Limited
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

"""kedro is a CLI for creating Kedro projects.

This module implements commands available from the kedro CLI.
"""
import importlib
import os
import re
import warnings
import webbrowser
from collections import defaultdict
from copy import deepcopy
from pathlib import Path
from typing import Any, Callable, Dict, List

import click
import git
import pkg_resources
import yaml

import kedro.config.default_logger  # noqa
from kedro import __version__ as version
from kedro.framework.cli.utils import (
    CommandCollection,
    KedroCliError,
    _add_src_to_path,
    _clean_pycache,
    _filter_deprecation_warnings,
    command_with_verbosity,
)
from kedro.framework.context.context import load_context
from kedro.framework.startup import _get_project_metadata, _is_project

KEDRO_PATH = Path(kedro.__file__).parent
TEMPLATE_PATH = KEDRO_PATH / "templates" / "project"
CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

LOGO = rf"""
 _            _
| | _____  __| |_ __ ___
| |/ / _ \/ _` | '__/ _ \
|   <  __/ (_| | | | (_) |
|_|\_\___|\__,_|_|  \___/
v{version}
"""

_STARTERS_REPO = "git+https://github.com/quantumblacklabs/kedro-starters.git"
_STARTER_ALIASES = {
    "mini-kedro",
    "pandas-iris",
    "pyspark",
    "pyspark-iris",
    "spaceflights",
}


@click.group(context_settings=CONTEXT_SETTINGS, name="Kedro")
@click.version_option(version, "--version", "-V", help="Show version and exit")
def cli():
    """Kedro is a CLI for creating and using Kedro projects
    For more information, type ``kedro info``.

    When inside a Kedro project (created with `kedro new`) commands from
    the project's `cli.py` file will also be available here.
    """
    pass


ENTRY_POINT_GROUPS = {
    "global": "kedro.global_commands",
    "project": "kedro.project_commands",
    "init": "kedro.init",
    "line_magic": "kedro.line_magic",
}


@cli.command()
def info():
    """Get more information about kedro.
    """
    click.secho(LOGO, fg="green")
    click.echo(
        "kedro allows teams to create analytics\n"
        "projects. It is developed as part of\n"
        "the Kedro initiative at QuantumBlack."
    )

    plugin_versions = {}
    plugin_hooks = defaultdict(set)
    for hook, group in ENTRY_POINT_GROUPS.items():
        for entry_point in pkg_resources.iter_entry_points(group=group):
            module_name = entry_point.module_name.split(".")[0]
            plugin_version = pkg_resources.get_distribution(module_name).version
            plugin_versions[module_name] = plugin_version
            plugin_hooks[module_name].add(hook)

    click.echo()
    if plugin_versions:
        click.echo("Installed plugins:")
        for plugin_name, plugin_version in sorted(plugin_versions.items()):
            hooks = ",".join(sorted(plugin_hooks[plugin_name]))
            click.echo(f"{plugin_name}: {plugin_version} (hooks:{hooks})")
    else:
        click.echo("No plugins installed")


@command_with_verbosity(cli, short_help="Create a new kedro project.")
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    help="Non-interactive mode, using a configuration yaml file.",
)
@click.option(
    "--starter",
    "-s",
    "starter_name",
    help="Specify the starter template to use when creating the project.",
)
@click.option(
    "--checkout", help="A tag, branch or commit to checkout in the starter repository."
)
@click.option(
    "--directory",
    help="An optional directory inside the repository where the starter resides.",
)
def new(
    config, starter_name, checkout, directory, **kwargs
):  # pylint: disable=unused-argument
    """Create a new kedro project, either interactively or from a
    configuration file.

    Create projects according to the Kedro default project template. This
    template is ideal for analytics projects and comes with a data
    architecture, folders for notebooks, configuration, source code, etc.

    \b
    ``kedro new``
    Create a new project interactively.

    \b
    You will have to provide four choices:
    * ``Project Name`` - name of the project, not to be confused with name of
    the project folder.
    * ``Repository Name`` - intended name of your project folder.
    * ``Package Name`` - intended name of your Python package.
    * ``Generate Example Pipeline`` - yes/no to generating an example pipeline
    in your project.

    \b
    ``kedro new --config <config.yml>``
    ``kedro new -c <config.yml>``
    Create a new project from configuration.

    * ``config.yml`` - The configuration YAML must contain at the top level
                    the above parameters (project_name, repo_name,
                    python_package) and output_dir - the
                    parent directory for the new project directory.

    \b
    ``kedro new --starter <starter>``
    Create a new project from a starter template. The starter can be either the path to
    a local directory, a URL to a remote VCS repository supported by `cookiecutter` or
    one of the aliases listed in ``kedro starter list``.

    \b
    ``kedro new --starter <starter> --checkout <checkout>``
    Create a new project from a starter template and a particular tag, branch or commit
    in the starter repository.

    \b
    ``kedro new --starter <starter> --directory <directory>``
    Create a new project from a starter repository and a directory within the location.
    Useful when you have multiple starters in the same repository.
    """
    if checkout and not starter_name:
        raise KedroCliError("Cannot use the --checkout flag without a --starter value.")

    if directory and not starter_name:
        raise KedroCliError(
            "Cannot use the --directory flag without a --starter value."
        )

    if starter_name in _STARTER_ALIASES:
        if directory:
            raise KedroCliError(
                "Cannot use the --directory flag with a --starter alias."
            )
        template_path = _STARTERS_REPO
        directory = starter_name
    elif starter_name is not None:
        template_path = starter_name
    else:
        template_path = TEMPLATE_PATH

    _create_project(
        config_path=config,
        template_path=template_path,
        checkout=checkout,
        directory=directory,
    )


@cli.command(short_help="See the kedro API docs and introductory tutorial.")
def docs():
    """Display the API docs and introductory tutorial in the browser,
    using the packaged HTML doc files."""
    index_path = "file://" + os.path.realpath(
        os.path.join(
            os.path.realpath(__file__), os.pardir, os.pardir, "html", "index.html"
        )
    )
    click.echo("Opening " + index_path)
    webbrowser.open(index_path)


@cli.group()
def starter():
    """Commands for working with project starters."""


@starter.command("list")
def list_starters():
    """List all official project starters available."""
    repo_url = _STARTERS_REPO.replace("git+", "").replace(
        ".git", "/tree/master/{alias}"
    )
    output = [
        {alias: repo_url.format(alias=alias)} for alias in sorted(_STARTER_ALIASES)
    ]
    click.echo(yaml.safe_dump(output))


def _create_project(
    config_path: str,
    template_path: Path = TEMPLATE_PATH,
    checkout: str = None,
    directory: str = None,
):
    """Implementation of the kedro new cli command.

    Args:
        config_path: In non-interactive mode, the path of the config.yml which
            should contain the project_name, output_dir and repo_name.
        template_path: The path to the cookiecutter template to create the project.
            It could either be a local directory or a remote VCS repository
            supported by cookiecutter. For more details, please see:
            https://cookiecutter.readthedocs.io/en/latest/usage.html#generate-your-project
        checkout: The tag, branch or commit in the starter repository to checkout.
            Maps directly to cookiecutter's --checkout argument.
            If the value is not provided, cookiecutter will use the installed Kedro version
            by default.
        directory: The directory of a specific starter inside a repository containing
            multiple starters. Map directly to cookiecutter's --directory argument.
            https://cookiecutter.readthedocs.io/en/1.7.2/advanced/directories.html
    Raises:
        KedroCliError: If it fails to generate a project.
    """
    with _filter_deprecation_warnings():
        # pylint: disable=import-outside-toplevel
        from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound
        from cookiecutter.main import cookiecutter  # for performance reasons

    try:
        if config_path:
            config = _parse_config(config_path)
            config = _check_config_ok(config_path, config)
        else:
            config = _get_config_from_prompts()
        config.setdefault("kedro_version", version)

        checkout = checkout or version
        cookiecutter_args = dict(
            output_dir=config["output_dir"],
            no_input=True,
            extra_context=config,
            checkout=checkout,
        )
        if directory:
            cookiecutter_args["directory"] = directory
        result_path = Path(cookiecutter(str(template_path), **cookiecutter_args))
        _clean_pycache(result_path)
        _print_kedro_new_success_message(result_path)
    except click.exceptions.Abort as exc:  # pragma: no cover
        raise KedroCliError("User interrupt.") from exc
    except RepositoryNotFound as exc:
        raise KedroCliError(
            f"Kedro project template not found at {template_path}"
        ) from exc
    except RepositoryCloneFailed as exc:
        error_message = (
            f"Kedro project template not found at {template_path} with tag {checkout}."
        )
        tags = _get_available_tags(str(template_path).replace("git+", ""))
        if tags:
            error_message += (
                f" The following tags are available: {', '.join(tags.__iter__())}"
            )
        raise KedroCliError(error_message) from exc
    # we don't want the user to see a stack trace on the cli
    except Exception as exc:
        raise KedroCliError("Failed to generate project.") from exc


def _get_available_tags(template_path: str) -> List:
    try:
        tags = git.cmd.Git().ls_remote("--tags", str(template_path)).split("\n")

        unique_tags = {tag.split("/")[-1].replace("^{}", "") for tag in tags}
        # Remove git ref "^{}" and duplicates. For example,
        # tags: ['/tags/version', '/tags/version^{}']
        # unique_tags: {'version'}

    except git.GitCommandError:
        return []
    return sorted(unique_tags)


def _get_user_input(
    text: str, default: Any = None, check_input: Callable = None
) -> Any:
    """Get user input and validate it.

    Args:
        text: Text to display in command line prompt.
        default: Default value for the input.
        check_input: Function to apply to check user input.

    Returns:
        Processed user value.

    """

    while True:
        value = click.prompt(text, default=default)
        if check_input:
            try:
                check_input(value)
            except KedroCliError as exc:
                click.secho(str(exc), fg="red", err=True)
                continue
        return value


def _get_config_from_prompts() -> Dict:
    """Ask user to provide necessary inputs.

    Returns:
        Resulting config dictionary.

    """

    # set output directory to the current directory
    output_dir = os.path.abspath(os.path.curdir)

    # get project name
    project_name_prompt = _get_prompt_text(
        "Project Name:",
        "Please enter a human readable name for your new project.",
        "Spaces and punctuation are allowed.",
        start="",
    )

    project_name = _get_user_input(project_name_prompt, default="New Kedro Project")

    normalized_project_name = re.sub(r"[^\w-]+", "-", project_name).lower().strip("-")

    # get repo name
    repo_name_prompt = _get_prompt_text(
        "Repository Name:",
        "Please enter a directory name for your new project repository.",
        "Alphanumeric characters, hyphens and underscores are allowed.",
        "Lowercase is recommended.",
    )
    repo_name = _get_user_input(
        repo_name_prompt,
        default=normalized_project_name,
        check_input=_assert_repo_name_ok,
    )

    # get python package_name
    default_pkg_name = normalized_project_name.replace("-", "_")
    pkg_name_prompt = _get_prompt_text(
        "Python Package Name:",
        "Please enter a valid Python package name for your project package.",
        "Alphanumeric characters and underscores are allowed.",
        "Lowercase is recommended. Package name must start with a letter "
        "or underscore.",
    )
    python_package = _get_user_input(
        pkg_name_prompt, default=default_pkg_name, check_input=_assert_pkg_name_ok
    )

    return {
        "output_dir": output_dir,
        "project_name": project_name,
        "repo_name": repo_name,
        "python_package": python_package,
    }


def _parse_config(config_path: str) -> Dict:
    """Parse the config YAML from its path.

    Args:
        config_path: The path of the config.yml file.

    Raises:
        Exception: If the file cannot be parsed.

    Returns:
        The config as a dictionary.

    """
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)

        if KedroCliError.VERBOSE_ERROR:
            click.echo(config_path + ":")
            click.echo(yaml.dump(config, default_flow_style=False))

        return config

    except Exception as exc:
        click.secho("Failed to parse " + config_path, fg="red", err=True)
        _show_example_config()
        raise exc


def _check_config_ok(config_path: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Check that the configuration file contains all needed variables.

    Args:
        config_path: The path of the config file.
        config: The config as a dictionary.

    Returns:
        Config dictionary.

    Raises:
        KedroCliError: If the config file is empty or does not contain all
            keys from template/cookiecutter.json and output_dir.

    """
    if config is None:
        _show_example_config()
        raise KedroCliError(config_path + " is empty")

    missing_keys = _get_default_config().keys() - config.keys()

    if missing_keys:
        click.echo(f"\n{config_path}:")
        click.echo(yaml.dump(config, default_flow_style=False))
        _show_example_config()

        missing_keys_str = ", ".join(str(k) for k in missing_keys)
        raise KedroCliError(f"[{missing_keys_str}] not found in {config_path}")

    config["output_dir"] = _fix_user_path(config["output_dir"])
    _assert_output_dir_ok(config["output_dir"])
    _assert_repo_name_ok(config["repo_name"])
    _assert_pkg_name_ok(config["python_package"])
    return config


def _get_default_config():
    default_config_path = TEMPLATE_PATH / "default_config.yml"
    with default_config_path.open() as default_config_file:
        return yaml.safe_load(default_config_file)


def _assert_output_dir_ok(output_dir: str):
    """Check that output directory exists.

    Args:
        output_dir: Output directory path.

    Raises:
        KedroCliError: If the output directory does not exist.

    """
    if not os.path.exists(output_dir):
        message = (
            f"`{output_dir}` is not a valid output directory. "
            f"It must be a relative or absolute path "
            f"to an existing directory."
        )
        raise KedroCliError(message)


def _assert_pkg_name_ok(pkg_name: str):
    """Check that python package name is in line with PEP8 requirements.

    Args:
        pkg_name: Candidate Python package name.

    Raises:
        KedroCliError: If package name violates the requirements.
    """

    base_message = f"`{pkg_name}` is not a valid Python package name."
    if not re.match(r"^[a-zA-Z_]", pkg_name):
        message = base_message + " It must start with a letter or underscore."
        raise KedroCliError(message)
    if len(pkg_name) < 2:
        message = base_message + " It must be at least 2 characters long."
        raise KedroCliError(message)
    if not re.match(r"^\w+$", pkg_name[1:]):
        message = (
            base_message + " It must contain only letters, digits, and/or underscores."
        )
        raise KedroCliError(message)


def _assert_repo_name_ok(repo_name):
    if not re.match(r"^\w+(-*\w+)*$", repo_name):
        message = (
            f"`{repo_name}` is not a valid repository name. It must contain "
            f"only word symbols and/or hyphens, must also start and "
            f"end with alphanumeric symbol."
        )
        raise KedroCliError(message)


def _fix_user_path(output_dir):
    output_dir = output_dir or ""
    output_dir = os.path.expanduser(output_dir)

    result = os.path.abspath(output_dir)
    return result


def _show_example_config():
    click.secho("Example of valid config.yml:")
    default_config = _get_default_config()
    for key, value in default_config.items():
        click.secho(
            click.style(key + ": ", bold=True, fg="yellow")
            + click.style(str(value), fg="cyan")
        )
    click.echo("")


def _print_kedro_new_success_message(result):
    click.secho(
        f"\nChange directory to the project generated in {result.resolve()}",
        fg="green",
    )
    click.secho(
        "\nA best-practice setup includes initialising git and creating "
        "a virtual environment before running `kedro install` to install "
        "project-specific dependencies. Refer to the Kedro documentation: "
        "https://kedro.readthedocs.io/"
    )


def _get_prompt_text(title, *text, start: str = "\n"):
    title = title.strip().title()
    title = click.style(title + "\n" + "=" * len(title), bold=True)
    prompt_lines = [title] + list(text)
    prompt_text = "\n".join(str(line).strip() for line in prompt_lines)
    return f"{start}{prompt_text}\n"


def get_project_context(
    key: str = "context", project_path: Path = None, **kwargs
) -> Any:
    """Gets the context value from context associated with the key.

    Args:
        key: Optional key to get associated value from Kedro context.
            Supported keys are "verbose" and "context", and it defaults to "context".
        project_path: Optional path to where the project root is to load the context.
            If omitted, the current working directory will be used.
        kwargs: Optional custom arguments defined by users, which will be passed into
            the constructor of the projects KedroContext subclass.

    Returns:
        Requested value from Kedro context dictionary or the default if the key
            was not found.

    Raises:
        KedroCliError: When the key is not found and the default value was not
            specified.
    """
    warnings.warn(
        "`get_project_context` is now deprecated and will be removed in Kedro 0.18.0. "
        "Please use `KedroSession.load_context()` to access the "
        "`KedroContext` object. For more information, please visit "
        "https://kedro.readthedocs.io/en/stable/04_kedro_project_setup/03_session.html",
        DeprecationWarning,
    )
    project_path = project_path or Path.cwd()
    context = load_context(project_path, **kwargs)
    # Dictionary to be compatible with existing Plugins. Future plugins should
    # retrieve necessary Kedro project properties from context
    value = {"context": context, "verbose": KedroCliError.VERBOSE_ERROR}[key]

    return deepcopy(value)


def load_entry_points(name: str) -> List[str]:
    """Load package entry point commands.

    Args:
        name: The key value specified in ENTRY_POINT_GROUPS.

    Raises:
        KedroCliError: If loading an entry point failed.

    Returns:
        List of entry point commands.

    """
    entry_points = pkg_resources.iter_entry_points(group=ENTRY_POINT_GROUPS[name])
    entry_point_commands = []
    for entry_point in entry_points:
        try:
            entry_point_commands.append(entry_point.load())
        except Exception as exc:
            raise KedroCliError(f"Loading {name} commands from {entry_point}") from exc
    return entry_point_commands


def _init_plugins():
    group = ENTRY_POINT_GROUPS["init"]
    for entry_point in pkg_resources.iter_entry_points(group=group):
        try:
            init_hook = entry_point.load()
            init_hook()
        except Exception as exc:
            raise KedroCliError(f"Initializing {entry_point}") from exc


def main():  # pragma: no cover
    """Main entry point, look for a `cli.py` and if found add its
    commands to `kedro`'s then invoke the cli.
    """
    _init_plugins()

    global_groups = [cli]
    global_groups.extend(load_entry_points("global"))
    project_groups = []
    cli_context = dict()

    path = Path.cwd()
    if _is_project(path):
        # load project commands from cli.py
        metadata = _get_project_metadata(path)
        cli_context = dict(obj=metadata)
        _add_src_to_path(metadata.source_dir, path)

        project_groups.extend(load_entry_points("project"))
        package_name = metadata.package_name

        try:
            project_cli = importlib.import_module(f"{package_name}.cli")
            project_groups.append(project_cli.cli)
        except Exception as exc:
            raise KedroCliError(
                f"Cannot load commands from {package_name}.cli"
            ) from exc

    cli_collection = CommandCollection(
        ("Global commands", global_groups),
        ("Project specific commands", project_groups),
    )
    cli_collection(**cli_context)


if __name__ == "__main__":  # pragma: no cover
    main()
