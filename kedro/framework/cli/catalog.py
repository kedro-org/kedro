"""A collection of CLI commands for working with Kedro catalog."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import click
import yaml
from click import secho

from kedro.framework.cli.utils import env_option, split_string
from kedro.framework.session import KedroSession

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata


def _create_session(package_name: str, **kwargs: Any) -> KedroSession:
    kwargs.setdefault("save_on_close", False)
    return KedroSession.create(**kwargs)


@click.group(name="kedro")
def catalog_cli() -> None:  # pragma: no cover
    pass


@catalog_cli.group()
def catalog() -> None:
    """Commands for working with catalog."""


@catalog.command("describe-datasets")
@env_option
@click.option(
    "--pipeline",
    "-p",
    type=str,
    default="",
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def describe_datasets(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """
    Describe datasets used in the specified pipelines, grouped by type.\n

    This command provides a structured overview of datasets used in the selected pipelines,
    categorizing them into three groups:\n
    - `datasets`: Datasets explicitly defined in the catalog.\n
    - `factories`: Datasets resolved from dataset factory patterns.\n
    - `defaults`: Datasets that do not match any pattern or explicit definition.\n
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    p = pipeline or None
    datasets_dict = context.catalog.describe_datasets(p)  # type: ignore

    secho(yaml.dump(datasets_dict))


@catalog.command("list-patterns")
@env_option
@click.pass_obj
def list_patterns(metadata: ProjectMetadata, env: str) -> None:
    """
    List all dataset factory patterns in the catalog, ranked by priority.

    This method retrieves all dataset factory patterns defined in the catalog,
    ordered by the priority in which they are matched.
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    click.echo(yaml.dump(context.catalog.list_patterns()))  # type: ignore


@catalog.command("resolve-patterns")
@env_option
@click.option(
    "--pipeline",
    "-p",
    type=str,
    default="",
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def resolve_patterns(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """
    Resolve dataset factory patterns against pipeline datasets.

    This method resolves dataset factory patterns for datasets used in the specified pipelines.
    It includes datasets explicitly defined in the catalog as well as those resolved
    from dataset factory patterns.
    """
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    p = pipeline or None
    datasets_dict = context.catalog.resolve_patterns(p)  # type: ignore

    secho(yaml.dump(datasets_dict))
