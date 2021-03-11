# Copyright 2021 QuantumBlack Visual Analytics Limited
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

"""kedro is a CLI for managing Kedro projects.

This module implements commands available from the kedro CLI for creating
projects.
"""
import re
import tempfile
from collections import namedtuple
from pathlib import Path
from typing import Any, Dict, List

import click
import git
import yaml

import kedro
from kedro import __version__ as version
from kedro.framework.cli.utils import (
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    command_with_verbosity,
)

KEDRO_PATH = Path(kedro.__file__).parent
TEMPLATE_PATH = KEDRO_PATH / "templates" / "project"

_STARTER_ALIASES = {
    "mini-kedro",
    "pandas-iris",
    "pyspark",
    "pyspark-iris",
    "spaceflights",
}
_STARTERS_REPO = "git+https://github.com/quantumblacklabs/kedro-starters.git"


@click.group(name="Kedro")
def create_cli():  # pragma: no cover
    """Command line tools for creating Kedro projects."""
    pass


@command_with_verbosity(create_cli, short_help="Create a new kedro project.")
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


@create_cli.group()
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

    config: Dict[str, str] = dict()
    checkout = checkout or version
    try:
        if config_path:
            config = _parse_config(config_path)
            config = _check_config_ok(config_path, config)
        else:
            config = _prompt_user_for_config(template_path, checkout, directory)

        config.setdefault("kedro_version", version)
        cookiecutter_args = dict(
            output_dir=config.get("output_dir", str(Path.cwd().resolve())),
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


def _prompt_user_for_config(  # pylint: disable=too-many-locals
    template_path: Path, checkout: str = None, directory: str = None
) -> Dict[str, str]:
    """Prompt user in the CLI to provide configuration values for cookiecutter variables
    in a starter, such as project_name, package_name, etc.
    """
    # pylint: disable=import-outside-toplevel
    from cookiecutter.prompt import read_user_variable, render_variable
    from cookiecutter.repository import determine_repo_dir  # for performance reasons

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir_path = Path(tmpdir).resolve()
        cookiecutter_repo, _ = determine_repo_dir(
            template=str(template_path),
            abbreviations=dict(),
            clone_to_dir=temp_dir_path,
            checkout=checkout,
            no_input=True,
            directory=directory,
        )
        cookiecutter_dir = temp_dir_path / cookiecutter_repo
        prompts_yml = cookiecutter_dir / "prompts.yml"

        # If there is no prompts.yml, no need to ask user for input.
        if not prompts_yml.is_file():
            return {}

        with open(prompts_yml) as config_file:
            prompts_dict = yaml.safe_load(config_file)

        cookiecutter_env = _prepare_cookiecutter_env(cookiecutter_dir)

        config: Dict[str, str] = dict()
        config["output_dir"] = str(Path.cwd().resolve())

        for variable_name, prompt_dict in prompts_dict.items():
            prompt = _Prompt(**prompt_dict)

            # render the variable on the command line
            cookiecutter_variable = render_variable(
                env=cookiecutter_env.env,
                raw=cookiecutter_env.context[variable_name],
                cookiecutter_dict=config,
            )

            # read the user's input for the variable
            user_input = read_user_variable(str(prompt), cookiecutter_variable)
            if user_input:
                prompt.validate(user_input)
                config[variable_name] = user_input
        return config


# A cookiecutter env contains the context and environment to render templated
# cookiecutter values on the CLI.
_CookiecutterEnv = namedtuple("CookiecutterEnv", ["env", "context"])


def _prepare_cookiecutter_env(cookiecutter_dir) -> _CookiecutterEnv:
    """Prepare the cookiecutter environment to render its default values
    when prompting user on the CLI for inputs.
    """
    # pylint: disable=import-outside-toplevel
    from cookiecutter.environment import StrictEnvironment
    from cookiecutter.generate import generate_context

    cookiecutter_json = cookiecutter_dir / "cookiecutter.json"
    cookiecutter_context = generate_context(context_file=cookiecutter_json).get(
        "cookiecutter", {}
    )
    cookiecutter_env = StrictEnvironment(context=cookiecutter_context)
    return _CookiecutterEnv(context=cookiecutter_context, env=cookiecutter_env)


class _Prompt:
    """Represent a single CLI prompt for `kedro new`
    """

    def __init__(self, *args, **kwargs) -> None:  # pylint: disable=unused-argument
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
        """Validate a given prompt value against the regex validator
        """
        if self.regexp and not re.match(self.regexp, user_input):
            click.secho(f"`{user_input}` is an invalid value.", fg="red", err=True)
            click.secho(self.error_message, fg="red", err=True)
            raise ValueError(user_input)


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

    mandatory_keys = set(_get_prompts_config().keys())
    mandatory_keys.add("output_dir")
    missing_keys = mandatory_keys - set(config.keys())

    if missing_keys:
        click.echo(f"\n{config_path}:")
        click.echo(yaml.dump(config, default_flow_style=False))
        _show_example_config()

        missing_keys_str = ", ".join(str(k) for k in missing_keys)
        raise KedroCliError(f"[{missing_keys_str}] not found in {config_path}")

    config["output_dir"] = Path(config.get("output_dir", "")).expanduser().resolve()
    _assert_output_dir_ok(config["output_dir"])
    return config


def _get_prompts_config():
    prompts_config_path = TEMPLATE_PATH / "prompts.yml"
    with prompts_config_path.open() as prompts_config_file:
        return yaml.safe_load(prompts_config_file)


def _assert_output_dir_ok(output_dir: str):
    """Check that output directory exists.
    Args:
        output_dir: Output directory path.
    Raises:
        KedroCliError: If the output directory does not exist.
    """
    if not Path(output_dir).exists():
        message = (
            f"`{output_dir}` is not a valid output directory. "
            f"It must be a relative or absolute path "
            f"to an existing directory."
        )
        raise KedroCliError(message)


def _show_example_config():
    click.secho("Example of valid config.yml:")
    prompts_config = _get_prompts_config()
    for key, value in prompts_config.items():
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
        "a virtual environment before running ``kedro install`` to install "
        "project-specific dependencies. Refer to the Kedro documentation: "
        "https://kedro.readthedocs.io/"
    )
