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
import logging
import logging.config
import os
import sys
from pathlib import Path
from typing import Any, Dict, Iterable, Union
from warnings import warn

import yaml

from kedro import __version__
from kedro.config import ConfigLoader, MissingConfigException
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.runner import AbstractRunner, SequentialRunner
from kedro.utils import load_obj
from kedro.versioning import VersionJournal


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

    def __init__(self, project_path: Union[Path, str], env: str = None):
        """Create a context object by providing the root of a Kedro project and
        the environment configuration subfolders (see ``kedro.config.ConfigLoader``)

        Raises:
            KedroContextError: If there is a mismatch
                between Kedro project version and package version.

        Args:
            project_path: Project path to define the context for.
            env: Optional argument for configuration default environment to be used
            for running the pipeline. If not specified, it defaults to "local".

        """

        def _version_mismatch_error(context_version):
            return (
                "Your Kedro project version {} does not match Kedro package "
                "version {} you are running. Make sure to update your project template. "
                "See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md for how to "
                "migrate your Kedro project."
            ).format(context_version, __version__)

        # check the match for major and minor version (skip patch version)
        if self.project_version.split(".")[:2] != __version__.split(".")[:2]:
            raise KedroContextError(_version_mismatch_error(self.project_version))

        self._project_path = Path(project_path).expanduser().resolve()
        self.env = env or "local"
        self._setup_logging()

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

    def _create_catalog(  # pylint: disable=no-self-use
        self, conf_catalog: Dict[str, Any], conf_creds: Dict[str, Any]
    ) -> DataCatalog:
        """A hook for changing the creation of the DataCatalog instance.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        return DataCatalog.from_config(conf_catalog, conf_creds)

    @property
    def catalog(self) -> DataCatalog:
        """Read-only property referring to Kedro's ``DataCatalog`` for this context.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        conf_catalog = self.config_loader.get("catalog*", "catalog*/**")
        conf_creds = self._get_config_credentials()
        catalog = self._create_catalog(conf_catalog, conf_creds)
        catalog.add_feed_dict(self._get_feed_dict())
        return catalog

    @property
    def io(self) -> DataCatalog:
        """Read-only alias property referring to Kedro's ``DataCatalog`` for this
        context.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        # pylint: disable=invalid-name
        return self.catalog

    def _create_config_loader(  # pylint: disable=no-self-use
        self, conf_paths: Iterable[str]
    ) -> ConfigLoader:
        """A hook for changing the creation of the ConfigLoader instance.

        Returns:
            Instance of `ConfigLoader`.

        """
        return ConfigLoader(conf_paths)

    @property
    def config_loader(self) -> ConfigLoader:
        """Read-only property referring to Kedro's ``ConfigLoader`` for this
        context.

        Returns:
            Instance of `ConfigLoader` created by `_create_config_loader()`.

        """
        conf_paths = [
            str(self.project_path / self.CONF_ROOT / "base"),
            str(self.project_path / self.CONF_ROOT / self.env),
        ]
        return self._create_config_loader(conf_paths)

    def _setup_logging(self) -> None:
        """Register logging specified in logging directory."""
        conf_logging = self.config_loader.get("logging*", "logging*/**")
        logging.config.dictConfig(conf_logging)

    def _get_feed_dict(self) -> Dict[str, Any]:
        """Get parameters and return the feed dictionary."""
        try:
            params = self.config_loader.get("parameters*", "parameters*/**")
        except MissingConfigException as exc:
            warn(
                "Parameters not found in your Kedro project config.\n{}".format(
                    str(exc)
                )
            )
            params = {}

        feed_dict = {"parameters": params}
        for param_name, param_value in params.items():
            key = "params:{}".format(param_name)
            feed_dict[key] = param_value
        return feed_dict

    def _get_config_credentials(self) -> Dict[str, Any]:
        """Getter for credentials specified in credentials directory."""
        try:
            conf_creds = self.config_loader.get("credentials*", "credentials*/**")
        except MissingConfigException as exc:
            warn(
                "Credentials not found in your Kedro project config.\n{}".format(
                    str(exc)
                )
            )
            conf_creds = {}
        return conf_creds

    # pylint: disable=too-many-arguments
    def _filter_pipeline(
        self,
        pipeline: Pipeline = None,
        tags: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        node_names: Iterable[str] = None,
    ) -> Pipeline:
        """Filter the pipeline as the intersection of all conditions."""
        pipeline = pipeline or self.pipeline
        if tags:
            pipeline = pipeline & self.pipeline.only_nodes_with_tags(*tags)
            if not pipeline.nodes:
                raise KedroContextError(
                    "Pipeline contains no nodes with tags: {}".format(str(tags))
                )
        if from_nodes:
            pipeline = pipeline & self.pipeline.from_nodes(*from_nodes)
        if to_nodes:
            pipeline = pipeline & self.pipeline.to_nodes(*to_nodes)
        if node_names:
            pipeline = pipeline & self.pipeline.only_nodes(*node_names)

        if not pipeline.nodes:
            raise KedroContextError("Pipeline contains no nodes")
        return pipeline

    # pylint: disable=too-many-arguments
    def _record_version_journal(
        self,
        catalog: DataCatalog,
        tags: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        node_names: Iterable[str] = None,
    ) -> None:
        """Record the run variables into journal."""
        record_data = {
            "project_path": str(self.project_path),
            "env": self.env,
            "kedro_version": self.project_version,
            "tags": tags,
            "from_nodes": from_nodes,
            "to_nodes": to_nodes,
            "node_names": node_names,
        }
        journal = VersionJournal(record_data)
        catalog.set_version_journal(journal)

    def run(  # pylint: disable=too-many-arguments
        self,
        tags: Iterable[str] = None,
        runner: AbstractRunner = None,
        node_names: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        pipeline: Pipeline = None,
        catalog: DataCatalog = None,
    ) -> Dict[str, Any]:
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
            from_nodes: An optional list of node names which should be used as a
                starting point of the new ``Pipeline``.
            to_nodes: An optional list of node names which should be used as an
                end point of the new ``Pipeline``.
            pipeline: Optional Pipeline to run, defaults to self.pipeline.
            catalog: Optional DataCatalog to run with, defaults to self.catalog.
        Raises:
            KedroContextError: If the resulting ``Pipeline`` is empty
                or incorrect tags are provided.
        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.
        """
        # Report project name
        logging.info("** Kedro project %s", self.project_path.name)

        pipeline = self._filter_pipeline(
            pipeline, tags, from_nodes, to_nodes, node_names
        )
        catalog = catalog or self.catalog

        self._record_version_journal(catalog, tags, from_nodes, to_nodes, node_names)

        # Run the runner
        runner = runner or SequentialRunner()
        return runner.run(pipeline, catalog)


