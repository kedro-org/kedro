"""A collection of helper functions to integrate with Jupyter/IPython
and CLI commands for working with Kedro catalog.
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from collections import Counter
from glob import iglob
from pathlib import Path
from typing import Any
from warnings import warn

import click
from click import secho

from kedro.framework.cli.utils import (
    KedroCliError,
    _check_module_importable,
    command_with_verbosity,
    env_option,
    forward_command,
    python_call,
)
from kedro.framework.project import validate_settings
from kedro.framework.startup import ProjectMetadata

CONVERT_ALL_HELP = """Extract the nodes from all notebooks in the Kedro project directory,
including sub-folders."""

OVERWRITE_HELP = """If Python file already exists for the equivalent notebook,
overwrite its contents."""


class JupyterCommandGroup(click.Group):
    """A custom class for ordering the `kedro jupyter` command groups"""

    def list_commands(self, ctx):
        """List commands according to a custom order"""
        return ["setup", "notebook", "lab", "convert"]


# noqa: missing-function-docstring
@click.group(name="Kedro")
def jupyter_cli():  # pragma: no cover
    pass


@jupyter_cli.group(cls=JupyterCommandGroup)
def jupyter():
    """Open Jupyter Notebook / Lab with project specific variables loaded, or
    convert notebooks into Kedro code.
    """


@forward_command(jupyter, "setup", forward_help=True)
@click.pass_obj  # this will pass the metadata as first argument
def setup(metadata: ProjectMetadata, args, **kwargs):  # noqa: unused-argument
    """Initialise the Jupyter Kernel for a kedro project."""
    _check_module_importable("ipykernel")
    validate_settings()

    kernel_name = f"kedro_{metadata.package_name}"
    kernel_path = _create_kernel(kernel_name, f"Kedro ({metadata.package_name})")
    click.secho(f"\nThe kernel has been created successfully at {kernel_path}")


@forward_command(jupyter, "notebook", forward_help=True)
@env_option
@click.pass_obj  # this will pass the metadata as first argument
def jupyter_notebook(
    metadata: ProjectMetadata,
    env,
    args,
    **kwargs,
):  # noqa: unused-argument
    """Open Jupyter Notebook with project specific variables loaded."""
    _check_module_importable("notebook")
    validate_settings()

    kernel_name = f"kedro_{metadata.package_name}"
    _create_kernel(kernel_name, f"Kedro ({metadata.package_name})")

    if env:
        os.environ["KEDRO_ENV"] = env

    python_call(
        "jupyter",
        ["notebook", f"--MultiKernelManager.default_kernel_name={kernel_name}"]
        + list(args),
    )


@forward_command(jupyter, "lab", forward_help=True)
@env_option
@click.pass_obj  # this will pass the metadata as first argument
def jupyter_lab(
    metadata: ProjectMetadata,
    env,
    args,
    **kwargs,
):  # noqa: unused-argument
    """Open Jupyter Lab with project specific variables loaded."""
    _check_module_importable("jupyterlab")
    validate_settings()

    kernel_name = f"kedro_{metadata.package_name}"
    _create_kernel(kernel_name, f"Kedro ({metadata.package_name})")

    if env:
        os.environ["KEDRO_ENV"] = env

    python_call(
        "jupyter",
        ["lab", f"--MultiKernelManager.default_kernel_name={kernel_name}"] + list(args),
    )


def _create_kernel(kernel_name: str, display_name: str) -> str:
    """Creates an IPython kernel for the kedro project. If one with the same kernel_name
    exists already it will be replaced.

    Installs the default IPython kernel (which points towards `sys.executable`)
    and customises it to make the launch command load the kedro extension.
    This is equivalent to the method recommended for creating a custom IPython kernel
    on the CLI: https://ipython.readthedocs.io/en/stable/install/kernel_install.html.

    On linux this creates a directory ~/.local/share/jupyter/kernels/{kernel_name}
    containing kernel.json, logo-32x32.png, logo-64x64.png and logo-svg.svg. An example kernel.json
    looks as follows:

    {
     "argv": [
      "/Users/antony_milne/miniconda3/envs/spaceflights/bin/python",
      "-m",
      "ipykernel_launcher",
      "-f",
      "{connection_file}",
      "--ext",
      "kedro.ipython"
     ],
     "display_name": "Kedro (spaceflights)",
     "language": "python",
     "metadata": {
      "debugger": false
     }
    }

    Args:
        kernel_name: Name of the kernel to create.
        display_name: Kernel name as it is displayed in the UI.

    Returns:
        String of the path of the created kernel.

    Raises:
        KedroCliError: When kernel cannot be setup.
    """
    # These packages are required by jupyter lab and notebook, which we have already
    # checked are importable, so we don't run _check_module_importable on them.
    # noqa: import-outside-toplevel
    from ipykernel.kernelspec import install

    try:
        # Install with user=True rather than system-wide to minimise footprint and
        # ensure that we have permissions to write there. Under the hood this calls
        # jupyter_client.KernelSpecManager.install_kernel_spec, which automatically
        # removes an old kernel spec if it already exists.
        kernel_path = install(
            user=True,
            kernel_name=kernel_name,
            display_name=display_name,
        )

        kernel_json = Path(kernel_path) / "kernel.json"
        kernel_spec = json.loads(kernel_json.read_text(encoding="utf-8"))
        kernel_spec["argv"].extend(["--ext", "kedro.ipython"])
        # indent=1 is to match the default ipykernel style (see
        # ipykernel.write_kernel_spec).
        kernel_json.write_text(json.dumps(kernel_spec, indent=1), encoding="utf-8")

        kedro_ipython_dir = Path(__file__).parents[2] / "ipython"
        shutil.copy(kedro_ipython_dir / "logo-32x32.png", kernel_path)
        shutil.copy(kedro_ipython_dir / "logo-64x64.png", kernel_path)
        shutil.copy(kedro_ipython_dir / "logo-svg.svg", kernel_path)
    except Exception as exc:
        raise KedroCliError(
            f"Cannot setup kedro kernel for Jupyter.\nError: {exc}"
        ) from exc
    return kernel_path


@command_with_verbosity(jupyter, "convert")
@click.option("--all", "-a", "all_flag", is_flag=True, help=CONVERT_ALL_HELP)
@click.option("-y", "overwrite_flag", is_flag=True, help=OVERWRITE_HELP)
@click.argument(
    "filepath",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=False,
    nargs=-1,
)
@env_option
@click.pass_obj  # this will pass the metadata as first argument
def convert_notebook(
    metadata: ProjectMetadata, all_flag, overwrite_flag, filepath, env, **kwargs
):  # noqa: unused-argument, too-many-locals
    """Convert selected or all notebooks found in a Kedro project
    to Kedro code, by exporting code from the appropriately-tagged cells:
    Cells tagged as `node` will be copied over to a Python file matching
    the name of the notebook, under `<source_dir>/<package_name>/nodes`.
    *Note*: Make sure your notebooks have unique names!
    FILEPATH: Path(s) to exact notebook file(s) to be converted. Both
    relative and absolute paths are accepted.
    Should not be provided if --all flag is already present. (DEPRECATED)
    """

    deprecation_message = (
        "DeprecationWarning: Command 'kedro jupyter convert' is deprecated and "
        "will not be available from Kedro 0.19.0."
    )
    click.secho(deprecation_message, fg="red")

    project_path = metadata.project_path
    source_path = metadata.source_dir
    package_name = metadata.package_name

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

    secho("Done!", color="green")  # type: ignore


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


def _append_source_code(cell: dict[str, Any], path: Path) -> None:
    source_code = "".join(cell["source"]).strip() + "\n"
    with path.open(mode="a") as file_:
        file_.write(source_code)
