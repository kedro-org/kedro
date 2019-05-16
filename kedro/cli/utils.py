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

"""Utilities for use with click."""

import re
import shlex
import subprocess
import sys
from itertools import chain
from pathlib import Path
from typing import List, Tuple, Union

import click
from click import ClickException, style

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])


def call(cmd, **kwargs):  # pragma: no cover
    """Run a subprocess command and exit if it fails."""
    print(" ".join(shlex.quote(c) for c in cmd))
    res = subprocess.run(cmd, **kwargs).returncode
    if res:
        sys.exit(res)


def python_call(module, arguments, **kwargs):  # pragma: no cover
    """Run a subprocess command that invokes a Python module."""
    call([sys.executable, "-m", module] + list(arguments), **kwargs)


def forward_command(group, name=None, forward_help=False):
    """A command that receives the rest of the command line as 'args'."""

    def wrapit(func):
        func = click.argument("args", nargs=-1, type=click.UNPROCESSED)(func)
        func = group.command(
            name=name,
            context_settings=dict(
                ignore_unknown_options=True,
                help_option_names=[] if forward_help else ["-h", "--help"],
            ),
        )(func)
        return func

    return wrapit


class CommandCollection(click.CommandCollection):
    """Modified from the Click one to still run the source groups function."""

    def __init__(self, *groups: Tuple[str, List[click.core.Group]]):
        self.groups = groups
        sources = list(chain.from_iterable(groups for title, groups in groups))
        help_strs = [source.help for source in sources if source.help]
        super().__init__(
            sources=sources,
            help="\n\n".join(help_strs),
            context_settings=CONTEXT_SETTINGS,
        )
        self.params = sources[0].params
        self.callback = sources[0].callback

    def format_commands(
        self, ctx: click.core.Context, formatter: click.formatting.HelpFormatter
    ):
        for title, groups in self.groups:
            for group in groups:
                formatter.write(
                    click.style("\n{} from {}".format(title, group.name), fg="green")
                )
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
    if isinstance(reqs_path, str):
        reqs_path = Path(reqs_path)
    reqs_path = reqs_path.absolute()
    if not reqs_path.is_file():
        raise KedroCliError(
            "Given path `{0}` is not a regular file.".format(str(reqs_path))
        )

    pattern = re.compile(package_name + r"([^\w]|$)")
    with open(str(reqs_path), "r") as reqs_file:
        for req_line in reqs_file:
            req_line = req_line.strip()
            if pattern.search(req_line):
                return req_line
    msg = "Cannot find `{0}` package in `{1}`.".format(package_name, str(reqs_path))
    raise KedroCliError(msg)


class KedroCliError(ClickException):
    """Exceptions generated from the Kedro CLI.

    Users should pass an appropriate message at the constructor.
    """

    def format_message(self):
        return style(self.message, fg="red")  # pragma: no cover
