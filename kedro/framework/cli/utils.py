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

"""Utilities for use with click."""
import difflib
import os
import re
import shlex
import shutil
import subprocess
import sys
import textwrap
import traceback
import warnings
from contextlib import contextmanager
from importlib import import_module
from itertools import chain
from pathlib import Path
from typing import Iterable, List, Sequence, Tuple, Union

import click

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])
MAX_SUGGESTIONS = 3
CUTOFF = 0.5

ENV_HELP = "Kedro configuration environment name. Defaults to `local`."


def call(cmd: List[str], **kwargs):  # pragma: no cover
    """Run a subprocess command and raise if it fails.

    Args:
        cmd: List of command parts.
        **kwargs: Optional keyword arguments passed to `subprocess.run`.

    Raises:
        click.exceptions.Exit: If `subprocess.run` returns non-zero code.
    """
    click.echo(" ".join(shlex.quote(c) for c in cmd))
    # pylint: disable=subprocess-run-check
    code = subprocess.run(cmd, **kwargs).returncode
    if code:
        raise click.exceptions.Exit(code=code)


def python_call(module: str, arguments: Iterable[str], **kwargs):  # pragma: no cover
    """Run a subprocess command that invokes a Python module."""
    call([sys.executable, "-m", module] + list(arguments), **kwargs)


def find_stylesheets() -> Iterable[str]:  # pragma: no cover
    """Fetch all stylesheets used in the official Kedro documentation"""
    css_path = Path(__file__).resolve().parents[1] / "html" / "_static" / "css"
    return (
        str(css_path / "copybutton.css"),
        str(css_path / "qb1-sphinx-rtd.css"),
        str(css_path / "theme-overrides.css"),
    )


def forward_command(group, name=None, forward_help=False):
    """A command that receives the rest of the command line as 'args'."""

    def wrapit(func):
        func = click.argument("args", nargs=-1, type=click.UNPROCESSED)(func)
        func = command_with_verbosity(
            group,
            name=name,
            context_settings=dict(
                ignore_unknown_options=True,
                help_option_names=[] if forward_help else ["-h", "--help"],
            ),
        )(func)
        return func

    return wrapit


def _suggest_cli_command(
    original_command_name: str, existing_command_names: Iterable[str]
) -> str:
    matches = difflib.get_close_matches(
        original_command_name, existing_command_names, MAX_SUGGESTIONS, CUTOFF
    )

    if not matches:
        return ""

    if len(matches) == 1:
        suggestion = "\n\nDid you mean this?"
    else:
        suggestion = "\n\nDid you mean one of these?\n"
    suggestion += textwrap.indent("\n".join(matches), " " * 4)  # type: ignore
    return suggestion


class CommandCollection(click.CommandCollection):
    """Modified from the Click one to still run the source groups function."""

    def __init__(self, *groups: Tuple[str, Sequence[click.core.MultiCommand]]):
        self.groups = groups
        sources = list(chain.from_iterable(cli_groups for title, cli_groups in groups))
        help_strs = [source.help for source in sources if source.help]
        super().__init__(
            sources=sources,
            help="\n\n".join(help_strs),
            context_settings=CONTEXT_SETTINGS,
        )
        self.params = sources[0].params
        self.callback = sources[0].callback

    def resolve_command(self, ctx: click.core.Context, args: List):
        try:
            return super().resolve_command(ctx, args)
        except click.exceptions.UsageError as exc:
            original_command_name = click.utils.make_str(args[0])
            existing_command_names = self.list_commands(ctx)
            exc.message += _suggest_cli_command(
                original_command_name, existing_command_names
            )
            raise

    def format_commands(
        self, ctx: click.core.Context, formatter: click.formatting.HelpFormatter
    ):
        for title, groups in self.groups:
            for group in groups:
                formatter.write(click.style(f"\n{title} from {group.name}", fg="green"))
                group.format_commands(ctx, formatter)


def get_pkg_version(reqs_path: (Union[str, Path]), package_name: str) -> str:
    """Get package version from requirements.txt.

    Args:
        reqs_path: Path to requirements.txt file.
        package_name: Package to search for.

    Returns:
        Package and its version as specified in requirements.txt.

    Raises:
        KedroCliError: If the file specified in ``reqs_path`` does not exist
            or ``package_name`` was not found in that file.
    """
    reqs_path = Path(reqs_path).absolute()
    if not reqs_path.is_file():
        raise KedroCliError(f"Given path `{reqs_path}` is not a regular file.")

    pattern = re.compile(package_name + r"([^\w]|$)")
    with reqs_path.open("r") as reqs_file:
        for req_line in reqs_file:
            req_line = req_line.strip()
            if pattern.search(req_line):
                return req_line

    raise KedroCliError(f"Cannot find `{package_name}` package in `{reqs_path}`.")


