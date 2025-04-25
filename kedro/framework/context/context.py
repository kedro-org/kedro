"""This module provides context for Kedro project."""

from __future__ import annotations

import logging
from copy import deepcopy
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from warnings import warn

from attrs import define, field
from omegaconf import OmegaConf

from kedro.config import AbstractConfigLoader, MissingConfigException
from kedro.framework.project import settings
from kedro.io import CatalogProtocol, KedroDataCatalog  # noqa: TCH001
from kedro.pipeline.transcoding import _transcode_split

if TYPE_CHECKING:
    from pluggy import PluginManager


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


def _validate_transcoded_datasets(catalog: CatalogProtocol) -> None:
    """Validates transcoded datasets are correctly named

    Args:
        catalog: The catalog object containing the datasets to be
            validated.

    Raises:
        ValueError: If a dataset name does not conform to the expected
            transcoding naming conventions,a ValueError is raised by the
            `_transcode_split` function.

    """
    for dataset_name in catalog:
        _transcode_split(dataset_name)


def _expand_full_path(project_path: str | Path) -> Path:
    return Path(project_path).expanduser().resolve()


@define(slots=False)  # Enable setting new attributes to `KedroContext`
class KedroContext:
    """``KedroContext`` is the base class which holds the configuration and
    Kedro's main functionality.

    Create a context object by providing the root of a Kedro project and
    the environment configuration subfolders (see ``kedro.config.OmegaConfigLoader``)
    Raises:
        KedroContextError: If there is a mismatch
            between Kedro project version and package version.
    Args:
        project_path: Project path to define the context for.
        config_loader: Kedro's ``OmegaConfigLoader`` for loading the configuration files.
        env: Optional argument for configuration default environment to be used
            for running the pipeline. If not specified, it defaults to "local".
        package_name: Package name for the Kedro project the context is
            created for.
        hook_manager: The ``PluginManager`` to activate hooks, supplied by the session.
        runtime_params: Optional dictionary containing runtime project parameters.
            If specified, will update (and therefore take precedence over)
            the parameters retrieved from the project configuration.

    """

    project_path: Path = field(init=True, converter=_expand_full_path)
    config_loader: AbstractConfigLoader = field(init=True)
    env: str | None = field(init=True)
    _package_name: str = field(init=True)
    _hook_manager: PluginManager = field(init=True)
    _runtime_params: dict[str, Any] | None = field(
        init=True, default=None, converter=deepcopy
    )

    @property
    def catalog(self) -> CatalogProtocol:
        """Read-only property referring to Kedro's catalog` for this context.

        Returns:
            catalog defined in `catalog.yml`.
        Raises:
            KedroContextError: Incorrect catalog registered for the project.

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
            warn(f"Parameters not found in your Kedro project config.\n{exc!s}")
            params = {}

        if self._runtime_params:
            # Merge nested structures
            params = OmegaConf.merge(params, self._runtime_params)

        return OmegaConf.to_container(params) if OmegaConf.is_config(params) else params  # type: ignore[return-value]

    def _get_catalog(
        self,
        save_version: str | None = None,
        load_versions: dict[str, str] | None = None,
    ) -> CatalogProtocol:
        """A hook for changing the creation of a catalog instance.

        Returns:
            catalog defined in `catalog.yml`.
        Raises:
            KedroContextError: Incorrect catalog registered for the project.

        """
        # '**/catalog*' reads modular pipeline configs
        conf_catalog = self.config_loader["catalog"]
        # turn relative paths in conf_catalog into absolute paths
        # before initializing the catalog
        conf_catalog = _convert_paths_to_absolute_posix(
            project_path=self.project_path, conf_dictionary=conf_catalog
        )
        conf_creds = self._get_config_credentials()

        catalog: KedroDataCatalog = settings.DATA_CATALOG_CLASS.from_config(
            catalog=conf_catalog,
            credentials=conf_creds,
            load_versions=load_versions,
            save_version=save_version,
        )

        parameters = self._get_parameters()

        # Add parameters data to catalog.
        for param_name, param_value in parameters.items():
            catalog[param_name] = param_value

        _validate_transcoded_datasets(catalog)

        self._hook_manager.hook.after_catalog_created(
            catalog=catalog,
            conf_catalog=conf_catalog,
            conf_creds=conf_creds,
            parameters=parameters,
            save_version=save_version,
            load_versions=load_versions,
        )
        return catalog

    def _get_parameters(self) -> dict[str, Any]:
        """Returns a dictionary with data to be added in memory as `MemoryDataset`` instances.
        Keys represent parameter names and the values are parameter values."""
        params = self.params
        params_dict = {"parameters": params}

        def _add_param_to_params_dict(param_name: str, param_value: Any) -> None:
            """This recursively adds parameter paths that are defined in `parameters.yml`
            with the addition of any extra parameters passed at initialization to the `params_dict`,
            whenever `param_value` is a dictionary itself, so that users can
            specify specific nested parameters in their node inputs.

            Example:

                >>> param_name = "a"
                >>> param_value = {"b": 1}
                >>> _add_param_to_params_dict(param_name, param_value)
                >>> assert params_dict["params:a"] == {"b": 1}
                >>> assert params_dict["params:a.b"] == 1
            """
            key = f"params:{param_name}"
            params_dict[key] = param_value
            if isinstance(param_value, dict):
                for key, val in param_value.items():
                    _add_param_to_params_dict(f"{param_name}.{key}", val)

        for param_name, param_value in params.items():
            _add_param_to_params_dict(param_name, param_value)

        return params_dict

    def _get_config_credentials(self) -> dict[str, Any]:
        """Getter for credentials specified in credentials directory."""
        try:
            conf_creds: dict[str, Any] = self.config_loader["credentials"]
        except MissingConfigException as exc:
            logging.getLogger(__name__).debug(
                "Credentials not found in your Kedro project config.\n %s", str(exc)
            )
            conf_creds = {}
        return conf_creds


class KedroContextError(Exception):
    """Error occurred when loading project and running context pipeline."""
