# Copyright 2020 QuantumBlack Visual Analytics Limited
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
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Iterable, Union
from warnings import warn

import yaml

from kedro import __version__
from kedro.config import ConfigLoader, MissingConfigException
from kedro.io import DataCatalog
from kedro.io.core import generate_timestamp
from kedro.pipeline import Pipeline
from kedro.runner import AbstractRunner, SequentialRunner
from kedro.utils import load_obj
from kedro.versioning import Journal

KEDRO_ENV_VAR = "KEDRO_ENV"


def _version_mismatch_error(context_version) -> str:
    return (
        "Your Kedro project version {} does not match Kedro package version {} "
        "you are running. Make sure to update your project template. See "
        "https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md "
        "for how to migrate your Kedro project."
    ).format(context_version, __version__)


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

    def __init__(
        self,
        project_path: Union[Path, str],
        env: str = None,
        extra_params: Dict[str, Any] = None,
    ):
        """Create a context object by providing the root of a Kedro project and
        the environment configuration subfolders (see ``kedro.config.ConfigLoader``)

        Raises:
            KedroContextError: If there is a mismatch
                between Kedro project version and package version.

        Args:
            project_path: Project path to define the context for.
            env: Optional argument for configuration default environment to be used
                for running the pipeline. If not specified, it defaults to "local".
            extra_params: Optional dictionary containing extra project parameters.
                If specified, will update (and therefore take precedence over)
                the parameters retrieved from the project configuration.
        """

        # check the match for major and minor version (skip patch version)
        if self.project_version.split(".")[:2] != __version__.split(".")[:2]:
            raise KedroContextError(_version_mismatch_error(self.project_version))

        self._project_path = Path(project_path).expanduser().resolve()
        self.env = env or "local"
        self._extra_params = deepcopy(extra_params)
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
    def pipeline(self) -> Pipeline:
        """Read-only property for an instance of Pipeline.

        Returns:
            Defined pipeline.

        """
        return self._get_pipeline()

    @property
    def pipelines(self) -> Dict[str, Pipeline]:
        """Read-only property for an instance of Pipeline.

        Returns:
            A dictionary of defined pipelines.
        """
        return self._get_pipelines()

    def _get_pipeline(self, name: str = None) -> Pipeline:
        name = name or "__default__"
        pipelines = self._get_pipelines()

        try:
            return pipelines[name]
        except (TypeError, KeyError):
            raise KedroContextError(
                "Failed to find the pipeline named '{}'. "
                "It needs to be generated and returned "
                "by the '_get_pipelines' function.".format(name)
            )

    def _get_pipelines(self) -> Dict[str, Pipeline]:
        """Abstract method for a hook for changing the creation of a Pipeline instance.

        Returns:
            A dictionary of defined pipelines.
        """
        # NOTE: This method is not `abc.abstractmethod` for backward compatibility.
        raise NotImplementedError(
            "`{}` is a subclass of KedroContext and it must implement "
            "the `_get_pipelines` method".format(self.__class__.__name__)
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
        return self._get_catalog()

    @property
    def params(self) -> Dict[str, Any]:
        """Read-only property referring to Kedro's parameters for this context.

        Returns:
            Parameters defined in `parameters.yml` with the addition of any
                extra parameters passed at initialization.
        """
        try:
            params = self.config_loader.get("parameters*", "parameters*/**")
        except MissingConfigException as exc:
            warn(
                "Parameters not found in your Kedro project config.\n{}".format(
                    str(exc)
                )
            )
            params = {}
        params.update(self._extra_params or {})
        return params

    def _get_catalog(
        self,
        save_version: str = None,
        journal: Journal = None,
        load_versions: Dict[str, str] = None,
    ) -> DataCatalog:
        """A hook for changing the creation of a DataCatalog instance.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        conf_catalog = self.config_loader.get("catalog*", "catalog*/**")
        conf_creds = self._get_config_credentials()
        catalog = self._create_catalog(
            conf_catalog, conf_creds, save_version, journal, load_versions
        )
        catalog.add_feed_dict(self._get_feed_dict())
        return catalog

    def _create_catalog(  # pylint: disable=no-self-use,too-many-arguments
        self,
        conf_catalog: Dict[str, Any],
        conf_creds: Dict[str, Any],
        save_version: str = None,
        journal: Journal = None,
        load_versions: Dict[str, str] = None,
    ) -> DataCatalog:
        """A factory method for the DataCatalog instantiation.

        Returns:
            DataCatalog defined in `catalog.yml`.

        """
        return DataCatalog.from_config(
            conf_catalog,
            conf_creds,
            save_version=save_version,
            journal=journal,
            load_versions=load_versions,
        )

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
        """A factory method for the ConfigLoader instantiation.

        Returns:
            Instance of `ConfigLoader`.

        """
        return ConfigLoader(conf_paths)

    def _get_config_loader(self) -> ConfigLoader:
        """A hook for changing the creation of a ConfigLoader instance.

        Returns:
            Instance of `ConfigLoader` created by `_create_config_loader()`.

        """
        conf_paths = [
            str(self.project_path / self.CONF_ROOT / "base"),
            str(self.project_path / self.CONF_ROOT / self.env),
        ]
        return self._create_config_loader(conf_paths)

    @property
    def config_loader(self) -> ConfigLoader:
        """Read-only property referring to Kedro's ``ConfigLoader`` for this
        context.

        Returns:
            Instance of `ConfigLoader`.

        """
        return self._get_config_loader()

    def _setup_logging(self) -> None:
        """Register logging specified in logging directory."""
        conf_logging = self.config_loader.get("logging*", "logging*/**")
        logging.config.dictConfig(conf_logging)

    def _get_feed_dict(self) -> Dict[str, Any]:
        """Get parameters and return the feed dictionary."""
        params = self.params
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

    # pylint: disable=too-many-arguments, no-self-use
    def _filter_pipeline(
        self,
        pipeline: Pipeline,
        tags: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        node_names: Iterable[str] = None,
        from_inputs: Iterable[str] = None,
    ) -> Pipeline:
        """Filter the pipeline as the intersection of all conditions."""
        new_pipeline = pipeline
        # We need to intersect with the pipeline because the order
        # of operations matters, so we don't want to do it incrementally.
        # As an example, with a pipeline of nodes 1,2,3, think of
        # "from 1", and "only 1 and 3" - the order you do them in results in
        # either 1 & 3, or just 1.
        if tags:
            new_pipeline &= pipeline.only_nodes_with_tags(*tags)
            if not new_pipeline.nodes:
                raise KedroContextError(
                    "Pipeline contains no nodes with tags: {}".format(str(tags))
                )
        if from_nodes:
            new_pipeline &= pipeline.from_nodes(*from_nodes)
        if to_nodes:
            new_pipeline &= pipeline.to_nodes(*to_nodes)
        if node_names:
            new_pipeline &= pipeline.only_nodes(*node_names)
        if from_inputs:
            new_pipeline &= pipeline.from_inputs(*from_inputs)

        if not new_pipeline.nodes:
            raise KedroContextError("Pipeline contains no nodes")
        return new_pipeline

    @property
    def run_id(self) -> Union[None, str]:
        """Unique identifier for a run / journal record, defaults to None.
        If `run_id` is None, `save_version` will be used instead.
        """
        return self._get_run_id()

    def run(  # pylint: disable=too-many-arguments,too-many-locals
        self,
        tags: Iterable[str] = None,
        runner: AbstractRunner = None,
        node_names: Iterable[str] = None,
        from_nodes: Iterable[str] = None,
        to_nodes: Iterable[str] = None,
        from_inputs: Iterable[str] = None,
        load_versions: Dict[str, str] = None,
        pipeline_name: str = None,
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
            from_inputs: An optional list of input datasets which should be used as a
                starting point of the new ``Pipeline``.
            load_versions: An optional flag to specify a particular dataset version timestamp
                to load.
            pipeline_name: Name of the ``Pipeline`` to execute.
                Defaults to "__default__".
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

        try:
            pipeline = self._get_pipeline(name=pipeline_name)
        except NotImplementedError:
            common_migration_message = (
                "`ProjectContext._get_pipeline(self, name)` method is expected. "
                "Please refer to the 'Modular Pipelines' section of the documentation."
            )
            if pipeline_name:
                raise KedroContextError(
                    "The project is not fully migrated to use multiple pipelines. "
                    + common_migration_message
                )

            warn(
                "You are using the deprecated pipeline construction mechanism. "
                + common_migration_message,
                DeprecationWarning,
            )
            pipeline = self.pipeline

        filtered_pipeline = self._filter_pipeline(
            pipeline=pipeline,
            tags=tags,
            from_nodes=from_nodes,
            to_nodes=to_nodes,
            node_names=node_names,
            from_inputs=from_inputs,
        )

        save_version = self._get_save_version()
        run_id = self.run_id or save_version

        record_data = {
            "run_id": run_id,
            "project_path": str(self.project_path),
            "env": self.env,
            "kedro_version": self.project_version,
            "tags": tags,
            "from_nodes": from_nodes,
            "to_nodes": to_nodes,
            "node_names": node_names,
            "from_inputs": from_inputs,
            "load_versions": load_versions,
            "pipeline_name": pipeline_name,
            "extra_params": self._extra_params,
        }
        journal = Journal(record_data)

        catalog = self._get_catalog(
            save_version=save_version, journal=journal, load_versions=load_versions
        )

        # Run the runner
        runner = runner or SequentialRunner()
        return runner.run(filtered_pipeline, catalog)

    def _get_run_id(
        self, *args, **kwargs  # pylint: disable=unused-argument
    ) -> Union[None, str]:
        """A hook for generating a unique identifier for a
        run / journal record, defaults to None.
        If None, `save_version` will be used instead.
        """
        return None

    def _get_save_version(
        self, *args, **kwargs  # pylint: disable=unused-argument
    ) -> str:
        """Generate unique ID for dataset versioning, defaults to timestamp.
        `save_version` MUST be something that can be ordered, in order to
        easily determine the latest version.
        """
        return generate_timestamp()


def load_context(project_path: Union[str, Path], **kwargs) -> KedroContext:
    """Loads the KedroContext object of a Kedro Project based on the path specified
    in `.kedro.yml`.
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
            kedro_yaml_content = yaml.safe_load(kedro_yml)
    except FileNotFoundError:
        raise KedroContextError(
            "Could not find '.kedro.yml' in {}. If you have created your project "
            "with Kedro version <0.15.0, make sure to update your project template. "
            "See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md "
            "for how to migrate your Kedro project.".format(str(project_path))
        )
    except Exception:
        raise KedroContextError("Failed to parse '.kedro.yml' file")

    try:
        context_path = kedro_yaml_content["context_path"]
    except (KeyError, TypeError):
        raise KedroContextError(
            "'.kedro.yml' doesn't have a required `context_path` field. "
            "Please refer to the documentation."
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