def _update_verbose_flag(ctx, param, value):  # pylint: disable=unused-argument
    KedroCliError.VERBOSE_ERROR = value


def _click_verbose(func):
    """Click option for enabling verbose mode.
    """
    return click.option(
        "--verbose",
        "-v",
        is_flag=True,
        callback=_update_verbose_flag,
        help="See extensive logging and error stack traces.",
    )(func)


def command_with_verbosity(group: click.core.Group, *args, **kwargs):
    """Custom command decorator with verbose flag added.
    """

    def decorator(func):
        func = _click_verbose(func)
        func = group.command(*args, **kwargs)(func)
        return func

    return decorator


class KedroCliError(click.exceptions.ClickException):
    """Exceptions generated from the Kedro CLI.

    Users should pass an appropriate message at the constructor.
    """

    VERBOSE_ERROR = False

    def show(self, file=None):
        if file is None:
            # pylint: disable=protected-access
            file = click._compat.get_text_stderr()
        if self.VERBOSE_ERROR:
            click.secho(traceback.format_exc(), nl=False, fg="yellow")
        else:
            etype, value, _ = sys.exc_info()
            formatted_exception = "".join(traceback.format_exception_only(etype, value))
            click.secho(
                f"{formatted_exception}Run with --verbose to see the full exception",
                fg="yellow",
            )
        click.secho(f"Error: {self.message}", fg="red", file=file)


def _clean_pycache(path: Path):
    """Recursively clean all __pycache__ folders from `path`.

    Args:
        path: Existing local directory to clean __pycache__ folders from.
    """
    to_delete = [each.resolve() for each in path.rglob("__pycache__")]

    for each in to_delete:
        shutil.rmtree(each, ignore_errors=True)


def split_string(ctx, param, value):  # pylint: disable=unused-argument
    """Split string by comma."""
    return [item.strip() for item in value.split(",") if item.strip()]


def env_option(func_=None, **kwargs):
    """Add `--env` CLI option to a function."""
    default_args = dict(type=str, default=None, help=ENV_HELP)
    kwargs = {**default_args, **kwargs}
    opt = click.option("--env", "-e", **kwargs)
    return opt(func_) if func_ else opt


def ipython_message(all_kernels=True):
    """Show a message saying how we have configured the IPython env."""
    ipy_vars = ["startup_error", "context"]
    click.secho("-" * 79, fg="cyan")
    click.secho("Starting a Kedro session with the following variables in scope")
    click.secho(", ".join(ipy_vars), fg="green")
    line_magic = click.style("%reload_kedro", fg="green")
    click.secho(f"Use the line magic {line_magic} to refresh them")
    click.secho("or to see the error message if they are undefined")

    if not all_kernels:
        click.secho("The choice of kernels is limited to the default one.", fg="yellow")
        click.secho("(restart with --all-kernels to get access to others)", fg="yellow")

    click.secho("-" * 79, fg="cyan")


@contextmanager
def _filter_deprecation_warnings():
    """Temporarily suppress all DeprecationWarnings."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        yield


def _check_module_importable(module_name: str) -> None:
    try:
        import_module(module_name)
    except ImportError as exc:
        raise KedroCliError(
            f"Module `{module_name}` not found. Make sure to install required project "
            f"dependencies by running the `kedro install` command first."
        ) from exc


def _validate_source_path(source_path: Path, project_path: Path):
    """Validate the source path exists and is relative to the project path.

    Args:
        source_path: Absolute source path.
        project_path: Path to the Kedro project.

    Raises:
        ValueError: If source_path is not relative to project_path.
        NotADirectoryError: If source_path does not exist.
    """
    try:
        source_path.relative_to(project_path)
    except ValueError as exc:
        raise ValueError(
            f"Source path '{source_path}' has to be relative to "
            f"your project root '{project_path}'."
        ) from exc
    if not source_path.exists():
        raise NotADirectoryError(f"Source path '{source_path}' cannot be found.")


def _add_src_to_path(source_dir: Path, project_path: Path):
    _validate_source_path(source_dir, project_path)

    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))
    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = str(source_dir)
