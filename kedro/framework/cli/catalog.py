"""A collection of CLI commands for working with Kedro catalog."""
import copy
from collections import defaultdict

import click
import yaml
from click import secho
from parse import parse

from kedro.framework.cli.utils import KedroCliError, env_option, split_string
from kedro.framework.project import pipelines, settings
from kedro.framework.session import KedroSession
from kedro.framework.startup import ProjectMetadata


def _create_session(package_name: str, **kwargs):
    kwargs.setdefault("save_on_close", False)
    try:
        return KedroSession.create(package_name, **kwargs)
    except Exception as exc:
        raise KedroCliError(
            f"Unable to instantiate Kedro session.\nError: {exc}"
        ) from exc


# pylint: disable=missing-function-docstring
@click.group(name="Kedro")
def catalog_cli():  # pragma: no cover
    pass


@catalog_cli.group()
def catalog():
    """Commands for working with catalog."""


# pylint: disable=too-many-locals
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
    title = "DataSets in '{}' pipeline"
    not_mentioned = "Datasets not mentioned in pipeline"
    mentioned = "Datasets mentioned in pipeline"

    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    datasets_meta = context.catalog._data_sets  # pylint: disable=protected-access
    catalog_ds = set(context.catalog.list())

    target_pipelines = pipeline or pipelines.keys()

    result = {}
    for pipe in target_pipelines:
        pl_obj = pipelines.get(pipe)
        if pl_obj:
            pipeline_ds = pl_obj.data_sets()
        else:
            existing_pls = ", ".join(sorted(pipelines.keys()))
            raise KedroCliError(
                f"'{pipe}' pipeline not found! Existing pipelines: {existing_pls}"
            )

        unused_ds = catalog_ds - pipeline_ds
        default_ds = pipeline_ds - catalog_ds
        used_ds = catalog_ds - unused_ds

        unused_by_type = _map_type_to_datasets(unused_ds, datasets_meta)
        used_by_type = _map_type_to_datasets(used_ds, datasets_meta)

        if default_ds:
            used_by_type["DefaultDataSet"].extend(default_ds)

        data = ((not_mentioned, dict(unused_by_type)), (mentioned, dict(used_by_type)))
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

    Add `MemoryDataSet` datasets to Data Catalog YAML configuration file
    for each dataset in a registered pipeline if it is missing from
    the `DataCatalog`.

    The catalog configuration will be saved to
    `<conf_source>/<env>/catalog/<pipeline_name>.yml` file.
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
        for ds_name in pipeline.data_sets()
        if not ds_name.startswith("params:") and ds_name != "parameters"
    }

    catalog_datasets = {
        ds_name
        for ds_name in context.catalog._data_sets.keys()  # pylint: disable=protected-access
        if not ds_name.startswith("params:") and ds_name != "parameters"
    }

    # Datasets that are missing in Data Catalog
    missing_ds = sorted(pipe_datasets - catalog_datasets)
    if missing_ds:
        catalog_path = (
            context.project_path
            / settings.CONF_SOURCE
            / env
            / "catalog"
            / f"{pipeline_name}.yml"
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
        catalog_config[ds_name] = {"type": "MemoryDataSet"}

    # Create only `catalog` folder under existing environment
    # (all parent folders must exist).
    catalog_path.parent.mkdir(exist_ok=True)
    with catalog_path.open(mode="w") as catalog_file:
        yaml.safe_dump(catalog_config, catalog_file, default_flow_style=False)


def pick_best_match(matches):
    matches = sorted(matches, key=lambda x: (specificity(x[0]), x[0]))
    return matches[0]


def specificity(pattern):
    """This function will check length of exactly matched characters not inside brackets
    Example -
    specificity("{namespace}.companies") = 10
    specificity("{namespace}.{dataset}") = 1
    specificity("france.companies") = 16
    """
    pattern_variables = parse(pattern, pattern).named
    for k in pattern_variables:
        pattern_variables[k] = ""
    specific_characters = pattern.format(**pattern_variables)
    return -len(specific_characters)


@catalog.command("resolve")
@env_option
@click.pass_obj
def resolve_catalog_datasets(metadata: ProjectMetadata, env):
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()
    catalog_conf = context.config_loader["catalog"]

    # Create a list of all datasets used in the project pipelines.
    pipeline_datasets = []
    for _, pl_obj in pipelines.items():
        pipeline_ds = pl_obj.data_sets()
        for dataset in pipeline_ds:
            pipeline_datasets.append(dataset)
    pipeline_datasets = set(pipeline_datasets)
    result_catalog = {}
    for pipeline_dataset in pipeline_datasets:
        matches = []
        for ds_name in catalog_conf.keys():
            result = parse(ds_name, pipeline_dataset)
            if not result:
                continue
            # We have found a match!
            matches.append((ds_name, result))
        if len(matches) == 0:
            # print(f"skipping {pipeline_dataset} -> maybe params or MemoryDataSet")
            continue
        best_match, result = pick_best_match(matches)
        best_match_config = copy.deepcopy(catalog_conf[best_match])
        # Match results to patterns in best matching catalog entry
        for key, value in best_match_config.items():
            string_value = str(value)
            try:
                formatted_string = string_value.format_map(result.named)
            except KeyError:
                # Dataset config has a placeholder which is not present in the ds name
                print(f"'{key}' has invalid catalog configuration")
            best_match_config[key] = formatted_string
        result_catalog[pipeline_dataset] = best_match_config
    secho(yaml.dump(result_catalog))
