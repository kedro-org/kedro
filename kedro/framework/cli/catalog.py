"""A collection of CLI commands for working with Kedro catalog."""
import copy
from collections import defaultdict
from itertools import chain

import click
import yaml
from click import secho

from kedro.framework.cli.utils import KedroCliError, env_option, split_string
from kedro.framework.project import pipelines, settings
from kedro.framework.session import KedroSession
from kedro.framework.startup import ProjectMetadata


def _create_session(package_name: str, **kwargs):
    kwargs.setdefault("save_on_close", False)
    return KedroSession.create(package_name, **kwargs)


# noqa: missing-function-docstring
@click.group(name="Kedro")
def catalog_cli():  # pragma: no cover
    pass


@catalog_cli.group()
def catalog():
    """Commands for working with catalog."""


# noqa: too-many-locals,protected-access
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
def list_datasets(metadata: ProjectMetadata, pipeline, env):
    """Show datasets per type."""
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
            matched_pattern = data_catalog._match_pattern(
                data_catalog._dataset_patterns, ds_name
            )
            if matched_pattern:
                ds_config_copy = copy.deepcopy(
                    data_catalog._dataset_patterns[matched_pattern]
                )

                ds_config = data_catalog._resolve_config(
                    ds_name, matched_pattern, ds_config_copy
                )
                factory_ds_by_type[ds_config["type"]].append(ds_name)

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


def _map_type_to_datasets(datasets, datasets_meta):
    """Build dictionary with a dataset type as a key and list of
    datasets of the specific type as a value.
    """
    mapping = defaultdict(list)
    for dataset in datasets:
        is_param = dataset.startswith("params:") or dataset == "parameters"
        if not is_param:
            ds_type = datasets_meta[dataset].__class__.__name__
            if dataset not in mapping[ds_type]:
                mapping[ds_type].append(dataset)
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
def create_catalog(metadata: ProjectMetadata, pipeline_name, env):
    """Create Data Catalog YAML configuration with missing datasets.

    Add ``MemoryDataset`` datasets to Data Catalog YAML configuration
    file for each dataset in a registered pipeline if it is missing from
    the ``DataCatalog``.

    The catalog configuration will be saved to
    `<conf_source>/<env>/catalog_<pipeline_name>.yml` file.
    """
    env = env or "base"
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    pipeline = pipelines.get(pipeline_name)

    if not pipeline:
        existing_pipelines = ", ".join(sorted(pipelines.keys()))
        raise KedroCliError(
            f"'{pipeline_name}' pipeline not found! Existing pipelines: {existing_pipelines}"
        )

    pipe_datasets = {
        ds_name
        for ds_name in pipeline.datasets()
        if not ds_name.startswith("params:") and ds_name != "parameters"
    }

    catalog_datasets = {
        ds_name
        for ds_name in context.catalog._datasets.keys()  # noqa: protected-access
        if not ds_name.startswith("params:") and ds_name != "parameters"
    }

    # Datasets that are missing in Data Catalog
    missing_ds = sorted(pipe_datasets - catalog_datasets)
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


def _add_missing_datasets_to_catalog(missing_ds, catalog_path):
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
def rank_catalog_factories(metadata: ProjectMetadata, env):
    """List all dataset factories in the catalog, ranked by priority by which they are matched."""
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    catalog_factories = context.catalog._dataset_patterns
    if catalog_factories:
        click.echo(yaml.dump(list(catalog_factories.keys())))
    else:
        click.echo("There are no dataset factories in the catalog.")


@catalog.command("resolve")
@env_option
@click.pass_obj
def resolve_patterns(metadata: ProjectMetadata, env):
    """Resolve catalog factories against pipeline datasets"""

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    data_catalog = context.catalog
    catalog_config = context.config_loader["catalog"]

    explicit_datasets = {
        ds_name: ds_config
        for ds_name, ds_config in catalog_config.items()
        if not data_catalog._is_pattern(ds_name)
    }

    target_pipelines = pipelines.keys()
    datasets = set()

    for pipe in target_pipelines:
        pl_obj = pipelines.get(pipe)
        if pl_obj:
            datasets.update(pl_obj.datasets())

    for ds_name in datasets:
        is_param = ds_name.startswith("params:") or ds_name == "parameters"
        if ds_name in explicit_datasets or is_param:
            continue

        matched_pattern = data_catalog._match_pattern(
            data_catalog._dataset_patterns, ds_name
        )
        if matched_pattern:
            ds_config_copy = copy.deepcopy(
                data_catalog._dataset_patterns[matched_pattern]
            )

            ds_config = data_catalog._resolve_config(
                ds_name, matched_pattern, ds_config_copy
            )

            ds_config["filepath"] = _trim_filepath(
                str(context.project_path) + "/", ds_config["filepath"]
            )
            explicit_datasets[ds_name] = ds_config

    secho(yaml.dump(explicit_datasets))


def _trim_filepath(project_path: str, file_path: str):
    return file_path.replace(project_path, "", 1)
