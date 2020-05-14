# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Command line tools for manipulating a Kedro project.
Intended to be invoked via `kedro`."""
import os
import shutil
import subprocess
import sys
import webbrowser

import yaml
from itertools import chain
from pathlib import Path
from typing import Dict, Iterable, Tuple


import click
from click import secho, style
from kedro.framework.cli import main as kedro_main
from kedro.framework.cli.catalog import catalog as catalog_group
from kedro.framework.cli.jupyter import jupyter as jupyter_group
from kedro.framework.cli.pipeline import pipeline as pipeline_group
from kedro.framework.cli.utils import (
    KedroCliError,
    call,
    forward_command,
    python_call,
)
from kedro.framework.context import load_context, validate_source_path

from kedro.utils import load_obj

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# get our package onto the python path
PROJ_PATH = Path(__file__).resolve().parent
os.environ["IPYTHONDIR"] = str(PROJ_PATH / ".ipython")

with (PROJ_PATH / ".kedro.yml").open("r") as kedro_yml:
    kedro_yaml = yaml.safe_load(kedro_yml)

SOURCE_DIR = Path(kedro_yaml.get("source_dir", "src")).expanduser()
SOURCE_PATH = (PROJ_PATH / SOURCE_DIR).resolve()
validate_source_path(SOURCE_PATH, PROJ_PATH)

KEDRO_PACKAGE_NAME = "{{ cookiecutter.python_package }}"

NO_DEPENDENCY_MESSAGE = """{module} is not installed. Please make sure {module} is in
{src}/requirements.txt and run `kedro install`."""

TAG_ARG_HELP = """Construct the pipeline using only nodes which have this tag
attached. Option can be used multiple times, what results in a
pipeline constructed from nodes having any of those tags."""

PIPELINE_ARG_HELP = """Name of the modular pipeline to run.
If not set, the project pipeline is run by default."""

ENV_ARG_HELP = """Run the pipeline in a configured environment. If not specified,
pipeline will run using environment `local`."""

NODE_ARG_HELP = """Run only nodes with specified names."""

FROM_NODES_HELP = """A list of node names which should be used as a starting point."""

TO_NODES_HELP = """A list of node names which should be used as an end point."""

FROM_INPUTS_HELP = (
    """A list of dataset names which should be used as a starting point."""
)

PARALLEL_ARG_HELP = """Run the pipeline using the `ParallelRunner`.
If not specified, use the `SequentialRunner`. This flag cannot be used together
with --runner."""

OPEN_ARG_HELP = """Open the documentation in your default browser after building."""

RUNNER_ARG_HELP = """Specify a runner that you want to run the pipeline with.
Available runners: `SequentialRunner`, `ParallelRunner` and `ThreadRunner`.
This option cannot be used together with --parallel."""

LOAD_VERSION_HELP = """Specify a particular dataset version (timestamp) for loading."""

CONFIG_FILE_HELP = """Specify a YAML configuration file to load the run
command arguments from. If command line arguments are provided, they will
override the loaded ones."""

PARAMS_ARG_HELP = """Specify extra parameters that you want to pass
to the context initializer. Items must be separated by comma, keys - by colon,
example: param1:value1,param2:value2. Each parameter is split by the first comma,
so parameter values are allowed to contain colons, parameter keys are not."""

LINT_CHECK_ONLY_HELP = """Check the files for style guide violations, unsorted /
unformatted imports, and unblackened Python code without modifying the files."""


def _env_option(func_=None, **kwargs):
    default_args = dict(type=str, default=None, help=ENV_ARG_HELP)
    kwargs = {**default_args, **kwargs}
    opt = click.option("--env", "-e", **kwargs)
    return opt(func_) if func_ else opt


def _split_string(ctx, param, value):
    return [item.strip() for item in value.split(",") if item.strip()]


def _try_convert_to_numeric(value):
    try:
        value = float(value)
    except ValueError:
        return value
    return int(value) if value.is_integer() else value


def _split_params(ctx, param, value):
    if isinstance(value, dict):
        return value
    result = {}
    for item in _split_string(ctx, param, value):
        item = item.split(":", 1)
        if len(item) != 2:
            ctx.fail(
                "Invalid format of `{}` option: Item `{}` must contain a key and "
                "a value separated by `:`.".format(param.name, item[0])
            )
        key = item[0].strip()
        if not key:
            ctx.fail(
                "Invalid format of `{}` option: Parameter key cannot be "
                "an empty string.".format(param.name)
            )
        value = item[1].strip()
        result[key] = _try_convert_to_numeric(value)
    return result


def _reformat_load_versions(ctx, param, value) -> Dict[str, str]:
    """Reformat data structure from tuple to dictionary for `load-version`.
        E.g ('dataset1:time1', 'dataset2:time2') -> {"dataset1": "time1", "dataset2": "time2"}.
    """
    load_version_separator = ":"
    load_versions_dict = {}

    for load_version in value:
        load_version_list = load_version.split(load_version_separator, 1)
        if len(load_version_list) != 2:
            raise ValueError(
                "Expected the form of `load_version` to be "
                "`dataset_name:YYYY-MM-DDThh.mm.ss.sssZ`,"
                "found {} instead".format(load_version)
            )
        load_versions_dict[load_version_list[0]] = load_version_list[1]

    return load_versions_dict


def _config_file_callback(ctx, param, value):
    """Config file callback, that replaces command line options with config file
    values. If command line options are passed, they override config file values.
    """
    # for performance reasons
    import anyconfig  # pylint: disable=import-outside-toplevel

    ctx.default_map = ctx.default_map or {}
    section = ctx.info_name

    if value:
        config = anyconfig.load(value)[section]
        ctx.default_map.update(config)

    return value


def _get_values_as_tuple(values: Iterable[str]) -> Tuple[str, ...]:
    return tuple(chain.from_iterable(value.split(",") for value in values))


@click.group(context_settings=CONTEXT_SETTINGS, name=__file__)
def cli():
    """Command line tools for manipulating a Kedro project."""


@cli.command()
@click.option(
    "--from-inputs", type=str, default="", help=FROM_INPUTS_HELP, callback=_split_string
)
@click.option(
    "--from-nodes", type=str, default="", help=FROM_NODES_HELP, callback=_split_string
)
@click.option(
    "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=_split_string
)
@click.option("--node", "-n", "node_names", type=str, multiple=True, help=NODE_ARG_HELP)
@click.option(
    "--runner", "-r", type=str, default=None, multiple=False, help=RUNNER_ARG_HELP
)
@click.option("--parallel", "-p", is_flag=True, multiple=False, help=PARALLEL_ARG_HELP)
@_env_option
@click.option("--tag", "-t", type=str, multiple=True, help=TAG_ARG_HELP)
@click.option(
    "--load-version",
    "-lv",
    type=str,
    multiple=True,
    help=LOAD_VERSION_HELP,
    callback=_reformat_load_versions,
)
@click.option("--pipeline", type=str, default=None, help=PIPELINE_ARG_HELP)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=CONFIG_FILE_HELP,
    callback=_config_file_callback,
)
@click.option(
    "--params", type=str, default="", help=PARAMS_ARG_HELP, callback=_split_params
)
def run(
    tag,
    env,
    parallel,
    runner,
    node_names,
    to_nodes,
    from_nodes,
    from_inputs,
    load_version,
    pipeline,
    config,
    params,
):
    """Run the pipeline."""
    if parallel and runner:
        raise KedroCliError(
            "Both --parallel and --runner options cannot be used together. "
            "Please use either --parallel or --runner."
        )
    runner = runner or "SequentialRunner"
    if parallel:
        runner = "ParallelRunner"
    runner_class = load_obj(runner, "kedro.runner")

    tag = _get_values_as_tuple(tag) if tag else tag
    node_names = _get_values_as_tuple(node_names) if node_names else node_names

    context = load_context(Path.cwd(), env=env, extra_params=params)
    context.run(
        tags=tag,
        runner=runner_class(),
        node_names=node_names,
        from_nodes=from_nodes,
        to_nodes=to_nodes,
        from_inputs=from_inputs,
        load_versions=load_version,
        pipeline_name=pipeline,
    )


@forward_command(cli, forward_help=True)
def test(args):
    """Run the test suite."""
    try:
        import pytest  # pylint: disable=unused-import
    except ImportError:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="pytest", src=str(SOURCE_PATH))
        )
    else:
        python_call("pytest", args)


@cli.command()
@click.option("-c", "--check-only", is_flag=True, help=LINT_CHECK_ONLY_HELP)
@click.argument("files", type=click.Path(exists=True), nargs=-1)
def lint(files, check_only):
    """Run flake8, isort and (on Python >=3.6) black."""
    files = files or (str(SOURCE_PATH / "tests"), str(SOURCE_PATH / KEDRO_PACKAGE_NAME))

    try:
        import flake8
        import isort
        import black
    except ImportError as exc:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module=exc.name, src=str(SOURCE_PATH))
        )

    python_call("black", ("--check",) + files if check_only else files)
    python_call("flake8", ("--max-line-length=88",) + files)

    check_flag = ("-c",) if check_only else ()
    python_call(
        "isort", (*check_flag, "-rc", "-tc", "-up", "-fgw=0", "-m=3", "-w=88") + files
    )


@cli.command()
def install():
    """Install project dependencies from both requirements.txt
    and environment.yml (optional)."""

    if (SOURCE_PATH / "environment.yml").is_file():
        call(
            [
                "conda",
                "install",
                "--file",
                str(SOURCE_PATH / "environment.yml"),
                "--yes",
            ]
        )

    pip_command = ["install", "-U", "-r", str(SOURCE_PATH / "requirements.txt")]

    if os.name == "posix":
        python_call("pip", pip_command)
    else:
        command = [sys.executable, "-m", "pip"] + pip_command
        subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)


@forward_command(cli, forward_help=True)
def ipython(args):
    """Open IPython with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message()
    call(["ipython"] + list(args))


