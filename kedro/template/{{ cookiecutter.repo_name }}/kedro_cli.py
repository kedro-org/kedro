# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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
from collections import Counter
from glob import iglob
from pathlib import Path
import webbrowser

import click
from click import secho, style
from kedro.cli import main as kedro_main
from kedro.cli.utils import (
    KedroCliError,
    call,
    forward_command,
    python_call,
    export_nodes,
)
from kedro.utils import load_obj
from kedro.runner import SequentialRunner
from kedro.context import load_context
from typing import Iterable, List, Dict

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# get our package onto the python path
PROJ_PATH = Path(__file__).resolve().parent
os.environ["IPYTHONDIR"] = str(PROJ_PATH / ".ipython")


NO_PYTEST_MESSAGE = """
pytest is not installed. Please make sure pytest is in
src/requirements.txt and run `kedro install`.
"""

NO_NBSTRIPOUT_MESSAGE = """
nbstripout is not installed. Please make sure nbstripout is in
`src/requirements.txt` and run `kedro install`.
"""

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
This option cannot be used together with --parallel."""

CONVERT_ALL_HELP = """Extract the nodes from all notebooks in the Kedro project directory,
including sub-folders."""

OVERWRITE_HELP = """If Python file already exists for the equivalent notebook,
overwrite its contents."""

LOAD_VERSION_HELP = """Specify a particular dataset version (timestamp) for loading."""


def _split_string(ctx, param, value):
    return [item for item in value.split(",") if item]


def _reformat_load_versions(ctx, param, value) -> Dict[str, str]:
    """Reformat data structure from tuple to dictionary for `load-version`.
        E.g ('dataset1:time1', 'dataset2:time2') -> {"dataset1": "time1", "dataset2": "time2"}.
    """
    load_version_separator = ":"
    load_versions_dict = {}

    for load_version in value:
        load_version_list = load_version.split(load_version_separator)
        if len(load_version_list) != 2:
            raise ValueError(
                "Expected the form of `load_version` to be "
                "`dataset_name:YYYY-MM-DDThh.mm.ss.sssZ`,"
                "found {} instead".format(load_version)
            )
        load_versions_dict[load_version_list[0]] = load_version_list[1]

    return load_versions_dict


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
@click.option("--env", "-e", type=str, default=None, multiple=False, help=ENV_ARG_HELP)
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
):
    """Run the pipeline."""
    if parallel and runner:
        raise KedroCliError(
            "Both --parallel and --runner options cannot be used together. "
            "Please use either --parallel or --runner."
        )
    if parallel:
        runner = "ParallelRunner"
    runner_class = load_obj(runner, "kedro.runner") if runner else SequentialRunner

    context = load_context(Path.cwd(), env=env)
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
        raise KedroCliError(NO_PYTEST_MESSAGE)
    else:
        python_call("pytest", args)


@cli.command()
def install():
    """Install project dependencies from both requirements.txt and environment.yml (optional)."""

    if (Path.cwd() / "src" / "environment.yml").is_file():
        call(["conda", "install", "--file", "src/environment.yml", "--yes"])

    python_call("pip", ["install", "-U", "-r", "src/requirements.txt"])


@forward_command(cli, forward_help=True)
def ipython(args):
    """Open IPython with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message()
    call(["ipython"] + list(args))


