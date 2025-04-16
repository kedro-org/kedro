"""A collection of CLI commands for working with Kedro catalog."""

from __future__ import annotations

from collections import defaultdict
from itertools import filterfalse
from typing import TYPE_CHECKING, Any

import click
import yaml
from click import secho

from kedro.framework.cli.utils import env_option, split_string
from kedro.framework.project import pipelines
from kedro.framework.session import KedroSession
from kedro.io.core import is_parameter
from kedro.io.kedro_data_catalog import KedroDataCatalog, _LazyDataset

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.startup import ProjectMetadata
    from kedro.io import AbstractDataset


def _create_session(package_name: str, **kwargs: Any) -> KedroSession:
    kwargs.setdefault("save_on_close", False)
    return KedroSession.create(**kwargs)


@click.group(name="Kedro")
def catalog_cli() -> None:  # pragma: no cover
    pass


@catalog_cli.group()
def catalog() -> None:
    """Commands for working with catalog."""


@catalog.command("list")
@env_option
@click.option(
    "--pipeline",
    "-p",
    type=str,
    default=None,
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def list_datasets(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """Show datasets per type."""

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    catalog = context.catalog

    datasets_dict = catalog.list_datasets(pipeline)

    secho(yaml.dump(datasets_dict))


def _map_type_to_datasets(
    datasets: set[str], datasets_meta: dict[str, AbstractDataset]
) -> dict:
    """Build dictionary with a dataset type as a key and list of
    datasets of the specific type as a value.
    """
    mapping = defaultdict(list)  # type: ignore[var-annotated]
    for dataset_name in filterfalse(is_parameter, datasets):
        if isinstance(datasets_meta[dataset_name], _LazyDataset):
            ds_type = str(datasets_meta[dataset_name]).split(".")[-1]
        else:
            ds_type = datasets_meta[dataset_name].__class__.__name__
        if dataset_name not in mapping[ds_type]:
            mapping[ds_type].append(dataset_name)
    return mapping


def _add_missing_datasets_to_catalog(missing_ds: list[str], catalog_path: Path) -> None:
    if catalog_path.is_file():
        catalog_config = yaml.safe_load(catalog_path.read_text()) or {}
    else:
        catalog_config = {}

    for ds_name in missing_ds:
        catalog_config[ds_name] = {"type": "MemoryDataset"}

    # Create only `catalog` folder under existing environment
    # (all parent folders must exist).
    catalog_path.parent.mkdir(exist_ok=True)
    with catalog_path.open(mode="w") as catalog_file:
        yaml.safe_dump(catalog_config, catalog_file, default_flow_style=False)


@catalog.command("rank")
@env_option
@click.pass_obj
def rank_catalog_factories(metadata: ProjectMetadata, env: str) -> None:
    """List all dataset factories in the catalog, ranked by priority by which they are matched."""
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    catalog_factories = context.catalog.config_resolver.list_patterns()
    if catalog_factories:
        click.echo(yaml.dump(catalog_factories))
    else:
        click.echo("There are no dataset factories in the catalog.")


@catalog.command("resolve")
@env_option
@click.pass_obj
def resolve_patterns(metadata: ProjectMetadata, env: str) -> None:
    """Resolve catalog factories against pipeline datasets. Note that this command is runner
    agnostic and thus won't take into account any default dataset creation defined in the runner."""

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    catalog_config = context.config_loader["catalog"]
    credentials_config = context._get_config_credentials()
    data_catalog = KedroDataCatalog.from_config(
        catalog=catalog_config, credentials=credentials_config
    )

    explicit_datasets = {
        ds_name: ds_config
        for ds_name, ds_config in catalog_config.items()
        if not data_catalog.config_resolver.is_pattern(ds_name)
    }

    target_pipelines = pipelines.keys()
    pipeline_datasets = set()

    for pipe in target_pipelines:
        pl_obj = pipelines.get(pipe)
        if pl_obj:
            pipeline_datasets.update(pl_obj.datasets())

    for ds_name in pipeline_datasets:
        if ds_name in explicit_datasets or is_parameter(ds_name):
            continue

        ds_config = data_catalog.config_resolver.resolve_pattern(ds_name)

        # Exclude MemoryDatasets not set in the catalog explicitly
        if ds_config:
            explicit_datasets[ds_name] = ds_config

    secho(yaml.dump(explicit_datasets))
