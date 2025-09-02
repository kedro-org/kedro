"""A collection of CLI commands for working with Kedro project."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click

from kedro.framework.cli.utils import (
    _check_module_importable,
    _config_file_callback,
    _split_load_versions,
    _split_params,
    call,
    env_option,
    forward_command,
    namespace_deprecation_warning,
    split_node_names,
    split_string,
    validate_conf_source,
)
from kedro.framework.project import settings
from kedro.framework.session import KedroSession
from kedro.utils import load_obj

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata

NO_DEPENDENCY_MESSAGE = """{module} is not installed. Please make sure {module} is in
requirements.txt and run 'pip install -r requirements.txt'."""
LINT_CHECK_ONLY_HELP = """Check the files for style guide violations, unsorted /
unformatted imports, and unblackened Python code without modifying the files."""
OPEN_ARG_HELP = """Open the documentation in your default browser after building."""
FROM_INPUTS_HELP = (
    """A list of dataset names which should be used as a starting point."""
)
TO_OUTPUTS_HELP = """A list of dataset names which should be used as an end point."""
FROM_NODES_HELP = """A list of node names which should be used as a starting point."""
TO_NODES_HELP = """A list of node names which should be used as an end point."""
NODE_ARG_HELP = """Run only nodes with specified names."""
RUNNER_ARG_HELP = """Specify a runner that you want to run the pipeline with.
Available runners: 'SequentialRunner', 'ParallelRunner' and 'ThreadRunner'."""
ASYNC_ARG_HELP = """Load and save node inputs and outputs asynchronously
with threads. If not specified, load and save datasets synchronously."""
TAG_ARG_HELP = """Construct the pipeline using only nodes which have this tag
attached. Option can be used multiple times, what results in a
pipeline constructed from nodes having any of those tags."""
LOAD_VERSION_HELP = """Specify a particular dataset version (timestamp) for loading."""
CONFIG_FILE_HELP = """Specify a YAML configuration file to load the run
command arguments from. If command line arguments are provided, they will
override the loaded ones."""
PIPELINE_ARG_HELP = """Name of the registered pipeline to run.
If not set, the '__default__' pipeline is run."""
NAMESPACE_ARG_HELP = """Name of the node namespace to run."""
PARAMS_ARG_HELP = """Specify extra parameters that you want to pass
to the context initialiser. Items must be separated by comma, keys - by colon or equals sign,
example: param1=value1,param2=value2. Each parameter is split by the first comma,
so parameter values are allowed to contain colons, parameter keys are not.
To pass a nested dictionary as parameter, separate keys by '.', example:
param_group.param1:value1."""
INPUT_FILE_HELP = """Name of the requirements file to compile."""
OUTPUT_FILE_HELP = """Name of the file where compiled requirements should be stored."""
CONF_SOURCE_HELP = """Path of a directory where project configuration is stored."""


@click.group(name="Kedro")
def project_group() -> None:  # pragma: no cover
    pass


@forward_command(project_group, forward_help=True)
@env_option
@click.pass_obj  # this will pass the metadata as first argument
def ipython(metadata: ProjectMetadata, /, env: str, args: Any, **kwargs: Any) -> None:
    """Open IPython with project specific variables loaded."""
    _check_module_importable("IPython")

    if env:
        os.environ["KEDRO_ENV"] = env
    call(["ipython", "--ext", "kedro.ipython", *list(args)])


@project_group.command()
@click.pass_obj  # this will pass the metadata as first argument
def package(metadata: ProjectMetadata) -> None:
    """Package the project as a Python wheel."""
    # Even if the user decides for the older setup.py on purpose,
    # pyproject.toml is needed for Kedro metadata
    if (metadata.project_path / "pyproject.toml").is_file():
        metadata_dir = metadata.project_path
        destination_dir = "dist"
    else:
        # Assume it's an old Kedro project, packaging metadata was under src
        # (could be pyproject.toml or setup.py, it's not important)
        metadata_dir = metadata.source_dir
        destination_dir = "../dist"

    call(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            destination_dir,
        ],
        cwd=str(metadata_dir),
    )

    directory = (
        str(Path(settings.CONF_SOURCE).parent)
        if settings.CONF_SOURCE != "conf"
        else metadata.project_path
    )
    call(
        [
            "tar",
            "--exclude=local/*.yml",
            "-czf",
            f"dist/conf-{metadata.package_name}.tar.gz",
            f"--directory={directory}",
            str(Path(settings.CONF_SOURCE).stem),
        ]
    )


@project_group.command()
@click.option(
    "--from-inputs",
    type=str,
    default="",
    help=FROM_INPUTS_HELP,
    callback=split_string,
)
@click.option(
    "--to-outputs",
    type=str,
    default="",
    help=TO_OUTPUTS_HELP,
    callback=split_string,
)
@click.option(
    "--from-nodes",
    type=str,
    default="",
    help=FROM_NODES_HELP,
    callback=split_node_names,
)
@click.option(
    "--to-nodes", type=str, default="", help=TO_NODES_HELP, callback=split_node_names
)
@click.option(
    "--nodes",
    "-n",
    "node_names",
    type=str,
    default="",
    help=NODE_ARG_HELP,
    callback=split_node_names,
)
@click.option("--runner", "-r", type=str, default=None, help=RUNNER_ARG_HELP)
@click.option("--async", "is_async", is_flag=True, help=ASYNC_ARG_HELP)
@env_option
@click.option(
    "--tags",
    "-t",
    type=str,
    default="",
    help=TAG_ARG_HELP,
    callback=split_string,
)
@click.option(
    "--load-versions",
    "-lv",
    type=str,
    default="",
    help=LOAD_VERSION_HELP,
    callback=_split_load_versions,
)
@click.option("--pipeline", "-p", type=str, default=None, help=PIPELINE_ARG_HELP)
@click.option(
    "--namespace",
    "-ns",
    type=str,
    default=None,
    help=NAMESPACE_ARG_HELP,
)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=CONFIG_FILE_HELP,
    callback=_config_file_callback,
)
@click.option(
    "--conf-source",
    callback=validate_conf_source,
    help=CONF_SOURCE_HELP,
)
@click.option(
    "--params",
    type=click.UNPROCESSED,
    default="",
    help=PARAMS_ARG_HELP,
    callback=_split_params,
)
def run(  # noqa: PLR0913
    tags: str,
    env: str,
    runner: str,
    is_async: bool,
    node_names: str,
    to_nodes: str,
    from_nodes: str,
    from_inputs: str,
    to_outputs: str,
    load_versions: dict[str, str] | None,
    pipeline: str,
    config: str,
    conf_source: str,
    params: dict[str, Any],
    namespace: str,
) -> dict[str, Any]:
    """Run the pipeline."""

    runner_obj = load_obj(runner or "SequentialRunner", "kedro.runner")
    tuple_tags = tuple(tags)
    tuple_node_names = tuple(node_names)

    if namespace:
        namespace_deprecation_warning()

    with KedroSession.create(
        env=env, conf_source=conf_source, extra_params=params
    ) as session:
        return session.run(
            tags=tuple_tags,
            runner=runner_obj(is_async=is_async),
            node_names=tuple_node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_versions,
            pipeline_name=pipeline,
            namespace=namespace,
        )
