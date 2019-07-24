# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Application entry point."""

import logging.config
from pathlib import Path
from typing import Iterable, Type, Union
from warnings import warn

from kedro.cli.utils import KedroCliError
from kedro.config import ConfigLoader, MissingConfigException
from kedro.context import KedroContext
from kedro.io import DataCatalog
from kedro.runner import AbstractRunner
from kedro.utils import load_obj
from kedro.pipeline import Pipeline

from {{ cookiecutter.python_package }}.pipeline import create_pipeline


class ProjectContext(KedroContext):
    """Users can override the remaining methods from the parent class here, or create new ones
    (e.g. as required by plugins)

    """

    project_name = "{{ cookiecutter.project_name }}"
    project_version = "{{ cookiecutter.kedro_version }}"

    @property
    def pipeline(self) -> Pipeline:
        return create_pipeline()


def __kedro_context__(env: str = None, **kwargs) -> KedroContext:
    """Provide this project's context to ``kedro`` CLI and plugins.
    Please do not rename or remove, as this will break the CLI tool.

    Plugins may request additional objects from this method.

    Args:
        env: An optional parameter specifying the environment in which
        the ``Pipeline`` should be run. If not specified defaults to "local".
        kwargs: Optional custom arguments defined by users.
    Returns:
        Instance of ProjectContext class defined in Kedro project.

    """
    if env is None:
        # Default configuration environment to be used for running the pipeline.
        # Change this constant value if you want to load configuration
        # from a different location.
        env = "local"

    return ProjectContext(Path.cwd(), env, **kwargs)


def main(
    tags: Iterable[str] = None,
    env: str = None, runner: Type[AbstractRunner] = None,
    node_names: Iterable[str] = None,
):
    """Application main entry point.

    Args:
        tags: An optional list of node tags which should be used to
            filter the nodes of the ``Pipeline``. If specified, only the nodes
            containing *any* of these tags will be run.
        env: An optional parameter specifying the environment in which
            the ``Pipeline`` should be run. If not specified defaults to "local".
        runner: An optional parameter specifying the runner that you want to run
            the pipeline with.
        node_names: An optional list of node names which should be used to filter
            the nodes of the ``Pipeline``. If specified, only the nodes with these
            names will be run.

    """

    context = __kedro_context__(env)
    context.run(tags, runner, node_names)


if __name__ == "__main__":
    main()
