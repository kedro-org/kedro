"""This module provides context for Kedro project."""
from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any
from urllib.parse import urlparse
from warnings import warn

from attrs import field, frozen
from pluggy import PluginManager

from kedro.config import ConfigLoader, MissingConfigException
from kedro.framework.project import settings
from kedro.io import DataCatalog
from kedro.pipeline.pipeline import _transcode_split


def _is_relative_path(path_string: str) -> bool:
    """Checks whether a path string is a relative path.

    Example:
    ::
        >>> _is_relative_path("data/01_raw") == True
        >>> _is_relative_path("info.log") == True
        >>> _is_relative_path("/tmp/data/01_raw") == False
        >>> _is_relative_path(r"C:\\info.log") == False
        >>> _is_relative_path(r"\\'info.log") == False
        >>> _is_relative_path("c:/info.log") == False
        >>> _is_relative_path("s3://info.log") == False

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
    project_path: Path, conf_dictionary: dict[str, Any]
) -> dict[str, Any]:
    """Turn all relative paths inside ``conf_dictionary`` into absolute paths by appending them
    to ``project_path`` and convert absolute Windows paths to POSIX format. This is a hack to
    make sure that we don't have to change user's working directory for logging and datasets to
    work. It is important for non-standard workflows such as IPython notebook where users don't go
    through `kedro run` or `__main__.py` entrypoints.

    Example:
    ::
        >>> conf = _convert_paths_to_absolute_posix(
        >>>     project_path=Path("/path/to/my/project"),
        >>>     conf_dictionary={
        >>>         "handlers": {
        >>>             "info_file_handler": {
        >>>                 "filename": "info.log"
        >>>             }
        >>>         }
        >>>     }
        >>> )
        >>> print(conf['handlers']['info_file_handler']['filename'])
        "/path/to/my/project/info.log"

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
            f"project_path must be an absolute path. Received: {project_path}"
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


def _validate_transcoded_datasets(catalog: DataCatalog):
    """Validates transcoded datasets are correctly named

    Args:
        catalog (DataCatalog): The catalog object containing the
        datasets to be validated.

    Raises:
        ValueError: If a dataset name does not conform to the expected
        transcoding naming conventions,a ValueError is raised by the
        `_transcode_split` function.

    """
    # noqa: protected-access
    for dataset_name in catalog._datasets.keys():
        _transcode_split(dataset_name)


def _update_nested_dict(old_dict: dict[Any, Any], new_dict: dict[Any, Any]) -> None:
    """Update a nested dict with values of new_dict.

    Args:
        old_dict: dict to be updated
        new_dict: dict to use for updating old_dict

    """
    for key, value in new_dict.items():
        if key not in old_dict:
            old_dict[key] = value
        elif isinstance(old_dict[key], dict) and isinstance(value, dict):
            _update_nested_dict(old_dict[key], value)
        else:
            old_dict[key] = value


def _expand_full_path(project_path: str | Path) -> Path:
    return Path(project_path).expanduser().resolve()


@frozen
class KedroContext:
    """``KedroContext`` is the base class which holds the configuration and
    Kedro's main functionality.
    """

    _package_name: str
    project_path: Path = field(converter=_expand_full_path)
    config_loader: ConfigLoader
    _hook_manager: PluginManager
    env: str | None = None
    _extra_params: dict[str, Any] | None = field(default=None, converter=deepcopy)

    """Create a context object by providing the root of a Kedro project and
    the environment configuration subfolders (see ``kedro.config.ConfigLoader``)

    Raises:
        KedroContextError: If there is a mismatch
            between Kedro project version and package version.

    Args:
        package_name: Package name for the Kedro project the context is
            created for.
        project_path: Project path to define the context for.
        config_loader: Kedro's ``ConfigLoader`` for loading the configuration files.
        hook_manager: The ``PluginManager`` to activate hooks, supplied by the session.
        env: Optional argument for configuration default environment to be used
            for running the pipeline. If not specified, it defaults to "local".
        extra_params: Optional dictionary containing extra project parameters.
            If specified, will update (and therefore take precedence over)
            the parameters retrieved from the project configuration.
    """

    @property
    def catalog(self) -> DataCatalog:
        """Read-only property referring to Kedro's ``DataCatalog`` for this context.

        Returns:
            DataCatalog defined in `catalog.yml`.
        Raises:
            KedroContextError: Incorrect ``DataCatalog`` registered for the project.

        """
        return self._get_catalog()

    @property
    def params(self) -> dict[str, Any]:
        """Read-only property referring to Kedro's parameters for this context.

        Returns:
            Parameters defined in `parameters.yml` with the addition of any
                extra parameters passed at initialization.
        """
        try:
            params = self.config_loader["parameters"]
        except MissingConfigException as exc:
            warn(f"Parameters not found in your Kedro project config.\n{str(exc)}")
            params = {}
        _update_nested_dict(params, self._extra_params or {})
        return params

    def _get_catalog(
        self,
        save_version: str = None,
        load_versions: dict[str, str] = None,
    ) -> DataCatalog:
        """A hook for changing the creation of a DataCatalog instance.

        Returns:
            DataCatalog defined in `catalog.yml`.
        Raises:
            KedroContextError: Incorrect ``DataCatalog`` registered for the project.

        """
        # '**/catalog*' reads modular pipeline configs
        conf_catalog = self.config_loader["catalog"]
        # turn relative paths in conf_catalog into absolute paths
        # before initializing the catalog
        conf_catalog = _convert_paths_to_absolute_posix(
            project_path=self.project_path, conf_dictionary=conf_catalog
        )
        conf_creds = self._get_config_credentials()

        catalog = settings.DATA_CATALOG_CLASS.from_config(
            catalog=conf_catalog,
            credentials=conf_creds,
            load_versions=load_versions,
            save_version=save_version,
        )

        feed_dict = self._get_feed_dict()
        catalog.add_feed_dict(feed_dict)
        _validate_transcoded_datasets(catalog)
        self._hook_manager.hook.after_catalog_created(
            catalog=catalog,
            conf_catalog=conf_catalog,
            conf_creds=conf_creds,
            feed_dict=feed_dict,
            save_version=save_version,
            load_versions=load_versions,
        )
        return catalog

    def _get_feed_dict(self) -> dict[str, Any]:
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
            key = f"params:{param_name}"
            feed_dict[key] = param_value
            if isinstance(param_value, dict):
                for key, val in param_value.items():
                    _add_param_to_feed_dict(f"{param_name}.{key}", val)

        for param_name, param_value in params.items():
            _add_param_to_feed_dict(param_name, param_value)

        return feed_dict

    def _get_config_credentials(self) -> dict[str, Any]:
        """Getter for credentials specified in credentials directory."""
        try:
            conf_creds = self.config_loader["credentials"]
        except MissingConfigException as exc:
            logging.getLogger(__name__).debug(
                "Credentials not found in your Kedro project config.\n %s", str(exc)
            )
            conf_creds = {}
        return conf_creds


class KedroContextError(Exception):
    """Error occurred when loading project and running context pipeline."""
