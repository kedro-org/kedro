"""A collection of CLI commands for working with registered Kedro pipelines."""
import click
import yaml

from kedro.framework.cli.utils import KedroCliError, command_with_verbosity
from kedro.framework.project import pipelines
from kedro.framework.startup import ProjectMetadata


# pylint: disable=missing-function-docstring
@click.group(name="Kedro")
def registry_cli():  # pragma: no cover
    pass


@registry_cli.group()
def registry():
    """Commands for working with registered pipelines."""


@registry.command("list")
def list_registered_pipelines():
    """List all pipelines defined in your pipeline_registry.py file."""
    click.echo(yaml.dump(sorted(pipelines)))


@command_with_verbosity(registry, "describe")
@click.argument("name", nargs=1, default="__default__")
@click.pass_obj
def describe_registered_pipeline(
    metadata: ProjectMetadata, name, **kwargs
):  # pylint: disable=unused-argument, protected-access
    """Describe a registered pipeline by providing a pipeline name.
    Defaults to the `__default__` pipeline.
    """
    pipeline_obj = pipelines.get(name)
    if not pipeline_obj:
        all_pipeline_names = pipelines.keys()
        existing_pipelines = ", ".join(sorted(all_pipeline_names))
        raise KedroCliError(
            f"`{name}` pipeline not found. Existing pipelines: [{existing_pipelines}]"
        )

    nodes = []
    for node in pipeline_obj.nodes:
        namespace = f"{node.namespace}." if node.namespace else ""
        nodes.append(f"{namespace}{node._name or node._func_name} ({node._func_name})")
    result = {"Nodes": nodes}

    click.echo(yaml.dump(result))
