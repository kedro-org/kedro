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
"""This module provides context for Kedro project."""

import abc
import logging
import logging.config
import os
import sys
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any, Dict, Iterable, Tuple, Union
from urllib.parse import urlparse
from warnings import warn

import anyconfig

from kedro import __version__
from kedro.config import ConfigLoader, MissingConfigException
from kedro.framework.hooks import get_hook_manager
from kedro.io import DataCatalog
from kedro.io.core import generate_timestamp
from kedro.pipeline import Pipeline
from kedro.pipeline.pipeline import _transcode_split
from kedro.runner.runner import AbstractRunner
from kedro.runner.sequential_runner import SequentialRunner
from kedro.utils import load_obj
from kedro.versioning import Journal

_PLUGIN_HOOKS = "kedro.hooks"  # entry-point to load hooks from for installed plugins

# Kedro configuration files in the precedence order
KEDRO_CONFIGS = (".kedro.yml", "pyproject.toml")


def _version_mismatch_error(context_version) -> str:
    return (
        "Your Kedro project version {} does not match Kedro package version {} "
        "you are running. Make sure to update your project template. See "
        "https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md "
        "for how to migrate your Kedro project."
    ).format(context_version, __version__)


def _is_relative_path(path_string: str) -> bool:
    """Checks whether a path string is a relative path.

    Example:
    ::
        >>> _is_relative_path("data/01_raw") == True
        >>> _is_relative_path("logs/info.log") == True
        >>> _is_relative_path("/tmp/data/01_raw") == False
        >>> _is_relative_path(r"C:\\logs\\info.log") == False
        >>> _is_relative_path(r"\\logs\\'info.log") == False
        >>> _is_relative_path("c:/logs/info.log") == False
        >>> _is_relative_path("s3://logs/info.log") == False

    Args:
        path_string: The path string to check.
    Returns:
        Whether the string is a relative path.
    """
    # os.path.splitdrive does not reliably work on non-Windows systems
    # breaking the coverage, using PureWindowsPath instead
    is_full_windows_path_with_drive = bool(PureWindowsPath(path_string).drive)
    if is_full_windows_path_with_drive:
        return False

    is_remote_path = bool(urlparse(path_string).scheme)
    if is_remote_path:
        return False

    is_absolute_path = PurePosixPath(path_string).is_absolute()
    if is_absolute_path:
        return False

    return True


def _convert_paths_to_absolute_posix(
    project_path: Path, conf_dictionary: Dict[str, Any]
) -> Dict[str, Any]:
    """Turn all relative paths inside ``conf_dictionary`` into absolute paths by appending them
    to ``project_path`` and convert absolute Windows paths to POSIX format. This is a hack to
    make sure that we don't have to change user's working directory for logging and datasets to
    work. It is important for non-standard workflows such as IPython notebook where users don't go
    through `kedro run` or `run.py` entrypoints.

    Example:
    ::
        >>> conf = _convert_paths_to_absolute_posix(
        >>>     project_path=Path("/path/to/my/project"),
        >>>     conf_dictionary={
        >>>         "handlers": {
        >>>             "info_file_handler": {
        >>>                 "filename": "logs/info.log"
        >>>             }
        >>>         }
        >>>     }
        >>> )
        >>> print(conf['handlers']['info_file_handler']['filename'])
        "/path/to/my/project/logs/info.log"

    Args:
        project_path: The root directory to prepend to relative path to make absolute path.
        conf_dictionary: The configuration containing paths to expand.
    Returns:
        A dictionary containing only absolute paths.
    Raises:
        ValueError: If the provided ``project_path`` is not an absolute path.
    """
    if not project_path.is_absolute():
        raise ValueError(
            "project_path must be an absolute path. Received: {}".format(project_path)
        )

    # only check a few conf keys that are known to specify a path string as value
    conf_keys_with_filepath = ("filename", "filepath", "path")

    for conf_key, conf_value in conf_dictionary.items():

        # if the conf_value is another dictionary, absolutify its paths first.
        if isinstance(conf_value, dict):
            conf_dictionary[conf_key] = _convert_paths_to_absolute_posix(
                project_path, conf_value
            )
            continue

        # if the conf_value is not a dictionary nor a string, skip
        if not isinstance(conf_value, str):
            continue

        # if the conf_value is a string but the conf_key isn't one associated with filepath, skip
        if conf_key not in conf_keys_with_filepath:
            continue

        if _is_relative_path(conf_value):
            # Absolute local path should be in POSIX format
            conf_value_absolute_path = (project_path / conf_value).as_posix()
            conf_dictionary[conf_key] = conf_value_absolute_path
        elif PureWindowsPath(conf_value).drive:
            # Convert absolute Windows path to POSIX format
            conf_dictionary[conf_key] = PureWindowsPath(conf_value).as_posix()

    return conf_dictionary


