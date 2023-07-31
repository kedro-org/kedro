"""A collection of CLI commands for working with Kedro project."""

import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

import click

from kedro.framework.cli.utils import (
    KedroCliError,
    _check_module_importable,
    _config_file_callback,
    _deprecate_options,
    _get_values_as_tuple,
    _reformat_load_versions,
    _split_load_versions,
    _split_params,
    call,
    command_with_verbosity,
    env_option,
    forward_command,
    python_call,
    split_node_names,
    split_string,
)
from kedro.framework.project import settings
from kedro.framework.session import KedroSession
from kedro.framework.startup import ProjectMetadata
from kedro.utils import load_obj

NO_DEPENDENCY_MESSAGE = """{module} is not installed. Please make sure {module} is in
{src}/requirements.txt and run 'pip install -r src/requirements.txt'."""
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
@click.pass_obj  # this will pass the metadata as first argument
def test(metadata: ProjectMetadata, args, **kwargs):  # noqa: ument
    """Run the test suite. (DEPRECATED)"""
    deprecation_message = (
        "DeprecationWarning: Command 'kedro test' is deprecated and "
        "will not be available from Kedro 0.19.0. "
        "Use the command 'pytest' instead. "
    )
    click.secho(deprecation_message, fg="red")

    try:
        _check_module_importable("pytest")
    except KedroCliError as exc:
        source_path = metadata.source_dir
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="pytest", src=str(source_path))
        ) from exc
    python_call("pytest", args)


@command_with_verbosity(project_group)
@click.option("-c", "--check-only", is_flag=True, help=LINT_CHECK_ONLY_HELP)
@click.argument("files", type=click.Path(exists=True), nargs=-1)
@click.pass_obj  # this will pass the metadata as first argument
def lint(
    metadata: ProjectMetadata, files, check_only, **kwargs
):  # noqa: unused-argument
    """Run flake8, isort and black. (DEPRECATED)"""
    deprecation_message = (
        "DeprecationWarning: Command 'kedro lint' is deprecated and "
        "will not be available from Kedro 0.19.0."
    )
    click.secho(deprecation_message, fg="red")

    source_path = metadata.source_dir
    package_name = metadata.package_name
    files = files or (str(source_path / "tests"), str(source_path / package_name))

    if "PYTHONPATH" not in os.environ:
        # isort needs the source path to be in the 'PYTHONPATH' environment
        # variable to treat it as a first-party import location
        os.environ["PYTHONPATH"] = str(source_path)  # pragma: no cover

    for module_name in ("flake8", "isort", "black"):
        try:
            _check_module_importable(module_name)
        except KedroCliError as exc:
            raise KedroCliError(
                NO_DEPENDENCY_MESSAGE.format(module=module_name, src=str(source_path))
            ) from exc

    python_call("black", ("--check",) + files if check_only else files)
    python_call("flake8", files)
    python_call("isort", ("--check",) + files if check_only else files)


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
    source_path = metadata.source_dir
    call(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            "../dist",
        ],
        cwd=str(source_path),
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
@click.pass_obj  # this will pass the metadata as first argument
def build_docs(metadata: ProjectMetadata, open_docs):
    """Build the project documentation. (DEPRECATED)"""
    deprecation_message = (
        "DeprecationWarning: Command 'kedro build-docs' is deprecated and "
        "will not be available from Kedro 0.19.0."
    )
    click.secho(deprecation_message, fg="red")

    source_path = metadata.source_dir
    package_name = metadata.package_name

    python_call("pip", ["install", str(source_path / "[docs]")])
    python_call("pip", ["install", "-r", str(source_path / "requirements.txt")])
    python_call("ipykernel", ["install", "--user", f"--name={package_name}"])
    shutil.rmtree("docs/build", ignore_errors=True)
    call(
        [
            "sphinx-apidoc",
            "--module-first",
            "-o",
            "docs/source",
            str(source_path / package_name),
        ]
    )
    call(["sphinx-build", "-M", "html", "docs/source", "docs/build", "-a"])
    if open_docs:
        docs_page = (Path.cwd() / "docs" / "build" / "html" / "index.html").as_uri()
        click.secho(f"Opening {docs_page}")
        webbrowser.open(docs_page)


@forward_command(project_group, name="build-reqs")
@click.option(
    "--input-file",
    "input_file",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    multiple=False,
    help=INPUT_FILE_HELP,
)
@click.option(
    "--output-file",
    "output_file",
    multiple=False,
    help=OUTPUT_FILE_HELP,
)
@click.pass_obj  # this will pass the metadata as first argument
def build_reqs(
    metadata: ProjectMetadata, input_file, output_file, args, **kwargs
):  # noqa: unused-argument
    """Run `pip-compile` on src/requirements.txt or the user defined input file and save
    the compiled requirements to src/requirements.lock or the user defined output file.
    (DEPRECATED)
    """
    deprecation_message = (
        "DeprecationWarning: Command 'kedro build-reqs' is deprecated and "
        "will not be available from Kedro 0.19.0."
    )
    click.secho(deprecation_message, fg="red")

    source_path = metadata.source_dir
    input_file = Path(input_file or source_path / "requirements.txt")
    output_file = Path(output_file or source_path / "requirements.lock")

    if input_file.is_file():
        python_call(
            "piptools",
            [
                "compile",
                *args,
                str(input_file),
                "--output-file",
                str(output_file),
            ],
        )

    else:
        raise FileNotFoundError(
            f"File '{input_file}' not found in the project. "
            "Please specify another input or create the file and try again."
        )

    click.secho(
        f"Requirements built! Please update {input_file.name} "
        "if you'd like to make a change in your project's dependencies, "
        f"and re-run build-reqs to generate the new {output_file.name}.",
        fg="green",
    )


@command_with_verbosity(project_group, "activate-nbstripout")
@click.pass_obj  # this will pass the metadata as first argument
def activate_nbstripout(metadata: ProjectMetadata, **kwargs):  # noqa: unused-argument
    """Install the nbstripout git hook to automatically clean notebooks. (DEPRECATED)"""
    deprecation_message = (
        "DeprecationWarning: Command 'kedro activate-nbstripout' is deprecated and "
        "will not be available from Kedro 0.19.0."
    )
    click.secho(deprecation_message, fg="red")

    source_path = metadata.source_dir
    click.secho(
        (
            "Notebook output cells will be automatically cleared before committing"
            " to git."
        ),
        fg="yellow",
    )

    try:
        _check_module_importable("nbstripout")
    except KedroCliError as exc:
        raise KedroCliError(
            NO_DEPENDENCY_MESSAGE.format(module="nbstripout", src=str(source_path))
        ) from exc

    try:
        res = subprocess.run(  # noqa: subprocess-run-check
            ["git", "rev-parse", "--git-dir"],
            capture_output=True,
        )
        if res.returncode:
            raise KedroCliError("Not a git repository. Run 'git init' first.")
    except FileNotFoundError as exc:
        raise KedroCliError("Git executable not found. Install Git first.") from exc

    call(["nbstripout", "--install"])


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