@cli.command()
def package():
    """Package the project as a Python egg and wheel."""
    call(
        [sys.executable, "setup.py", "clean", "--all", "bdist_egg"],
        cwd=str(SOURCE_PATH),
    )
    call(
        [sys.executable, "setup.py", "clean", "--all", "bdist_wheel"],
        cwd=str(SOURCE_PATH),
    )


@cli.command("build-docs")
@click.option(
    "--open",
    "-o",
    "open_docs",
    is_flag=True,
    multiple=False,
    default=False,
    help=OPEN_ARG_HELP,
)
def build_docs(open_docs):
    """Build the project documentation."""
    python_call("pip", ["install", str(SOURCE_PATH / "[docs]")])
    python_call("pip", ["install", "-r", str(SOURCE_PATH / "requirements.txt")])
    python_call("ipykernel", ["install", "--user", f"--name={KEDRO_PACKAGE_NAME}"])
    shutil.rmtree("docs/build", ignore_errors=True)
    call(
        [
            "sphinx-apidoc",
            "--module-first",
            "-o",
            "docs/source",
            str(SOURCE_PATH / KEDRO_PACKAGE_NAME),
        ]
    )
    call(["sphinx-build", "-M", "html", "docs/source", "docs/build", "-a"])
    if open_docs:
        docs_page = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        secho("Opening {}".format(docs_page))
        webbrowser.open(docs_page)


