# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""A collection of CLI commands for working with Kedro catalog."""
from collections import defaultdict

import click
import yaml
from click import secho

from kedro.framework.cli.pipeline import _create_session
from kedro.framework.cli.utils import KedroCliError, env_option, split_string
from kedro.framework.startup import ProjectMetadata


@click.group()
def catalog():
    """Commands for working with catalog."""


# pylint: disable=too-many-locals
@catalog.command("list")
@env_option
@click.option(
    "--pipeline",
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

    pipelines = pipeline or context.pipelines.keys()

    result = {}
    for pipe in pipelines:
        pl_obj = context.pipelines.get(pipe)
        if pl_obj:
            pipeline_ds = pl_obj.data_sets()
        else:
            existing_pls = ", ".join(sorted(context.pipelines.keys()))
            raise KedroCliError(
                f"`{pipe}` pipeline not found! Existing pipelines: {existing_pls}"
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
    "--pipeline", "pipeline_name", type=str, required=True, help="Name of a pipeline.",
)
@click.pass_obj
def create_catalog(metadata: ProjectMetadata, pipeline_name, env):
    """Create Data Catalog YAML configuration with missing datasets.

    Add `MemoryDataSet` datasets to Data Catalog YAML configuration file
    for each dataset in a registered pipeline if it is missing from
    the `DataCatalog`.

    The catalog configuration will be saved to
    `<conf_root>/<env>/catalog/<pipeline_name>.yml` file.
    """
    env = env or "base"
    session = _create_session(metadata.package_name, env=env)
    context = session.load_context()

    pipeline = context.pipelines.get(pipeline_name)

    if not pipeline:
        existing_pipelines = ", ".join(sorted(context.pipelines.keys()))
        raise KedroCliError(
            f"`{pipeline_name}` pipeline not found! Existing pipelines: {existing_pipelines}"
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
            / context.CONF_ROOT
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
