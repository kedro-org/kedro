"""A collection of CLI commands for working with Kedro project."""

import os
import sys
from pathlib import Path

import click

from kedro.framework.cli.utils import (
    _check_module_importable,
    _config_file_callback,
    _deprecate_options,
    _get_values_as_tuple,
    _reformat_load_versions,
    _split_load_versions,
    _split_params,
    call,
    env_option,
    forward_command,
    split_node_names,
    split_string,
)
from kedro.framework.project import settings
from kedro.framework.session import KedroSession
from kedro.framework.startup import ProjectMetadata
from kedro.utils import load_obj

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


# noqa: missing-function-docstring
@click.group(name="Kedro")
def project_group():  # pragma: no cover
    pass


@forward_command(project_group, forward_help=True)
@env_option
@click.pass_obj  # this will pass the metadata as first argument
def ipython(metadata: ProjectMetadata, env, args, **kwargs):  # noqa: unused-argument
    """Open IPython with project specific variables loaded."""
    _check_module_importable("IPython")

    if env:
        os.environ["KEDRO_ENV"] = env
    call(["ipython", "--ext", "kedro.ipython"] + list(args))


@project_group.command()
@click.pass_obj  # this will pass the metadata as first argument
def package(metadata: ProjectMetadata):
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
    "--node",
    "-n",
    "node_names",
    type=str,
    multiple=True,
    help=NODE_ARG_HELP,
    callback=_deprecate_options,
)
@click.option(
    "--nodes",
    "nodes_names",
    type=str,
    default="",
    help=NODE_ARG_HELP,
    callback=split_node_names,
)
@click.option("--runner", "-r", type=str, default=None, help=RUNNER_ARG_HELP)
@click.option("--async", "is_async", is_flag=True, help=ASYNC_ARG_HELP)
@env_option
@click.option(
    "--tag",
    "-t",
    type=str,
    multiple=True,
    help=TAG_ARG_HELP,
    callback=_deprecate_options,
)
@click.option(
    "--tags",
    type=str,
    default="",
    help=TAG_ARG_HELP,
    callback=split_string,
)
@click.option(
    "--load-version",
    "-lv",
    type=str,
    multiple=True,
    help=LOAD_VERSION_HELP,
    callback=_reformat_load_versions,
)
@click.option(
    "--load-versions",
    type=str,
    default="",
    help=LOAD_VERSION_HELP,
    callback=_split_load_versions,
)
@click.option("--pipeline", "-p", type=str, default=None, help=PIPELINE_ARG_HELP)
@click.option("--namespace", "-ns", type=str, default=None, help=NAMESPACE_ARG_HELP)
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    help=CONFIG_FILE_HELP,
    callback=_config_file_callback,
)
@click.option(
    "--conf-source",
    type=click.Path(exists=True, file_okay=True, resolve_path=True),
    help=CONF_SOURCE_HELP,
)
@click.option(
    "--params",
    type=click.UNPROCESSED,
    default="",
    help=PARAMS_ARG_HELP,
    callback=_split_params,
)
def run(  # noqa: too-many-arguments,unused-argument,too-many-locals
    tag,
    tags,
    env,
    runner,
    is_async,
    node_names,
    nodes_names,
    to_nodes,
    from_nodes,
    from_inputs,
    to_outputs,
    load_version,
    load_versions,
    pipeline,
    config,
    conf_source,
    params,
    namespace,
):
    """Run the pipeline."""

    runner = load_obj(runner or "SequentialRunner", "kedro.runner")

    tag = _get_values_as_tuple(tag)
    node_names = _get_values_as_tuple(node_names)

    # temporary duplicates for the plural flags
    tags = _get_values_as_tuple(tags)
    nodes_names = _get_values_as_tuple(nodes_names)

    tag = tag + tags
    node_names = node_names + nodes_names
    load_version = {**load_version, **load_versions}

    with KedroSession.create(
        env=env, conf_source=conf_source, extra_params=params
    ) as session:
        session.run(
            tags=tag,
            runner=runner(is_async=is_async),
            node_names=node_names,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            from_inputs=from_inputs,
            to_outputs=to_outputs,
            load_versions=load_version,
            pipeline_name=pipeline,
            namespace=namespace,
        )
