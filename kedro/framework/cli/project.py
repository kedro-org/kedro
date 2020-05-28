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

"""A collection of CLI commands for working with Kedro project."""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import click
from click import secho

from kedro.framework.cli.cli import _handle_exception
from kedro.framework.cli.utils import (
    KedroCliError,
    call,
    env_option,
    forward_command,
    get_source_dir,
    ipython_message,
    python_call,
)
from kedro.framework.context import load_context

NO_DEPENDENCY_MESSAGE = """{module} is not installed. Please make sure {module} is in
{src}/requirements.txt and run `kedro install`."""
LINT_CHECK_ONLY_HELP = """Check the files for style guide violations, unsorted /
unformatted imports, and unblackened Python code without modifying the files."""
OPEN_ARG_HELP = """Open the documentation in your default browser after building."""


def _load_project_context(**kwargs):
    """Returns project context."""
    try:
        return load_context(Path.cwd(), **kwargs)
    except Exception as err:  # pylint: disable=broad-except
        env = kwargs.get("env")
        _handle_exception(
            f"Unable to load Kedro context with environment `{env}`. "
            f"Make sure it exists in the project configuration.\nError: {err}"
        )


@click.group()
def project_group():
    """Collection of project commands."""


@forward_command(project_group, forward_help=True)
def test(args):
    """Run the test suite."""
    try:
        # pylint: disable=import-outside-toplevel, unused-import
        import pytest  # noqa
    except ImportError:
        context = _load_project_context()
        source_path = get_source_dir(context.project_path)
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="pytest", src=str(source_path))
        )
    else:
        python_call("pytest", args)


@project_group.command()
@click.option("-c", "--check-only", is_flag=True, help=LINT_CHECK_ONLY_HELP)
@click.argument("files", type=click.Path(exists=True), nargs=-1)
def lint(files, check_only):
    """Run flake8, isort and (on Python >=3.6) black."""
    context = _load_project_context()
    source_path = get_source_dir(context.project_path)
    files = files or (
        str(source_path / "tests"),
        str(source_path / context.package_name),
    )

    try:
        # pylint: disable=import-outside-toplevel, unused-import
        import flake8  # noqa
        import isort  # noqa
        import black  # noqa
    except ImportError as exc:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module=exc.name, src=str(source_path))
        )

    python_call("black", ("--check",) + files if check_only else files)
    python_call("flake8", ("--max-line-length=88",) + files)

    check_flag = ("-c",) if check_only else ()
    python_call(
        "isort", (*check_flag, "-rc", "-tc", "-up", "-fgw=0", "-m=3", "-w=88") + files
    )


@project_group.command()
def install():
    """Install project dependencies from both requirements.txt
    and environment.yml (optional)."""
    # we cannot use `context.project_path` as in other commands since
    # context instantiation might break due to missing dependencies
    # we attempt to install here
    source_path = get_source_dir(Path.cwd())

    if (source_path / "environment.yml").is_file():
        call(
            [
                "conda",
                "install",
                "--file",
                str(source_path / "environment.yml"),
                "--yes",
            ]
        )

    pip_command = ["install", "-U", "-r", str(source_path / "requirements.txt")]

    if os.name == "posix":
        python_call("pip", pip_command)
    else:
        command = [sys.executable, "-m", "pip"] + pip_command
        subprocess.Popen(command, creationflags=subprocess.CREATE_NEW_CONSOLE)


@forward_command(project_group, forward_help=True)
@env_option
def ipython(env, args):
    """Open IPython with project specific variables loaded."""
    context = _load_project_context(env=env)
    os.environ["IPYTHONDIR"] = str(context.project_path / ".ipython")
    if env:
        os.environ["KEDRO_ENV"] = env
    if "-h" not in args and "--help" not in args:
        ipython_message()
    call(["ipython"] + list(args))


@project_group.command()
def package():
    """Package the project as a Python egg and wheel."""
    context = _load_project_context()
    source_path = get_source_dir(context.project_path)
    call(
        [sys.executable, "setup.py", "clean", "--all", "bdist_egg"],
        cwd=str(source_path),
    )
    call(
        [sys.executable, "setup.py", "clean", "--all", "bdist_wheel"],
        cwd=str(source_path),
    )


@project_group.command("build-docs")
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
    context = _load_project_context()
    source_path = get_source_dir(context.project_path)
    python_call("pip", ["install", str(source_path / "[docs]")])
    python_call("pip", ["install", "-r", str(source_path / "requirements.txt")])
    python_call("ipykernel", ["install", "--user", f"--name={context.package_name}"])
    shutil.rmtree("docs/build", ignore_errors=True)
    call(
        [
            "sphinx-apidoc",
            "--module-first",
            "-o",
            "docs/source",
            str(source_path / context.package_name),
        ]
    )
    call(["sphinx-build", "-M", "html", "docs/source", "docs/build", "-a"])
    if open_docs:
        docs_page = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        secho(f"Opening {docs_page}")
        webbrowser.open(docs_page)


@project_group.command("build-reqs")
def build_reqs():
    """Build the project dependency requirements."""
    # we cannot use `context.project_path` as in other commands since
    # context instantiation might break due to missing dependencies
    # we attempt to install here
    source_path = get_source_dir(Path.cwd())
    requirements_path = source_path / "requirements.in"
    if not requirements_path.is_file():
        secho("No requirements.in found. Copying contents from requirements.txt...")
        contents = (source_path / "requirements.txt").read_text()
        requirements_path.write_text(contents)
    python_call("piptools", ["compile", str(requirements_path)])
    secho(
        (
            "Requirements built! Please update requirements.in "
            "if you'd like to make a change in your project's dependencies, "
            "and re-run build-reqs to generate the new requirements.txt."
        )
    )


@project_group.command("activate-nbstripout")
def activate_nbstripout():
    """Install the nbstripout git hook to automatically clean notebooks."""
    context = _load_project_context()
    source_path = get_source_dir(context.project_path)
    secho(
        (
            "Notebook output cells will be automatically cleared before committing"
            " to git."
        ),
        fg="yellow",
    )

    try:
        # pylint: disable=import-outside-toplevel, unused-import
        import nbstripout  # noqa
    except ImportError:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="nbstripout", src=str(source_path))
        )

    try:
        res = subprocess.run(  # pylint: disable=subprocess-run-check
            ["git", "rev-parse", "--git-dir"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if res.returncode:
            raise KedroCliError("Not a git repository. Run `git init` first.")
    except FileNotFoundError:
        raise KedroCliError("Git executable not found. Install Git first.")

    call(["nbstripout", "--install"])
