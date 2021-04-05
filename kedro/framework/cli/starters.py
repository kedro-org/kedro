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
    CONTEXT_SETTINGS,
    KedroCliError,
    _clean_pycache,
    _filter_deprecation_warnings,
    command_with_verbosity,
)

KEDRO_PATH = Path(kedro.__file__).parent
TEMPLATE_PATH = KEDRO_PATH / "templates" / "project"

_STARTER_ALIASES = {
    "astro-iris",
    "mini-kedro",
    "pandas-iris",
    "pyspark",
    "pyspark-iris",
    "spaceflights",
}
_STARTERS_REPO = "git+https://github.com/quantumblacklabs/kedro-starters.git"


# pylint: disable=missing-function-docstring
@click.group(context_settings=CONTEXT_SETTINGS, name="Kedro")
def create_cli():  # pragma: no cover
    pass


@command_with_verbosity(create_cli, short_help="Create a new kedro project.")
@click.option(
    "--config",
    "-c",
    "config_path",
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
    config_path, starter_name, checkout, directory, **kwargs
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
        checkout = checkout or version
    elif starter_name is not None:
        template_path = starter_name
        checkout = checkout or version
    else:
        template_path = str(TEMPLATE_PATH)

    if config_path:
        config = _fetch_config_from_file(config_path)
    else:
        config = _fetch_config_from_prompts(template_path, checkout, directory)
    config.setdefault("kedro_version", version)

    cookiecutter_args = _make_cookiecutter_args(config, checkout, directory)
    _create_project(template_path, cookiecutter_args)


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


def _fetch_config_from_file(config_path: str) -> Dict[str, str]:
    """Obtains configuration for a new kedro project non-interactively from a file.

    Args:
        config_path: The path of the config.yml which should contain the data required
            by ``prompts.yml`` and also ``output_dir``.

    Returns:
        Configuration for starting a new project. This is passed as ``extra_context``
            to cookiecutter and will overwrite the cookiecutter.json defaults.
    """
    config = _parse_config_from_file(config_path)
    _validate_config_from_file(config_path, config)
    config["output_dir"] = Path(config["output_dir"]).expanduser().resolve()  # type: ignore
    _assert_output_dir_ok(config["output_dir"])  # type: ignore
    return config


def _make_cookiecutter_args(
    config: Dict[str, str], checkout: str, directory: str,
) -> Dict[str, Any]:
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


def _create_project(template_path: str, cookiecutter_args: Dict[str, str]):
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
    with _filter_deprecation_warnings():
        # pylint: disable=import-outside-toplevel
        from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound
        from cookiecutter.main import cookiecutter  # for performance reasons

    try:
        result_path = cookiecutter(template_path, **cookiecutter_args)
    except (RepositoryNotFound, RepositoryCloneFailed) as exc:
        error_message = (
            f"Kedro project template not found at {template_path}"
            f" with tag {cookiecutter_args.get('checkout')}."
        )
        tags = _get_available_tags(template_path)
        if tags:
            error_message += f" The following tags are available: {', '.join(tags)}"
        raise KedroCliError(error_message) from exc
    # we don't want the user to see a stack trace on the cli
    except Exception as exc:
        raise KedroCliError("Failed to generate project.") from exc

    _clean_pycache(Path(result_path))
    _print_kedro_new_success_message(result_path)


def _fetch_config_from_prompts(
    template_path: str, checkout: str, directory: str
) -> Dict[str, str]:
    """Obtains configuration for a new kedro project interactively from user prompts.

    Args:
       template_path: The path to the cookiecutter template to create the project.
           It could either be a local directory or a remote VCS repository
           supported by cookiecutter. For more details, please see:
           https://cookiecutter.readthedocs.io/en/latest/usage.html#generate-your-project
       checkout: The tag, branch or commit in the starter repository to checkout.
           Maps directly to cookiecutter's ``checkout`` argument. Relevant only when
           using a starter.
       directory: The directory of a specific starter inside a repository containing
           multiple starters. Maps directly to cookiecutter's ``directory`` argument.
           Relevant only when using a starter.
           https://cookiecutter.readthedocs.io/en/1.7.2/advanced/directories.html

    Returns:
        Configuration for starting a new project. This is passed as ``extra_context``
        to cookiecutter and will overwrite the cookiecutter.json defaults.

    Raises:
        KedroCliError: if Kedro project template could not be found.
    """
    # pylint: disable=import-outside-toplevel, too-many-locals
    from cookiecutter.exceptions import RepositoryCloneFailed, RepositoryNotFound
    from cookiecutter.repository import determine_repo_dir  # for performance reasons

    with tempfile.TemporaryDirectory() as tmpdir:
        temp_dir_path = Path(tmpdir).resolve()
        try:
            cookiecutter_repo, _ = determine_repo_dir(
                template=template_path,
                abbreviations=dict(),
                clone_to_dir=temp_dir_path,
                checkout=checkout,
                no_input=True,
                directory=directory,
            )
        except (RepositoryNotFound, RepositoryCloneFailed) as exc:
            error_message = (
                f"Kedro project template not found at {template_path}"
                f" with tag {checkout}."
            )
            tags = _get_available_tags(template_path)
            if tags:
                error_message += f" The following tags are available: {', '.join(tags)}"
            raise KedroCliError(error_message) from exc

        cookiecutter_dir = temp_dir_path / cookiecutter_repo
        prompts_yml = cookiecutter_dir / "prompts.yml"

        # If there is no prompts.yml, no need to ask user for input.
        if not prompts_yml.is_file():
            return dict()

        prompts = _parse_prompts_from_file(prompts_yml)
        return _run_prompts_for_user_input(prompts, cookiecutter_dir)


def _run_prompts_for_user_input(
    prompts: Dict[str, Dict[str, str]], cookiecutter_dir: Path
) -> Dict[str, str]:
    # pylint: disable=import-outside-toplevel
    from cookiecutter.prompt import read_user_variable, render_variable

    cookiecutter_env = _prepare_cookiecutter_env(cookiecutter_dir)
    config: Dict[str, str] = dict()

    for variable_name, prompt_dict in prompts.items():
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


def _parse_config_from_file(config_path: str) -> Dict[str, str]:
    """Parses the config YAML from its path.

    Args:
        config_path: The path of the config.yml file.

    Raises:
        KedroCliError: If the file cannot be parsed.

    Returns:
        The config as a dictionary.
    """
    try:
        with open(config_path, "r") as config_file:
            config = yaml.safe_load(config_file)

        if KedroCliError.VERBOSE_ERROR:
            click.echo(config_path + ":")
            click.echo(yaml.dump(config, default_flow_style=False))
    except Exception as exc:
        _show_example_config()
        raise KedroCliError(f"Failed to parse {config_path}.") from exc

    return config


def _validate_config_from_file(config_path: str, config: Dict[str, str]) -> None:
    """Checks that the configuration file contains all needed variables.

    Args:
        config_path: The path of the config file.
        config: The config as a dictionary.

    Raises:
        KedroCliError: If the config file is empty or does not contain all
            keys from template/cookiecutter.json and output_dir.
    """
    if config is None:
        _show_example_config()
        raise KedroCliError(config_path + " is empty")

    mandatory_keys = set(_parse_prompts_from_file(TEMPLATE_PATH / "prompts.yml").keys())
    mandatory_keys.add("output_dir")
    missing_keys = mandatory_keys - set(config.keys())

    if missing_keys:
        click.echo(f"\n{config_path}:")
        click.echo(yaml.dump(config, default_flow_style=False))
        _show_example_config()

        raise KedroCliError(f"{', '.join(missing_keys)} not found in {config_path}")


def _parse_prompts_from_file(prompts_yml: Path) -> Dict[str, Dict[str, str]]:
    try:
        with prompts_yml.open() as prompts:
            return yaml.safe_load(prompts)
    # we don't want the user to see a stack trace on the cli
    except Exception as exc:  # pragma: no cover
        raise KedroCliError("Failed to generate project.") from exc


def _assert_output_dir_ok(output_dir: Path):
    """Checks that output directory exists.

    Args:
        output_dir: Output directory path.

    Raises:
        KedroCliError: If the output directory does not exist.
    """
    if not output_dir.exists():
        message = (
            f"`{output_dir}` is not a valid output directory. "
            f"It must be a relative or absolute path "
            f"to an existing directory."
        )
        raise KedroCliError(message)


def _show_example_config():
    click.secho("Example of valid config.yml:")
    prompts_config = _parse_prompts_from_file(TEMPLATE_PATH / "prompts.yml")
    for key, value in prompts_config.items():
        click.secho(
            click.style(key + ": ", bold=True, fg="yellow")
            + click.style(str(value), fg="cyan")
        )
    click.echo("")


def _print_kedro_new_success_message(result_path):
    click.secho(
        f"\nChange directory to the project generated in {result_path}", fg="green",
    )
    click.secho(
        "\nA best-practice setup includes initialising git and creating "
        "a virtual environment before running ``kedro install`` to install "
        "project-specific dependencies. Refer to the Kedro documentation: "
        "https://kedro.readthedocs.io/"
    )