@cli.command("build-reqs")
def build_reqs():
    """Build the project dependency requirements."""
    requirements_path = SOURCE_PATH / "requirements.in"
    if not requirements_path.is_file():
        secho("No requirements.in found. Copying contents from requirements.txt...")
        contents = (SOURCE_PATH / "requirements.txt").read_text()
        requirements_path.write_text(contents)
    python_call("piptools", ["compile", str(requirements_path)])
    secho(
        (
            "Requirements built! Please update requirements.in "
            "if you'd like to make a change in your project's dependencies, "
            "and re-run build-reqs to generate the new requirements.txt."
        )
    )


@cli.command("activate-nbstripout")
def activate_nbstripout():
    """Install the nbstripout git hook to automatically clean notebooks."""
    secho(
        (
            "Notebook output cells will be automatically cleared before committing"
            " to git."
        ),
        fg="yellow",
    )

    try:
        import nbstripout  # pylint: disable=unused-import
    except ImportError:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="nbstripout", src=str(SOURCE_PATH))
        )

    try:
        res = subprocess.run(
            ["git", "rev-parse", "--git-dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode:
            raise KedroCliError("Not a git repository. Run `git init` first.")
    except FileNotFoundError:
        raise KedroCliError("Git executable not found. Install Git first.")

    call(["nbstripout", "--install"])


def ipython_message(all_kernels=True):
    """Show a message saying how we have configured the IPython env."""
    ipy_vars = ["startup_error", "context"]
    secho("-" * 79, fg="cyan")
    secho("Starting a Kedro session with the following variables in scope")
    secho(", ".join(ipy_vars), fg="green")
    secho(
        "Use the line magic {} to refresh them".format(
            style("%reload_kedro", fg="green")
        )
    )
    secho("or to see the error message if they are undefined")

    if not all_kernels:
        secho("The choice of kernels is limited to the default one.", fg="yellow")
        secho("(restart with --all-kernels to get access to others)", fg="yellow")

    secho("-" * 79, fg="cyan")


cli.add_command(pipeline_group)
cli.add_command(catalog_group)
cli.add_command(jupyter_group)


if __name__ == "__main__":
    os.chdir(str(PROJ_PATH))
    kedro_main()
