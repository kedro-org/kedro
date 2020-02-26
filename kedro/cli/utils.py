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

"""Utilities for use with click."""
import json
import re
import shlex
import subprocess
import sys
from itertools import chain
from pathlib import Path
from typing import Any, Dict, Iterable, List, Sequence, Tuple, Union
from warnings import warn

import click
from click import ClickException, style

CONTEXT_SETTINGS = dict(help_option_names=["-h", "--help"])

NODE_TAG = "node"


def call(cmd: List[str], **kwargs):  # pragma: no cover
    """Run a subprocess command and exit if it fails."""
    print(" ".join(shlex.quote(c) for c in cmd))
    # pylint: disable=subprocess-run-check
    res = subprocess.run(cmd, **kwargs).returncode
    if res:
        sys.exit(res)


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


def _append_source_code(cell: Dict[str, Any], path: Path) -> None:
    source_code = "".join(cell["source"]).strip() + "\n"
    with path.open(mode="a") as file_:
        file_.write(source_code)


def export_nodes(filepath: Path, output_path: Path) -> None:
    """Copy code from Jupyter cells into nodes in src/<package_name>/nodes/,
    under filename with same name as notebook.

    Args:
        filepath: Path to Jupyter notebook file
        output_path: Path where notebook cells' source code will be exported
    Raises:
        KedroCliError: When provided a filepath that cannot be read as a
            Jupyer notebook and loaded into json format.
    """
    try:
        content = json.loads(filepath.read_text())
    except json.JSONDecodeError:
        raise KedroCliError(
            "Provided filepath is not a Jupyter notebook: {}".format(filepath)
        )

    cells = [
        cell
        for cell in content["cells"]
        if cell["cell_type"] == "code" and NODE_TAG in cell["metadata"].get("tags", {})
    ]

    if cells:
        output_path.write_text("")
        for cell in cells:
            _append_source_code(cell, output_path)
    else:
        warn("Skipping notebook '{}' - no nodes to export.".format(filepath))


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

    def __init__(self, *groups: Tuple[str, Sequence[click.core.MultiCommand]]):
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
