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

"""A collection of helper functions to integrate with Jupyter/IPython
and CLI commands for working with Kedro catalog.
"""
import json
import os
import re
import sys
from collections import Counter
from glob import iglob
from pathlib import Path
from typing import Any, Dict, Iterable, List
from warnings import warn

import click
from click import secho
from jupyter_client.kernelspec import NATIVE_KERNEL_NAME, KernelSpecManager
from traitlets import Unicode

from kedro.framework.cli import load_entry_points
from kedro.framework.cli.cli import _handle_exception
from kedro.framework.cli.utils import (
    KedroCliError,
    _check_module_importable,
    env_option,
    forward_command,
    ipython_message,
    python_call,
)
from kedro.framework.context import get_static_project_data, load_context

JUPYTER_IP_HELP = "IP address of the Jupyter server."
JUPYTER_ALL_KERNELS_HELP = "Display all available Python kernels."
JUPYTER_IDLE_TIMEOUT_HELP = """When a notebook is closed, Jupyter server will
terminate its kernel after so many seconds of inactivity. This does not affect
any open notebooks."""

CONVERT_ALL_HELP = """Extract the nodes from all notebooks in the Kedro project directory,
including sub-folders."""

OVERWRITE_HELP = """If Python file already exists for the equivalent notebook,
overwrite its contents."""


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


def collect_line_magic():
    """Interface function for collecting line magic functions from plugin entry points.
    """
    return load_entry_points("line_magic")


class SingleKernelSpecManager(KernelSpecManager):
    """A custom KernelSpec manager to be used by Kedro projects.
    It limits the kernels to the default one only,
    to make it less confusing for users, and gives it a sensible name.
    """

    default_kernel_name = Unicode(
        "Kedro", config=True, help="Alternative name for the default kernel"
    )
    whitelist = [NATIVE_KERNEL_NAME]

    def get_kernel_spec(self, kernel_name):
        """
        This function will only be called by Jupyter to get a KernelSpec
        for the default kernel.
        We replace the name by something sensible here.
        """
        kernelspec = super().get_kernel_spec(kernel_name)

        if kernel_name == NATIVE_KERNEL_NAME:
            kernelspec.display_name = self.default_kernel_name

        return kernelspec


def _update_ipython_dir(project_path: Path) -> None:
    os.environ["IPYTHONDIR"] = str(project_path / ".ipython")


@click.group()
def jupyter():
    """Open Jupyter Notebook / Lab with project specific variables loaded, or
    convert notebooks into Kedro code.
    """


@forward_command(jupyter, "notebook", forward_help=True)
@click.option(
    "--ip",
    "ip_address",
    type=str,
    default="127.0.0.1",
    help="IP address of the Jupyter server.",
)
@click.option(
    "--all-kernels", is_flag=True, default=False, help=JUPYTER_ALL_KERNELS_HELP
)
@click.option("--idle-timeout", type=int, default=30, help=JUPYTER_IDLE_TIMEOUT_HELP)
@env_option
def jupyter_notebook(ip_address, all_kernels, env, idle_timeout, args):
    """Open Jupyter Notebook with project specific variables loaded."""
    context = _load_project_context(env=env)
    _check_module_importable("jupyter_core")

    if "-h" not in args and "--help" not in args:
        ipython_message(all_kernels)

    _update_ipython_dir(context.project_path)
    arguments = _build_jupyter_command(
        "notebook",
        ip_address=ip_address,
        all_kernels=all_kernels,
        args=args,
        idle_timeout=idle_timeout,
        project_name=context.project_name,
    )

    python_call_kwargs = _build_jupyter_env(env)
    python_call("jupyter", arguments, **python_call_kwargs)


@forward_command(jupyter, "lab", forward_help=True)
@click.option("--ip", "ip_address", type=str, default="127.0.0.1", help=JUPYTER_IP_HELP)
@click.option(
    "--all-kernels", is_flag=True, default=False, help=JUPYTER_ALL_KERNELS_HELP
)
@click.option("--idle-timeout", type=int, default=30, help=JUPYTER_IDLE_TIMEOUT_HELP)
@env_option
def jupyter_lab(ip_address, all_kernels, env, idle_timeout, args):
    """Open Jupyter Lab with project specific variables loaded."""
    context = _load_project_context(env=env)
    _check_module_importable("jupyter_core")

    if "-h" not in args and "--help" not in args:
        ipython_message(all_kernels)

    _update_ipython_dir(context.project_path)
    arguments = _build_jupyter_command(
        "lab",
        ip_address=ip_address,
        all_kernels=all_kernels,
        args=args,
        idle_timeout=idle_timeout,
        project_name=context.project_name,
    )

    python_call_kwargs = _build_jupyter_env(env)
    python_call("jupyter", arguments, **python_call_kwargs)