@cli.command()
def package():
    """Package the project as a Python egg and wheel."""
    call([sys.executable, "setup.py", "clean", "--all", "bdist_egg"], cwd="src")
    call([sys.executable, "setup.py", "clean", "--all", "bdist_wheel"], cwd="src")


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
    python_call("pip", ["install", "src/[docs]"])
    python_call("pip", ["install", "-r", "src/requirements.txt"])
    python_call(
        "ipykernel", ["install", "--user", "--name={{ cookiecutter.python_package }}"]
    )
    shutil.rmtree("docs/build", ignore_errors=True)
    call(
        [
            "sphinx-apidoc",
            "--module-first",
            "-o",
            "docs/source",
            "src/{{ cookiecutter.python_package }}",
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
    requirements_path = Path.cwd() / "src" / "requirements.in"
    if not requirements_path.is_file():
        secho("No requirements.in found. Copying contents from requirements.txt...")
        contents = (Path.cwd() / "src" / "requirements.txt").read_text()
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
        raise KedroCliError(NO_NBSTRIPOUT_MESSAGE)

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


def _build_jupyter_command(
    base: str, ip: str, all_kernels: bool, args: Iterable[str]
) -> List[str]:
    cmd = [base, "--ip=" + ip]

    if not all_kernels:
        cmd.append("--KernelSpecManager.whitelist=['python3']")

    return cmd + list(args)


@cli.group()
def jupyter():
    """Open Jupyter Notebook / Lab with project specific variables loaded, or
    convert notebooks into Kedro code.
    """


@forward_command(jupyter, "notebook", forward_help=True)
@click.option("--ip", type=str, default="127.0.0.1")
@click.option("--all-kernels", is_flag=True, default=False)
def jupyter_notebook(ip, all_kernels, args):
    """Open Jupyter Notebook with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message(all_kernels)

    call(
        _build_jupyter_command(
            "jupyter-notebook", ip=ip, all_kernels=all_kernels, args=args
        )
    )


@forward_command(jupyter, "lab", forward_help=True)
@click.option("--ip", type=str, default="127.0.0.1")
@click.option("--all-kernels", is_flag=True, default=False)
def jupyter_lab(ip, all_kernels, args):
    """Open Jupyter Lab with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message(all_kernels)

    call(
        _build_jupyter_command("jupyter-lab", ip=ip, all_kernels=all_kernels, args=args)
    )


@jupyter.command("convert")
@click.option("--all", "all_flag", is_flag=True, help=CONVERT_ALL_HELP)
@click.option("-y", "overwrite_flag", is_flag=True, help=OVERWRITE_HELP)
@click.argument(
    "filepath",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=False,
    nargs=-1,
)
def convert_notebook(all_flag, overwrite_flag, filepath):
    """Convert selected or all notebooks found in a Kedro project
    to Kedro code, by exporting code from the appropriately-tagged cells:
    Cells tagged as `node` will be copied over to a Python file matching
    the name of the notebook, under `src/<package_name>/nodes`.
    *Note*: Make sure your notebooks have unique names!
    FILEPATH: Path(s) to exact notebook file(s) to be converted. Both
    relative and absolute paths are accepted.
    Should not be provided if --all flag is already present.
    """
    context = load_context(Path.cwd())

    if not filepath and not all_flag:
        secho(
            "Please specify a notebook filepath "
            "or add '--all' to convert all notebooks."
        )
        sys.exit(1)

    kedro_project_path = context.project_path
    kedro_package_name = "{{cookiecutter.python_package}}"

    if all_flag:
        # pathlib glob does not ignore hidden directories,
        # whereas Python glob does, which is more useful in
        # ensuring checkpoints will not be included
        pattern = kedro_project_path / "**" / "*.ipynb"
        notebooks = sorted(Path(p) for p in iglob(str(pattern), recursive=True))
    else:
        notebooks = [Path(f) for f in filepath]

    counter = Counter(n.stem for n in notebooks)
    non_unique_names = [name for name, counts in counter.items() if counts > 1]
    if non_unique_names:
        raise KedroCliError(
            "Found non-unique notebook names! "
            "Please rename the following: {}".format(", ".join(non_unique_names))
        )

    for notebook in notebooks:
        secho("Converting notebook '{}'...".format(str(notebook)))
        output_path = (
            kedro_project_path
            / "src"
            / kedro_package_name
            / "nodes"
            / "{}.py".format(notebook.stem)
        )

        if output_path.is_file():
            overwrite = overwrite_flag or click.confirm(
                "Output file {} already exists. Overwrite?".format(str(output_path)),
                default=False,
            )
            if overwrite:
                export_nodes(notebook, output_path)
        else:
            export_nodes(notebook, output_path)

    secho("Done!")


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


if __name__ == "__main__":
    os.chdir(str(PROJ_PATH))
    kedro_main()
