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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
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
from pathlib import Path

import click
from click import secho, style
from kedro.cli import main as kernalai_main
from kedro.cli.utils import KedroCliError, call, forward_command, python_call

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

# get our package onto the python path
PROJ_PATH = Path(__file__).resolve().parent
sys.path.append(str(PROJ_PATH / "src"))
os.environ["PYTHONPATH"] = (
    os.environ.get("PYTHONPATH", "") + os.pathsep + str(PROJ_PATH / "src")
)
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


ENV_ARG_HELP = """Run the pipeline in a configured environment. If not specified,
pipeline will run using environment `local`."""


PARALLEL_ARG_HELP = """Run the pipeline using the `ParallelRunner`.
If not specified, use the `SequentialRunner`. This flag cannot be used together
with --runner."""

RUNNER_ARG_HELP = """Specify a runner that you want to run the pipeline with.
This option cannot be used together with --parallel."""


def __get_kedro_context__():
    """Used to provide this project's context to plugins."""
    from {{cookiecutter.python_package}}.run import __kedro_context__
    return __kedro_context__()


@click.group(context_settings=CONTEXT_SETTINGS, name=__file__)
def cli():
    """Command line tools for manipulating a Kedro project."""


@cli.command()
@click.option("--runner", "-r", type=str, default=None, multiple=False, help=RUNNER_ARG_HELP)
@click.option("--parallel", "-p", is_flag=True, multiple=False, help=PARALLEL_ARG_HELP)
@click.option("--env", "-e", type=str, default=None, multiple=False, help=ENV_ARG_HELP)
@click.option("--tag", "-t", type=str, default=None, multiple=True, help=TAG_ARG_HELP)
def run(tag, env, parallel, runner):
    """Run the pipeline."""
    from {{cookiecutter.python_package}}.run import main
    if parallel and runner:
        raise KedroCliError(
            "Both --parallel and --runner options cannot be used together. "
            "Please use either --parallel or --runner."
        )
    if parallel:
        runner = "ParallelRunner"
    main(tags=tag, env=env, runner=runner)


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
    """Install project dependencies from requirements.txt."""
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
def build_docs():
    """Build the project documentation."""
    python_call("pip", ["install", "src/[docs]"])
    python_call("pip", ["install", "-r", "src/requirements.txt"])
    python_call(
        "ipykernel", ["install", "--user", "--name={{ cookiecutter.python_package }}"]
    )
    if Path("docs/build").exists():
        shutil.rmtree("docs/build")
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


@cli.group()
def jupyter():
    """Open Jupyter Notebook / Lab with project specific variables loaded."""


@forward_command(jupyter, "notebook", forward_help=True)
@click.option("--ip", type=str, default="127.0.0.1")
def jupyter_notebook(ip, args):
    """Open Jupyter Notebook with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message()
    call(["jupyter-notebook", "--ip=" + ip] + list(args))


@forward_command(jupyter, "lab", forward_help=True)
@click.option("--ip", type=str, default="127.0.0.1")
def jupyter_lab(ip, args):
    """Open Jupyter Lab with project specific variables loaded."""
    if "-h" not in args and "--help" not in args:
        ipython_message()
    call(["jupyter-lab", "--ip=" + ip] + list(args))


def ipython_message():
    """Show a message saying how we have configured the IPython env."""
    ipy_vars = ["proj_dir", "proj_name", "io", "startup_error"]
    secho("-" * 79, fg="cyan")
    secho("Starting a Kedro session with the following variables in scope")
    secho(", ".join(ipy_vars), fg="green")
    secho(
        "Use the line magic {} to refresh them".format(
            style("%reload_kedro", fg="green")
        )
    )
    secho("or to see the error message if they are undefined")
    secho("-" * 79, fg="cyan")


if __name__ == "__main__":
    os.chdir(str(PROJ_PATH))
    kernalai_main()
