"""A collection of CLI commands for working with Kedro catalog."""

from __future__ import annotations

import warnings
from collections import defaultdict
from itertools import chain, filterfalse
from typing import TYPE_CHECKING, Any

import click
import yaml
from click import secho

from kedro import KedroDeprecationWarning
from kedro.framework.cli.utils import KedroCliError, env_option, split_string
from kedro.framework.project import pipelines, settings
from kedro.framework.session import KedroSession
from kedro.io.data_catalog import DataCatalog
from kedro.io.kedro_data_catalog import _LazyDataset

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.startup import ProjectMetadata
    from kedro.io import AbstractDataset


def _create_session(package_name: str, **kwargs: Any) -> KedroSession:
    kwargs.setdefault("save_on_close", False)
    return KedroSession.create(**kwargs)


def is_parameter(dataset_name: str) -> bool:
    # TODO: when breaking change move it to kedro/io/core.py
    """Check if dataset is a parameter."""
    return dataset_name.startswith("params:") or dataset_name == "parameters"


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
    default="",
    help="Name of the modular pipeline to run. If not set, "
    "the project pipeline is run by default.",
    callback=split_string,
)
@click.pass_obj
def list_datasets(metadata: ProjectMetadata, pipeline: str, env: str) -> None:
    """Show datasets per type."""
    warnings.warn(
        "`kedro catalog list` CLI command is deprecated and will be replaced with "
        "its updated version - `kedro catalog list-datasets` in Kedro 1.0.0.",
        KedroDeprecationWarning,
    )
    title = "Datasets in '{}' pipeline"
    not_mentioned = "Datasets not mentioned in pipeline"
    mentioned = "Datasets mentioned in pipeline"
    factories = "Datasets generated from factories"

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    try:
        data_catalog = context.catalog
        datasets_meta = data_catalog._datasets
        catalog_ds = set(data_catalog.list())
    except Exception as exc:
        raise KedroCliError(
            f"Unable to instantiate Kedro Catalog.\nError: {exc}"
        ) from exc

    target_pipelines = pipeline or pipelines.keys()

    result = {}
    for pipe in target_pipelines:
        pl_obj = pipelines.get(pipe)
        if pl_obj:
            pipeline_ds = pl_obj.datasets()
        else:
            existing_pls = ", ".join(sorted(pipelines.keys()))
            raise KedroCliError(
                f"'{pipe}' pipeline not found! Existing pipelines: {existing_pls}"
            )

        unused_ds = catalog_ds - pipeline_ds
        default_ds = pipeline_ds - catalog_ds
        used_ds = catalog_ds - unused_ds

        # resolve any factory datasets in the pipeline
        factory_ds_by_type = defaultdict(list)

        for ds_name in default_ds:
            if data_catalog.config_resolver.match_pattern(ds_name):
                ds_config = data_catalog.config_resolver.resolve_pattern(ds_name)
                factory_ds_by_type[ds_config.get("type", "DefaultDataset")].append(
                    ds_name
                )

        default_ds = default_ds - set(chain.from_iterable(factory_ds_by_type.values()))

        unused_by_type = _map_type_to_datasets(unused_ds, datasets_meta)
        used_by_type = _map_type_to_datasets(used_ds, datasets_meta)

        if default_ds:
            used_by_type["DefaultDataset"].extend(default_ds)

        data = (
            (mentioned, dict(used_by_type)),
            (factories, dict(factory_ds_by_type)),
            (not_mentioned, dict(unused_by_type)),
        )
        result[title.format(pipe)] = {key: value for key, value in data if value}
    secho(yaml.dump(result))


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


@catalog.command("create")
@env_option(help="Environment to create Data Catalog YAML file in. Defaults to `base`.")
@click.option(
    "--pipeline",
    "-p",
    "pipeline_name",
    type=str,
    required=True,
    help="Name of a pipeline.",
)
@click.pass_obj
def create_catalog(metadata: ProjectMetadata, pipeline_name: str, env: str) -> None:
    """Create Data Catalog YAML configuration with missing datasets.

    Add ``MemoryDataset`` datasets to Data Catalog YAML configuration
    file for each dataset in a registered pipeline if it is missing from
    the ``DataCatalog``.

    The catalog configuration will be saved to
    `<conf_source>/<env>/catalog_<pipeline_name>.yml` file.
    """
    warnings.warn(
        "`kedro catalog create` CLI command is deprecated and will be removed in Kedro 1.0.0.",
        KedroDeprecationWarning,
    )
    env = env or "base"
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    pipeline = pipelines.get(pipeline_name)

    if not pipeline:
        existing_pipelines = ", ".join(sorted(pipelines.keys()))
        raise KedroCliError(
            f"'{pipeline_name}' pipeline not found! Existing pipelines: {existing_pipelines}"
        )

    pipeline_datasets = set(filterfalse(is_parameter, pipeline.datasets()))

    catalog_datasets = set(filterfalse(is_parameter, context.catalog.list()))

    # Datasets that are missing in Data Catalog
    missing_ds = sorted(pipeline_datasets - catalog_datasets)
    if missing_ds:
        catalog_path = (
            context.project_path
            / settings.CONF_SOURCE
            / env
            / f"catalog_{pipeline_name}.yml"
        )
        _add_missing_datasets_to_catalog(missing_ds, catalog_path)
        click.echo(f"Data Catalog YAML configuration was created: {catalog_path}")
    else:
        click.echo("All datasets are already configured.")


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
    warnings.warn(
        "`kedro catalog rank` CLI command is deprecated and will be replaced with "
        "its updated version - `kedro catalog list-patterns` in Kedro 1.0.0.",
        KedroDeprecationWarning,
    )
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
    warnings.warn(
        "`kedro catalog resolve` CLI command is deprecated and will be replaced with "
        "its updated version - `kedro catalog resolve-patterns` in Kedro 1.0.0.",
        KedroDeprecationWarning,
    )

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    catalog_config = context.config_loader["catalog"]
    credentials_config = context._get_config_credentials()
    data_catalog = DataCatalog.from_config(
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
