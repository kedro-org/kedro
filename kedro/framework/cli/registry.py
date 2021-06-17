# Copyright 2021 QuantumBlack Visual Analytics Limited
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