def _validate_layers_for_transcoding(catalog: DataCatalog) -> None:
    """Check that transcoded names that correspond to
    the same dataset also belong to the same layer.
    """

    def _find_conflicts():
        base_names_to_layer = {}
        for current_layer, dataset_names in catalog.layers.items():
            for name in dataset_names:
                base_name, _ = _transcode_split(name)
                known_layer = base_names_to_layer.setdefault(base_name, current_layer)
                if current_layer != known_layer:
                    yield name
                else:
                    base_names_to_layer[base_name] = current_layer

    conflicting_datasets = sorted(_find_conflicts())
    if conflicting_datasets:
        error_str = ", ".join(conflicting_datasets)
        raise ValueError(
            f"Transcoded datasets should have the same layer. Mismatch found for: {error_str}"
        )


class KedroContext(abc.ABC):
    """``KedroContext`` is the base class which holds the configuration and
    Kedro's main functionality. Project-specific context class should extend
    this abstract class and implement the all abstract methods.

    Attributes:
       CONF_ROOT: Name of root directory containing project configuration.
       Default name is "conf".
       hooks: The list of hooks provided by user to extend KedroContext's execution.

    Example:
    ::

        >>> from kedro.framework.context import KedroContext
        >>> from kedro.pipeline import Pipeline
        >>>
        >>> class ProjectContext(KedroContext):
        >>>     @property
        >>>     def pipeline(self) -> Pipeline:
        >>>         return Pipeline([])

    """

    CONF_ROOT = "conf"

    # Registry for user-defined hooks to be overwritten by a project context.
    hooks: Tuple = ()

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
        self._project_path = Path(project_path).expanduser().resolve()
        self._static_data = get_static_project_data(self._project_path)

        # check the match for major and minor version (skip patch version)
        if self.project_version.split(".")[:2] != __version__.split(".")[:2]:
            raise KedroContextError(_version_mismatch_error(self.project_version))

        self.env = env or "local"
        self._extra_params = deepcopy(extra_params)

        self._register_hooks(auto=True)
        # we need a ConfigLoader registered in order to be able to set up logging
        self._setup_logging()

    @property
    def static_data(self) -> Dict[str, Any]:
        """Read-only property for Kedro project static data.

        Returns:
            A dictionary with defined static project data.

        """
        return deepcopy(self._static_data)

    @property
    def project_name(self) -> str:
        """Property for Kedro project name.

        Returns:
            Name of Kedro project.

        """
        return self.static_data["project_name"]

    @property
    def project_version(self) -> str:
        """Property for Kedro version.

        Returns:
            Kedro version.

        """
        return self.static_data["project_version"]

    @property
    def package_name(self) -> str:
        """Property for Kedro project package name.

        Returns:
            Name of Kedro project package.

        """
        return self.static_data["package_name"]

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

    def _register_hooks_setuptools(self):
        """Register pluggy hooks from setuptools entrypoints."""
        hook_manager = get_hook_manager()
        already_registered = hook_manager.get_plugins()
        found = hook_manager.load_setuptools_entrypoints(_PLUGIN_HOOKS)
        disable_plugins = set(self.static_data.get("disable_hooks_for_plugins", []))

        # Get list of plugin/distinfo tuples for all setuptools registered plugins.
        plugininfo = hook_manager.list_plugin_distinfo()
        plugin_names = []
        disabled_plugin_names = []
        for plugin, dist in plugininfo:
            if dist.project_name in disable_plugins:
                # `unregister()` is used instead of `set_blocked()` because
                # we want to disable hooks for specific plugin based on project
                # name and not `entry_point` name. Also, we log project names with
                # version for which hooks were registered.
                hook_manager.unregister(plugin=plugin)
                found -= 1
                disabled_plugin_names.append(f"{dist.project_name}-{dist.version}")
            elif plugin not in already_registered:
                plugin_names.append(f"{dist.project_name}-{dist.version}")

        if disabled_plugin_names:
            logging.info(
                "Hooks are disabled for plugin(s): %s",
                ", ".join(sorted(disabled_plugin_names)),
            )

        if plugin_names:
            logging.info(
                "Registered hooks from %d installed plugin(s): %s",
                found,
                ", ".join(sorted(plugin_names)),
            )

    def _register_hooks(self, auto: bool = False) -> None:
        """Register all hooks as specified in ``hooks`` with the global ``hook_manager``,
        and, optionally, from installed plugins.

        Args:
            auto: An optional flag to enable auto-discovery and registration of plugin hooks.
        """
        hook_manager = get_hook_manager()

        # enrich with hooks specified in .kedro.yml or pyproject.toml if .kedro.yml doesn't exist
        hooks_locations = self.static_data.get("hooks", [])
        configured_hooks = tuple(load_obj(hook) for hook in hooks_locations)

        all_hooks = self.hooks + configured_hooks
        for hooks_collection in all_hooks:
            # Sometimes users might create more than one context instance, in which case
            # hooks have already been registered, so we perform a simple check here
            # to avoid an error being raised and break user's workflow.
            if not hook_manager.is_registered(hooks_collection):
                hook_manager.register(hooks_collection)

        if auto:
            self._register_hooks_setuptools()

    def _get_pipeline(self, name: str = None) -> Pipeline:
        name = name or "__default__"
        pipelines = self._get_pipelines()

        try:
            return pipelines[name]
        except (TypeError, KeyError) as exc:
            raise KedroContextError(
                f"Failed to find the pipeline named '{name}'. "
                f"It needs to be generated and returned "
                f"by the '_get_pipelines' function."
            ) from exc

    def _get_pipelines(self) -> Dict[str, Pipeline]:  # pylint: disable=no-self-use
        """Abstract method for a hook for changing the creation of a Pipeline instance.

        Returns:
            A dictionary of defined pipelines.
        """
        hook_manager = get_hook_manager()
        pipelines_dicts = (
            hook_manager.hook.register_pipelines()  # pylint: disable=no-member
        )

        pipelines = {}  # type: Dict[str, Pipeline]
        for pipeline_collection in pipelines_dicts:
            duplicate_keys = pipeline_collection.keys() & pipelines.keys()
            if duplicate_keys:
                warn(
                    f"Found duplicate pipeline entries. "
                    f"The following will be overwritten: {', '.join(duplicate_keys)}"
                )
            pipelines.update(pipeline_collection)

        return pipelines

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
            # '**/parameters*' reads modular pipeline configs
            params = self.config_loader.get(
                "parameters*", "parameters*/**", "**/parameters*"
            )
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
        # '**/catalog*' reads modular pipeline configs
        conf_catalog = self.config_loader.get("catalog*", "catalog*/**", "**/catalog*")
        # turn relative paths in conf_catalog into absolute paths
        # before initializing the catalog
        conf_catalog = _convert_paths_to_absolute_posix(
            project_path=self.project_path, conf_dictionary=conf_catalog
        )
        conf_creds = self._get_config_credentials()
        catalog = self._create_catalog(
            conf_catalog, conf_creds, save_version, journal, load_versions
        )
        feed_dict = self._get_feed_dict()
        catalog.add_feed_dict(feed_dict)
        if catalog.layers:
            _validate_layers_for_transcoding(catalog)
        hook_manager = get_hook_manager()
        hook_manager.hook.after_catalog_created(  # pylint: disable=no-member
            catalog=catalog,
            conf_catalog=conf_catalog,
            conf_creds=conf_creds,
            feed_dict=feed_dict,
            save_version=save_version,
            load_versions=load_versions,
            run_id=self.run_id,
        )
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
        hook_manager = get_hook_manager()
        catalog = hook_manager.hook.register_catalog(  # pylint: disable=no-member
            catalog=conf_catalog,
            credentials=conf_creds,
            load_versions=load_versions,
            save_version=save_version,
            journal=journal,
        )

        return catalog or DataCatalog.from_config(  # for backwards compatibility
            conf_catalog, conf_creds, load_versions, save_version, journal
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
        hook_manager = get_hook_manager()
        config_loader = hook_manager.hook.register_config_loader(  # pylint: disable=no-member
            conf_paths=conf_paths
        )
        return config_loader or ConfigLoader(conf_paths)  # for backwards compatibility

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
        conf_logging = self.config_loader.get("logging*", "logging*/**", "**/logging*")
        # turn relative paths in logging config into absolute path
        # before initialising loggers
        conf_logging = _convert_paths_to_absolute_posix(
            project_path=self.project_path, conf_dictionary=conf_logging
        )
        logging.config.dictConfig(conf_logging)

    def _get_feed_dict(self) -> Dict[str, Any]:
        """Get parameters and return the feed dictionary."""
        params = self.params
        feed_dict = {"parameters": params}

        def _add_param_to_feed_dict(param_name, param_value):
            """This recursively adds parameter paths to the `feed_dict`,
            whenever `param_value` is a dictionary itself, so that users can
            specify specific nested parameters in their node inputs.

            Example:

                >>> param_name = "a"
                >>> param_value = {"b": 1}
                >>> _add_param_to_feed_dict(param_name, param_value)
                >>> assert feed_dict["params:a"] == {"b": 1}
                >>> assert feed_dict["params:a.b"] == 1
            """
            key = "params:{}".format(param_name)
            feed_dict[key] = param_value

            if isinstance(param_value, dict):
                for key, val in param_value.items():
                    _add_param_to_feed_dict("{}.{}".format(param_name, key), val)

        for param_name, param_value in params.items():
            _add_param_to_feed_dict(param_name, param_value)

        return feed_dict

    def _get_config_credentials(self) -> Dict[str, Any]:
        """Getter for credentials specified in credentials directory."""
        try:
            conf_creds = self.config_loader.get(
                "credentials*", "credentials*/**", "**/credentials*"
            )
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
            Exception: Any uncaught exception will be re-raised
                after being passed to``on_pipeline_error``.
        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.
        """
        # Report project name
        logging.info("** Kedro project %s", self.project_path.name)

        pipeline = self._get_pipeline(name=pipeline_name)
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
        hook_manager = get_hook_manager()
        hook_manager.hook.before_pipeline_run(  # pylint: disable=no-member
            run_params=record_data, pipeline=filtered_pipeline, catalog=catalog
        )

        try:
            run_result = runner.run(filtered_pipeline, catalog, run_id)
        except Exception as exc:
            hook_manager.hook.on_pipeline_error(  # pylint: disable=no-member
                error=exc,
                run_params=record_data,
                pipeline=filtered_pipeline,
                catalog=catalog,
            )
            raise exc

        hook_manager.hook.after_pipeline_run(  # pylint: disable=no-member
            run_params=record_data,
            run_result=run_result,
            pipeline=filtered_pipeline,
            catalog=catalog,
        )
        return run_result

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


def get_static_project_data(project_path: Union[str, Path]) -> Dict[str, Any]:
    """Read static project data from `<project_path>/.kedro.yml` config file if it
    exists otherwise from `<project_path>/pyproject.toml` (under `[tool.kedro]` section).

    Args:
        project_path: Local path to project root directory to look up `.kedro.yml` or
            `pyproject.toml` in.

    Raises:
        KedroContextError: Neither '.kedro.yml' nor `pyproject.toml` was found
            or `[tool.kedro]` section is missing in `pyproject.toml`, or config file
            cannot be parsed.

    Returns:
        A mapping that contains static project data.
    """
    project_path = Path(project_path).expanduser().resolve()

    config_paths = [
        project_path / conf_file
        for conf_file in KEDRO_CONFIGS
        if (project_path / conf_file).is_file()
    ]

    if not config_paths:
        configs = ", ".join(KEDRO_CONFIGS)
        raise KedroContextError(
            f"Could not find any of configuration files '{configs}' in {project_path}. "
            f"If you have created your project with Kedro "
            f"version <0.15.0, make sure to update your project template. "
            f"See https://github.com/quantumblacklabs/kedro/blob/master/RELEASE.md"
            f"#migration-guide-from-kedro-014-to-kedro-0150 "
            f"for how to migrate your Kedro project."
        )

    # First found wins
    kedro_config = config_paths[0]
    try:
        static_data = anyconfig.load(kedro_config)
    except Exception as exc:
        raise KedroContextError(f"Failed to parse '{kedro_config.name}' file.") from exc

    if kedro_config.suffix == ".toml":
        try:
            static_data = static_data["tool"]["kedro"]
        except KeyError as exc:
            raise KedroContextError(
                f"There's no '[tool.kedro]' section in the '{kedro_config.name}'. "
                f"Please add '[tool.kedro]' section to the file with appropriate "
                f"configuration parameters."
            ) from exc

    source_dir = Path(static_data.get("source_dir", "src")).expanduser()
    source_dir = (project_path / source_dir).resolve()
    static_data["source_dir"] = source_dir
    static_data["config_file"] = kedro_config

    return static_data


def validate_source_path(source_path: Path, project_path: Path):
    """Validate the source path exists and is relative to the project path.

    Args:
        source_path: Absolute source path.
        project_path: Path to the Kedro project.

    Raises:
        KedroContextError: Either source_path is not relative to project_path or
            source_path does not exist.

    """
    try:
        source_path.relative_to(project_path)
    except ValueError as exc:
        raise KedroContextError(
            f"Source path '{source_path}' has to be relative to "
            f"your project root '{project_path}'."
        ) from exc
    if not source_path.exists():
        raise KedroContextError(f"Source path '{source_path}' cannot be found.")


def load_package_context(
    project_path: Path, package_name: str, **kwargs
) -> KedroContext:
    """Loads the KedroContext object of a Kedro project package,
    as output by `kedro package` and installed via `pip`.
    This function is only intended to be used in a project's `run.py`.
    If you are looking to load KedroContext object for any other workflow,
    you might want to use ``load_context`` instead.

    Args:
        project_path: Path to the Kedro project, i.e. where `conf/` resides.
        package_name: Name of the installed Kedro project package.
        kwargs: Optional kwargs for ``ProjectContext`` class in `run.py`.

    Returns:
        Instance of ``KedroContext`` class defined in Kedro project.

    Raises:
        KedroContextError: Neither '.kedro.yml' nor `pyproject.toml` was found
            or `[tool.kedro]` section is missing in `pyproject.toml`, or loaded context
            has package conflict.
    """
    context_path = f"{package_name}.run.ProjectContext"
    try:
        context_class = load_obj(context_path)
    except ModuleNotFoundError as exc:
        raise KedroContextError(
            f"Cannot load context object from {context_path} for package {package_name}."
        ) from exc

    # update kwargs with env from the environment variable (defaults to None if not set)
    # need to do this because some CLI command (e.g `kedro run`) defaults to passing
    # in `env=None`
    kwargs["env"] = kwargs.get("env") or os.getenv("KEDRO_ENV")

    context = context_class(project_path=project_path, **kwargs)
    return context


def load_context(project_path: Union[str, Path], **kwargs) -> KedroContext:
    """Loads the KedroContext object of a Kedro Project.
    This is the default way to load the KedroContext object for normal workflows such as
    CLI, Jupyter Notebook, Plugins, etc. It assumes the following project structure
    under the given project_path::

       <project_path>
           |__ <src_dir>
           |__ .kedro.yml
           |__ kedro_cli.py
           |__ pyproject.toml

    The name of the <scr_dir> is `src` by default. The `.kedro.yml` or `pyproject.toml` can
    be used for configuration. If `.kedro.yml` exists, it will be used otherwise, `pyproject.toml`
    will be treated as the configuration file (Kedro configuration should be under
    `[tool.kedro]` section).

    Args:
        project_path: Path to the Kedro project.
        kwargs: Optional kwargs for ``ProjectContext`` class in `run.py`.

    Returns:
        Instance of ``KedroContext`` class defined in Kedro project.

    Raises:
        KedroContextError: Neither '.kedro.yml' nor `pyproject.toml` was found
            or `[tool.kedro]` section is missing in `pyproject.toml`, or loaded context
            has package conflict.

    """
    project_path = Path(project_path).expanduser().resolve()
    static_data = get_static_project_data(project_path)

    source_dir = static_data["source_dir"]
    validate_source_path(source_dir, project_path)

    if "context_path" not in static_data:
        conf_file = static_data["config_file"].name
        raise KedroContextError(
            f"'{conf_file}' doesn't have a required `context_path` field. "
            f"Please refer to the documentation."
        )

    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

    if "PYTHONPATH" not in os.environ:
        os.environ["PYTHONPATH"] = str(source_dir)

    context_class = load_obj(static_data["context_path"])

    # update kwargs with env from the environment variable
    # (defaults to None if not set)
    # need to do this because some CLI command (e.g `kedro run`) defaults to
    # passing in `env=None`
    kwargs["env"] = kwargs.get("env") or os.getenv("KEDRO_ENV")

    context = context_class(project_path=project_path, **kwargs)
    return context


class KedroContextError(Exception):
    """Error occurred when loading project and running context pipeline."""