def load_context(project_path: Union[str, Path], **kwargs) -> KedroContext:
    """Loads the KedroContext object of a Kedro Project as defined in `src/<package-name>/run.py`.
    This function will change the current working directory to the project path.

    Args:
        project_path: Path to the Kedro project.
        kwargs: Optional kwargs for ``ProjectContext`` class in `run.py`.

    Returns:
        Instance of ``KedroContext`` class defined in Kedro project.

    Raises:
        KedroContextError: Either '.kedro.yml' was not found
            or loaded context has package conflict.

    """
    project_path = Path(project_path).expanduser().resolve()
    src_path = str(project_path / "src")

    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = src_path

    kedro_yaml = project_path / ".kedro.yml"
    try:
        with kedro_yaml.open("r") as kedro_yml:

            context_path = yaml.safe_load(kedro_yml)["context_path"]
    except Exception:
        raise KedroContextError(
            "Could not retrive 'context_path' from '.kedro.yml' in {}. If you have created "
            "your project with Kedro version <0.15.0, make sure to update your project template. "
            "See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md "
            "for how to migrate your Kedro project.".format(str(project_path))
        )

    context_class = load_obj(context_path)

    if os.getcwd() != str(project_path):
        logging.getLogger(__name__).warning(
            "Changing the current working directory to %s", str(project_path)
        )
        os.chdir(str(project_path))  # Move to project root

    # Instantiate the context after changing the cwd for logging to be properly configured.
    context = context_class(project_path, **kwargs)
    return context


class KedroContextError(Exception):
    """Error occurred when loading project and running context pipeline."""
