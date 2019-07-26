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
"""This module provides context for Kedro project."""

import abc
import importlib
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Union
from warnings import warn

from kedro.config import ConfigLoader, MissingConfigException
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.runner import AbstractRunner, SequentialRunner

_LOADED_PATH = None


class KedroContext(abc.ABC):
    """``KedroContext`` is the base class which holds the configuration and
    Kedro's main functionality. Project-specific context class should extend
    this abstract class and implement the all abstract methods.

    Attributes:
       CONF_ROOT: Name of root directory containing project configuration.
       Default name is "conf".

    Example:
    ::

        >>> from kedro.context import KedroContext
        >>> from kedro.pipeline import Pipeline
        >>>
        >>> class ProjectContext(KedroContext):
        >>>     @property
        >>>     def pipeline(self) -> Pipeline:
        >>>         return Pipeline([])

    """

    CONF_ROOT = "conf"

    def __init__(self, project_path: Union[Path, str], env: str = "local"):
        """Create a context object by providing the root of a Kedro project and
        the environment configuration subfolders (see ``kedro.config.ConfigLoader``)

        Args:
            project_path: Project path to define the context for.
            env: Optional argument for configuration default environment to be used
            for running the pipeline. Default environment is 'local'.

        """
        self._project_path = Path(project_path).expanduser().resolve()
        self.env = env
        self._config_loader = self._create_config()
        self._setup_logging()
        self._catalog = self._create_catalog()

    @property
    @abc.abstractmethod
    def project_name(self) -> str:
        """Abstract property for Kedro project name.

        Returns:
            Name of Kedro project.

        """
        raise NotImplementedError(
            "`{}` is a subclass of KedroContext and it must implement "
            "the `project_name` property".format(self.__class__.__name__)
        )

    @property
    @abc.abstractmethod
    def project_version(self) -> str:
        """Abstract property for Kedro version.

        Returns:
            Kedro version.

        """
        raise NotImplementedError(
            "`{}` is a subclass of KedroContext and it must implement "
            "the `project_version` property".format(self.__class__.__name__)
        )

    @property
    @abc.abstractmethod
    def pipeline(self) -> Pipeline:
        """Abstract property for Pipeline getter.

        Returns:
            Defined pipeline.

        """
        raise NotImplementedError(
            "`{}` is a subclass of KedroContext and it must implement "
            "the `pipeline` property".format(self.__class__.__name__)
        )

    @property
    def project_path(self) -> Path:
        """Read-only property containing Kedro's root project directory.

        Returns:
            Project directory.

        """
        return self._project_path

    @property
    def catalog(self) -> DataCatalog:
        """Read-only property referring to Kedro's ``DataCatalog`` for this context.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        return self._catalog

    @property
    def io(self) -> DataCatalog:
        """Read-only alias property referring to Kedro's ``DataCatalog`` for this
        context.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        # pylint: disable=invalid-name
        return self._catalog

    @property
    def config_loader(self) -> ConfigLoader:
        """Read-only property referring to Kedro's ``ConfigLoader`` for this
        context.

        Returns:
            Instance of `ConfigLoader` created by `_create_config()`.

        """
        return self._config_loader

    def _create_config(self) -> ConfigLoader:
        """Load Kedro's configuration at the root of the project.

        Returns:
            ConfigLoader which can be queried to access the project config.

        """
        conf_paths = [
            str(self.project_path / self.CONF_ROOT / "base"),
            str(self.project_path / self.CONF_ROOT / self.env),
        ]
        return ConfigLoader(conf_paths)

    def _setup_logging(self) -> None:
        """Register logging specified in logging directory."""
        conf_logging = self._config_loader.get("logging*", "logging*/**")
        logging.config.dictConfig(conf_logging)

    def _get_feed_dict(self) -> Dict[str, Any]:
        """Get parameters and return the feed dictionary."""
        try:
            params = self._config_loader.get("parameters*", "parameters*/**")
        except MissingConfigException as exc:
            warn(
                "Parameters not found in your Kedro project config.\n{}".format(
                    str(exc)
                )
            )
            params = {}
        return {"parameters": params}

    def _get_config_credentials(self) -> Dict[str, Any]:
        """Getter for credentials specified in credentials directory."""
        try:
            conf_creds = self._config_loader.get("credentials*", "credentials*/**")
        except MissingConfigException as exc:
            warn(
                "Credentials not found in your Kedro project config.\n{}".format(
                    str(exc)
                )
            )
            conf_creds = {}
        return conf_creds

    def _create_catalog(self) -> DataCatalog:
        """Load Kedro's ``DataCatalog`` specified in catalog directory.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        conf_catalog = self._config_loader.get("catalog*", "catalog*/**")
        conf_creds = self._get_config_credentials()
        catalog = DataCatalog.from_config(conf_catalog, conf_creds)
        catalog.add_feed_dict(self._get_feed_dict())
        return catalog

    def run(
        self,
        tags: Iterable[str] = None,
        runner: AbstractRunner = None,
        node_names: Iterable[str] = None,
    ) -> None:
        """Runs the pipeline with a specified runner.

        Args:
            tags: An optional list of node tags which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                containing *any* of these tags will be run.
            runner: An optional parameter specifying the runner that you want to run
                the pipeline with.
            node_names: An optional list of node names which should be used to
                filter the nodes of the ``Pipeline``. If specified, only the nodes
                with these names will be run.
        Raises:
            KedroContextError: If the resulting ``Pipeline`` is empty
                or incorrect tags are provided.

        """
        # Report project name
        logging.info("** Kedro project {}".format(self.project_path.name))

        # Load the pipeline
        pipeline = self.pipeline
        if node_names:
            pipeline = pipeline.only_nodes(*node_names)
        if tags:
            pipeline = pipeline.only_nodes_with_tags(*tags)

        if not pipeline.nodes:
            msg = "Pipeline contains no nodes"
            if tags:
                msg += " with tags: {}".format(str(tags))
            raise KedroContextError(msg)

        # Run the runner
        runner = runner or SequentialRunner()
        runner.run(pipeline, self.catalog)


def load_context(project_path: Union[str, Path], **kwargs) -> KedroContext:
    """Loads KedroContext object defined in `kedro_cli.__kedro_context__`.
    This function will change the current working directory to the project path.

    Args:
        project_path: Path to the Kedro project.
        kwargs: Optional custom arguments defined by users, which will be passed to
        __kedro_context__() in `run.py`.

    Returns:
        Instance of KedroContext class defined in Kedro project.

    Raises:
        KedroContextError: If another project context has already been loaded.

    """
    # global due to importlib caching import_module("kedro_cli") call
    global _LOADED_PATH  # pylint: disable=global-statement

    project_path = Path(project_path).expanduser().resolve()

    if _LOADED_PATH and project_path != _LOADED_PATH:
        raise KedroContextError(
            "Cannot load context for `{}`, since another project `{}` has "
            "already been loaded".format(project_path, _LOADED_PATH)
        )
    if str(project_path) not in sys.path:
        sys.path.append(str(project_path))

    kedro_cli = importlib.import_module("kedro_cli")
    if os.getcwd() != str(project_path):
        warn("Changing the current working directory to {}".format(str(project_path)))
        os.chdir(str(project_path))  # Move to project root
    result = kedro_cli.__get_kedro_context__(**kwargs)  # type: ignore
    _LOADED_PATH = project_path
    return result


class KedroContextError(Exception):
    """Error occurred when loading project and running context pipeline."""
