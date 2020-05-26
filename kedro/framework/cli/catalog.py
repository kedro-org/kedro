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
from pathlib import Path

import click
import yaml
from click import secho

from kedro.framework.cli.utils import KedroCliError, env_option, split_string
from kedro.framework.context import load_context


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
    help="Name of the modular pipeline to run. If not set, the project pipeline is run by default.",
    callback=split_string,
)
def list_datasets(pipeline, env):
    """Show datasets per type."""
    title = "DataSets in '{}' pipeline"
    not_mentioned = "Datasets not mentioned in pipeline"
    mentioned = "Datasets mentioned in pipeline"

    context = load_context(Path.cwd(), env=env)
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
                f"{pipe} pipeline not found! Existing pipelines: {existing_pls}"
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
