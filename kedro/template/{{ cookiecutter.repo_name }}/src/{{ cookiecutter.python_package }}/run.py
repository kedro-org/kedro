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
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
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
from typing import Iterable

from kedro.cli.utils import KedroCliError
from kedro.config import ConfigLoader
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner
from kedro.utils import load_obj

from {{ cookiecutter.python_package }}.pipeline import create_pipeline

# Name of root directory containing project configuration.
CONF_ROOT = "conf"

# Default configuration environment to be used for running the pipeline.
# Change this constant value if you want to load configuration
# from a different location.
DEFAULT_RUN_ENV = "local"


def __kedro_context__():
    """Provide this project's context to ``kedro`` CLI and plugins.
    Please do not rename or remove, as this will break the CLI tool.

    Plugins may request additional objects from this method.
    """
    return {
        "get_config": get_config,
        "create_catalog": create_catalog,
        "create_pipeline": create_pipeline,
        "template_version": "{{ cookiecutter.kedro_version }}",
        "project_name": "{{ cookiecutter.project_name }}",
        "project_path": Path.cwd(),
    }


def get_config(project_path: str, env: str = None, **kwargs) -> ConfigLoader:
    """Loads Kedro's configuration at the root of the project.

    Args:
        project_path: The root directory of the Kedro project.
        env: The environment used for loading configuration.
        kwargs: Ignore any additional arguments added in the future.

    Returns:
        ConfigLoader which can be queried to access the project config.

    """
    project_path = Path(project_path)
    env = env or DEFAULT_RUN_ENV
    conf_paths = [
        str(project_path / CONF_ROOT / "base"),
        str(project_path / CONF_ROOT / env),
    ]
    return ConfigLoader(conf_paths)


def create_catalog(config: ConfigLoader, **kwargs) -> DataCatalog:
    """Loads Kedro's ``DataCatalog``.

    Args:
        config: ConfigLoader which can be queried to access the project config.
        kwargs: Ignore any additional arguments added in the future.

    Returns:
        DataCatalog defined in `catalog.yml`.

    """
    conf_logging = config.get("logging*", "logging*/**")
    logging.config.dictConfig(conf_logging)
    conf_catalog = config.get("catalog*", "catalog*/**")
    conf_creds = config.get("credentials*", "credentials*/**")
    conf_params = config.get("parameters*", "parameters*/**")
    logging.config.dictConfig(conf_logging)
    catalog = DataCatalog.from_config(conf_catalog, conf_creds)
    catalog.add_feed_dict({"parameters": conf_params})
    return catalog


def main(
    tags: Iterable[str] = None,
    env: str = None,
    runner: str = None,
):
    """Application main entry point.

    Args:
        tags: An optional list of node tags which should be used to
            filter the nodes of the ``Pipeline``. If specified, only the nodes
            containing *any* of these tags will be added to the ``Pipeline``.
        env: An optional parameter specifying the environment in which
            the ``Pipeline`` should be run. If not specified defaults to "local".
        runner: An optional parameter specifying the runner that you want to run
            the pipeline with.

    Raises:
        KedroCliError: If the resulting ``Pipeline`` is empty.

    """
    # Report project name
    logging.info("** Kedro project {}".format(Path.cwd().name))

    # Load Catalog
    conf = get_config(project_path=str(Path.cwd()), env=env)
    catalog = create_catalog(config=conf)

    # Load the pipeline
    pipeline = create_pipeline()
    pipeline = pipeline.only_nodes_with_tags(*tags) if tags else pipeline
    if not pipeline.nodes:
        if tags:
            raise KedroCliError("Pipeline contains no nodes with tags: " + str(tags))
        raise KedroCliError("Pipeline contains no nodes")

    # Load the runner
    # When either --parallel or --runner is used, class_obj is assigned to runner
    runner = load_obj(runner, "kedro.runner") if runner else SequentialRunner

    # Run the runner
    runner().run(pipeline, catalog)


if __name__ == "__main__":
    main()