@jupyter.command("convert")
@click.option("--all", "all_flag", is_flag=True, help=CONVERT_ALL_HELP)
@click.option("-y", "overwrite_flag", is_flag=True, help=OVERWRITE_HELP)
@click.argument(
    "filepath",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=False,
    nargs=-1,
)
@env_option
def convert_notebook(  # pylint: disable=unused-argument,too-many-locals
    all_flag, overwrite_flag, filepath, env
):
    """Convert selected or all notebooks found in a Kedro project
    to Kedro code, by exporting code from the appropriately-tagged cells:
    Cells tagged as `node` will be copied over to a Python file matching
    the name of the notebook, under `<source_dir>/<package_name>/nodes`.
    *Note*: Make sure your notebooks have unique names!
    FILEPATH: Path(s) to exact notebook file(s) to be converted. Both
    relative and absolute paths are accepted.
    Should not be provided if --all flag is already present.
    """
    project_path = Path.cwd()
    static_data = get_static_project_data(project_path)
    source_path = static_data["source_dir"]
    package_name = (
        static_data.get("package_name") or _load_project_context().package_name
    )

    _update_ipython_dir(project_path)

    if not filepath and not all_flag:
        secho(
            "Please specify a notebook filepath "
            "or add '--all' to convert all notebooks."
        )
        sys.exit(1)

    if all_flag:
        # pathlib glob does not ignore hidden directories,
        # whereas Python glob does, which is more useful in
        # ensuring checkpoints will not be included
        pattern = project_path / "**" / "*.ipynb"
        notebooks = sorted(Path(p) for p in iglob(str(pattern), recursive=True))
    else:
        notebooks = [Path(f) for f in filepath]

    counter = Counter(n.stem for n in notebooks)
    non_unique_names = [name for name, counts in counter.items() if counts > 1]
    if non_unique_names:
        names = ", ".join(non_unique_names)
        raise KedroCliError(
            f"Found non-unique notebook names! Please rename the following: {names}"
        )

    output_dir = source_path / package_name / "nodes"
    if not output_dir.is_dir():
        output_dir.mkdir()
        (output_dir / "__init__.py").touch()

    for notebook in notebooks:
        secho(f"Converting notebook '{notebook}'...")
        output_path = output_dir / f"{notebook.stem}.py"

        if output_path.is_file():
            overwrite = overwrite_flag or click.confirm(
                f"Output file {output_path} already exists. Overwrite?", default=False
            )
            if overwrite:
                _export_nodes(notebook, output_path)
        else:
            _export_nodes(notebook, output_path)

    secho("Done!", color="green")


def _build_jupyter_command(  # pylint: disable=too-many-arguments
    base: str,
    ip_address: str,
    all_kernels: bool,
    args: Iterable[str],
    idle_timeout: int,
    project_name: str = "Kedro",
) -> List[str]:
    cmd = [
        base,
        "--ip",
        ip_address,
        f"--MappingKernelManager.cull_idle_timeout={idle_timeout}",
        f"--MappingKernelManager.cull_interval={idle_timeout}",
    ]

    if not all_kernels:
        kernel_name = re.sub(r"[^\w]+", "", project_name).strip() or "Kedro"

        cmd += [
            "--NotebookApp.kernel_spec_manager_class="
            "kedro.framework.cli.jupyter.SingleKernelSpecManager",
            f"--KernelSpecManager.default_kernel_name='{kernel_name}'",
        ]

    return cmd + list(args)


def _build_jupyter_env(kedro_env: str) -> Dict[str, Any]:
    """Build the environment dictionary that gets injected into the subprocess running
    Jupyter. Since the subprocess has access only to the environment variables passed
    in, we need to copy the current environment and add ``KEDRO_ENV``.
    """
    if not kedro_env:
        return {}
    jupyter_env = os.environ.copy()
    jupyter_env["KEDRO_ENV"] = kedro_env
    return {"env": jupyter_env}


def _export_nodes(filepath: Path, output_path: Path) -> None:
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
    except json.JSONDecodeError as exc:
        raise KedroCliError(
            f"Provided filepath is not a Jupyter notebook: {filepath}"
        ) from exc

    cells = [
        cell
        for cell in content["cells"]
        if cell["cell_type"] == "code" and "node" in cell["metadata"].get("tags", {})
    ]

    if cells:
        output_path.write_text("")
        for cell in cells:
            _append_source_code(cell, output_path)
    else:
        warn(f"Skipping notebook '{filepath}' - no nodes to export.")


def _append_source_code(cell: Dict[str, Any], path: Path) -> None:
    source_code = "".join(cell["source"]).strip() + "\n"
    with path.open(mode="a") as file_:
        file_.write(source_code)
