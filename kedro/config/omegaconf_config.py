"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files of yaml or json type from specified paths through OmegaConf.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import typing
from collections.abc import Iterable, KeysView
from enum import Enum, auto
from pathlib import Path
from typing import Any, Callable

import fsspec
from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError, UnsupportedInterpolationType
from omegaconf.resolvers import oc
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from kedro.config.abstract_config import AbstractConfigLoader, MissingConfigException
from kedro.utils import CLOUD_PROTOCOLS, HTTP_PROTOCOLS, _parse_filepath

_config_logger = logging.getLogger(__name__)

_NO_VALUE = object()


class MergeStrategies(Enum):
    SOFT = auto()
    DESTRUCTIVE = auto()


MERGING_IMPLEMENTATIONS = {
    MergeStrategies.SOFT: "_soft_merge",
    MergeStrategies.DESTRUCTIVE: "_destructive_merge",
}


class OmegaConfigLoader(AbstractConfigLoader):
    """Recursively scan directories (config paths) contained in ``conf_source`` for
    configuration files with a ``yaml``, ``yml`` or ``json`` extension, load and merge
    them through ``OmegaConf`` (https://omegaconf.readthedocs.io/)
    and return them in the form of a config dictionary.

    The first processed config path is the ``base`` directory inside
    ``conf_source``. The optional ``env`` argument can be used to specify a
    subdirectory of ``conf_source`` to process as a config path after ``base``.

    When the same top-level key appears in any two config files located in
    the same (sub)directory, a ``ValueError`` is raised.

    When the same key appears in any two config files located in different
    (sub)directories, the last processed config path takes precedence
    and overrides this key and any sub-keys.

    You can access the different configurations as follows:
    ::

        >>> import logging.config
        >>> from kedro.config import OmegaConfigLoader
        >>> from kedro.framework.project import settings
        >>>
        >>> conf_path = str(project_path / settings.CONF_SOURCE)
        >>> conf_loader = OmegaConfigLoader(conf_source=conf_path, env="local")
        >>>
        >>> conf_catalog = conf_loader["catalog"]
        >>> conf_params = conf_loader["parameters"]

    ``OmegaConf`` supports variable interpolation in configuration
    https://omegaconf.readthedocs.io/en/2.2_branch/usage.html#merging-configurations. It is
    recommended to use this instead of yaml anchors with the ``OmegaConfigLoader``.

    This version of the ``OmegaConfigLoader`` does not support any of the built-in ``OmegaConf``
    resolvers. Support for resolvers might be added in future versions.

    To use this class, change the setting for the `CONFIG_LOADER_CLASS` constant
    in `settings.py`.

    Example:
    ::

        >>> # in settings.py
        >>> from kedro.config import OmegaConfigLoader
        >>>
        >>> CONFIG_LOADER_CLASS = OmegaConfigLoader

    """

    def __init__(  # noqa: PLR0913
        self,
        conf_source: str | Path,
        env: str | None = None,
        runtime_params: dict[str, Any] | None = None,
        *,
        config_patterns: dict[str, list[str]] | None = None,
        base_env: str | None = None,
        default_run_env: str | None = None,
        custom_resolvers: dict[str, Callable] | None = None,
        merge_strategy: dict[str, str] | None = None,
    ):
        if isinstance(conf_source, Path):
            conf_source = str(conf_source)
        """Instantiates a ``OmegaConfigLoader``.

        Args:
            conf_source: Path to use as root directory for loading configuration.
                This can be a local filesystem path or a remote URL with protocol
                (e.g., s3://, gs://, etc.)
            env: Environment that will take precedence over base.
            runtime_params: Extra parameters passed to a Kedro run.
            config_patterns: Regex patterns that specify the naming convention for configuration
                files so they can be loaded. Can be customised by supplying config_patterns as
                in `CONFIG_LOADER_ARGS` in `settings.py`.
            base_env: Name of the base environment. When the ``OmegaConfigLoader`` is used directly
                this defaults to `None`. Otherwise, the value will come from the `CONFIG_LOADER_ARGS` in the project
                settings, where base_env defaults to `"base"`.
                This is used in the `conf_paths` property method to construct
                the configuration paths.
            default_run_env: Name of the default run environment. When the ``OmegaConfigLoader`` is used directly
                this defaults to `None`. Otherwise, the value will come from the `CONFIG_LOADER_ARGS` in the project
                settings, where default_run_env defaults to `"local"`.
                Can be overridden by supplying the `env` argument.
            custom_resolvers: A dictionary of custom resolvers to be registered. For more information,
                see here: https://omegaconf.readthedocs.io/en/2.3_branch/custom_resolvers.html#custom-resolvers
            merge_strategy: A dictionary that specifies the merging strategy for each configuration type.
                The accepted merging strategies are `soft` and `destructive`. Defaults to `destructive`.
        """
        self.base_env = base_env or ""
        self.default_run_env = default_run_env or ""
        self.merge_strategy = merge_strategy or {}
        self._globals_oc: DictConfig | None = None
        self._runtime_params_oc: DictConfig | None = None
        self.config_patterns = {
            "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
            "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
            "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
            "globals": ["globals.yml"],
        }
        self.config_patterns.update(config_patterns or {})

        # Deactivate oc.env built-in resolver for OmegaConf
        OmegaConf.clear_resolver("oc.env")
        # Register user provided custom resolvers
        self._custom_resolvers = custom_resolvers
        if custom_resolvers:
            self._register_new_resolvers(custom_resolvers)
        # Register globals resolver
        self._register_globals_resolver()

        # Setup file system and protocol
        self._fs, self._protocol = self._initialise_filesystem_and_protocol(conf_source)

        # Store remote root path if using cloud protocol
        if self._protocol in CLOUD_PROTOCOLS or self._protocol in HTTP_PROTOCOLS:
            options = _parse_filepath(conf_source)
            self._remote_root_path = options["path"].rstrip("/")

        super().__init__(
            conf_source=conf_source,
            env=env,
            runtime_params=runtime_params,
        )
        try:
            self._globals = self["globals"]
        except MissingConfigException:
            self._globals = {}

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "globals":
            # Update the cached value at self._globals since it is used by the globals resolver
            self._globals = value
        super().__setitem__(key, value)

    def __getitem__(self, key: str) -> dict[str, Any]:  # noqa: PLR0912
        """Get configuration files by key, load and merge them, and
        return them in the form of a config dictionary.

        Args:
            key: Key of the configuration type to fetch.

        Raises:
            KeyError: If key provided isn't present in the config_patterns of this
               ``OmegaConfigLoader`` instance.
            MissingConfigException: If no configuration files exist matching the patterns
                mapped to the provided key.

        Returns:
            Dict[str, Any]:  A Python dictionary with the combined
               configuration from all configuration files.
        """
        # Allow bypassing of loading config from patterns if a key and value have been set
        # explicitly on the ``OmegaConfigLoader`` instance.

        # Re-register runtime params resolver incase it was previously deactivated
        self._register_runtime_params_resolver()

        if key in self:
            return super().__getitem__(key)  # type: ignore[no-any-return]

        if key not in self.config_patterns:
            raise KeyError(
                f"No config patterns were found for '{key}' in your config loader"
            )
        patterns = [*self.config_patterns[key]]

        if key == "globals":
            # "runtime_params" resolver is not allowed in globals.
            OmegaConf.clear_resolver("runtime_params")

        read_environment_variables = key == "credentials"

        processed_files: set[Path] = set()
        # Load base env config
        # Handle remote paths
        if self._protocol in CLOUD_PROTOCOLS or self._protocol in HTTP_PROTOCOLS:
            base_path = f"{self._remote_root_path}/{self.base_env}"
        elif self._protocol == "file":
            base_path = str(Path(self.conf_source) / self.base_env)
        else:
            base_path = str(Path(self._fs.ls("", detail=False)[-1]) / self.base_env)
        try:
            base_config = self.load_and_merge_dir_config(  # type: ignore[no-untyped-call]
                base_path, patterns, key, processed_files, read_environment_variables
            )
        except UnsupportedInterpolationType as exc:
            if "runtime_params" in str(exc):
                raise UnsupportedInterpolationType(
                    "The `runtime_params:` resolver is not supported for globals."
                )
            else:
                raise exc

        config = base_config

        # Load chosen env config
        run_env = self.env or self.default_run_env

        # Return if chosen env config is the same as base config to avoid loading the same config twice
        if run_env == self.base_env:
            return config  # type: ignore[no-any-return]

        # Handle remote paths
        if self._protocol in CLOUD_PROTOCOLS or self._protocol in HTTP_PROTOCOLS:
            env_path = f"{self._remote_root_path}/{run_env}"
        elif self._protocol == "file":
            env_path = str(Path(self.conf_source) / run_env)
        else:
            env_path = str(Path(self._fs.ls("", detail=False)[-1]) / run_env)
        try:
            env_config = self.load_and_merge_dir_config(  # type: ignore[no-untyped-call]
                env_path, patterns, key, processed_files, read_environment_variables
            )
        except UnsupportedInterpolationType as exc:
            if "runtime_params" in str(exc):
                raise UnsupportedInterpolationType(
                    "The `runtime_params:` resolver is not supported for globals."
                )
            else:
                raise exc

        resulting_config = self._merge_configs(config, env_config, key, env_path)

        if not processed_files and key != "globals":
            raise MissingConfigException(
                f"No files of YAML or JSON format found in {base_path} or {env_path} matching"
                f" the glob pattern(s): {[*self.config_patterns[key]]}"
            )

        return resulting_config  # type: ignore[no-any-return]

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"OmegaConfigLoader(conf_source={self.conf_source}, env={self.env}, "
            f"runtime_params={self.runtime_params}, "
            f"config_patterns={self.config_patterns}, "
            f"base_env={self.base_env}), "
            f"default_run_env={self.default_run_env}), "
            f"custom_resolvers={self._custom_resolvers}), "
            f"merge_strategy={self.merge_strategy})"
        )

    def keys(self) -> KeysView:
        return KeysView(self.config_patterns)

    @typing.no_type_check
    def load_and_merge_dir_config(
        self,
        conf_path: str,
        patterns: Iterable[str],
        key: str,
        processed_files: set,
        read_environment_variables: bool | None = False,
    ) -> dict[str, Any]:
        """Recursively load and merge all configuration files in a directory using OmegaConf,
        which satisfy a given list of glob patterns from a specific path.

        Args:
            conf_path: Path to configuration directory.
            patterns: List of glob patterns to match the filenames against.
            key: Key of the configuration type to fetch.
            processed_files: Set of files read for a given configuration type.
            read_environment_variables: Whether to resolve environment variables.

        Raises:
            MissingConfigException: If configuration path doesn't exist or isn't valid.
            ValueError: If two or more configuration files contain the same key(s).
            ParserError: If config file contains invalid YAML or JSON syntax.

        Returns:
            Resulting configuration dictionary.

        """
        # Handle directory existence check for remote paths
        if self._protocol in CLOUD_PROTOCOLS or self._protocol in HTTP_PROTOCOLS:
            try:
                # Check directory existence in remote paths
                self._fs.ls(conf_path)
            except Exception as exc:
                raise MissingConfigException(
                    f"Given configuration path either does not exist "
                    f"or is not a valid directory: {conf_path}. Error: {exc!s}"
                )
        # Original check for local paths
        elif not self._fs.isdir(Path(conf_path).as_posix()):
            raise MissingConfigException(
                f"Given configuration path either does not exist "
                f"or is not a valid directory: {conf_path}"
            )

        paths = []
        for pattern in patterns:
            for each in self._fs.glob(Path(f"{conf_path!s}/{pattern}").as_posix()):
                if not self._is_hidden(each):
                    paths.append(Path(each))

        deduplicated_paths = set(paths)
        config_files_filtered = [
            path for path in deduplicated_paths if self._is_valid_config_path(path)
        ]

        config_per_file = {}
        for config_filepath in config_files_filtered:
            try:
                with self._fs.open(str(config_filepath.as_posix())) as open_config:
                    # As fsspec doesn't allow the file to be read as StringIO,
                    # this is a workaround to read it as a binary file and decode it back to utf8.
                    tmp_fo = io.StringIO(open_config.read().decode("utf8"))
                    config = OmegaConf.load(tmp_fo)
                    processed_files.add(config_filepath)
                if read_environment_variables:
                    self._resolve_environment_variables(config)
                config_per_file[config_filepath] = config
            except (ParserError, ScannerError) as exc:
                line = exc.problem_mark.line
                cursor = exc.problem_mark.column
                raise ParserError(
                    f"Invalid YAML or JSON file {Path(config_filepath).as_posix()},"
                    f" unable to read line {line}, position {cursor}."
                ) from exc

        aggregate_config = config_per_file.values()
        self._check_duplicates(key, config_per_file)

        if not aggregate_config:
            return {}

        if key == "parameters":
            # Merge with runtime parameters only for "parameters"
            return OmegaConf.to_container(
                OmegaConf.merge(*aggregate_config, self.runtime_params), resolve=True
            )

        merged_config_container = OmegaConf.to_container(
            OmegaConf.merge(*aggregate_config), resolve=True
        )
        return {
            k: v for k, v in merged_config_container.items() if not k.startswith("_")
        }

    @staticmethod
    def _initialise_filesystem_and_protocol(
        conf_source: str,
    ) -> tuple[fsspec.AbstractFileSystem, str]:
        """Set up the file system based on the file type or protocol detected in conf_source."""
        # Force string for regex
        conf_source = str(conf_source)
        # Check if it's an archive file
        file_mimetype, _ = mimetypes.guess_type(conf_source)
        if file_mimetype == "application/x-tar":
            return fsspec.filesystem(protocol="tar", fo=conf_source), "tar"
        elif file_mimetype in (
            "application/zip",
            "application/x-zip-compressed",
            "application/zip-compressed",
        ):
            return fsspec.filesystem(protocol="zip", fo=conf_source), "zip"

        # Parse to check for protocol
        options = _parse_filepath(conf_source)
        protocol = options["protocol"]

        # Create and return the appropriate filesystem
        if protocol in HTTP_PROTOCOLS or protocol in CLOUD_PROTOCOLS:
            # For HTTP and cloud storage protocols, create the appropriate filesystem
            return fsspec.filesystem(protocol=protocol), protocol
        else:
            # Default to local filesystem
            return fsspec.filesystem(protocol="file", fo=conf_source), "file"

    def _merge_configs(
        self,
        config: dict[str, Any],
        env_config: dict[str, Any],
        key: str,
        env_path: str,
    ) -> Any:
        merging_strategy = self.merge_strategy.get(key, "destructive")
        try:
            strategy = MergeStrategies[merging_strategy.upper()]

            # Get the corresponding merge function and call it
            merge_function_name = MERGING_IMPLEMENTATIONS[strategy]
            merge_function = getattr(self, merge_function_name)
            return merge_function(config, env_config, env_path)
        except KeyError:
            allowed_strategies = [strategy.name.lower() for strategy in MergeStrategies]
            raise ValueError(
                f"Merging strategy {merging_strategy} not supported. The accepted merging "
                f"strategies are {allowed_strategies}."
            )

    def _get_all_keys(self, cfg: Any, parent_key: str = "") -> set[str]:
        keys: set[str] = set()

        for key, value in cfg.items():
            full_key = f"{parent_key}.{key}" if parent_key else key
            if isinstance(value, dict):
                keys.update(self._get_all_keys(value, full_key))
            else:
                keys.add(full_key)
        return keys

    def _is_valid_config_path(self, path: Path) -> bool:
        """Check if given path is a file path and file type is yaml or json."""
        posix_path = path.as_posix()
        return self._fs.isfile(str(posix_path)) and path.suffix in [
            ".yml",
            ".yaml",
            ".json",
        ]

    def _register_globals_resolver(self) -> None:
        """Register the globals resolver"""
        OmegaConf.register_new_resolver(
            "globals",
            self._get_globals_value,
            replace=True,
        )

    def _register_runtime_params_resolver(self) -> None:
        OmegaConf.register_new_resolver(
            "runtime_params",
            self._get_runtime_value,
            replace=True,
        )

    def _get_globals_value(self, variable: str, default_value: Any = _NO_VALUE) -> Any:
        """Return the globals values to the resolver"""
        if variable.startswith("_"):
            raise InterpolationResolutionError(
                "Keys starting with '_' are not supported for globals."
            )

        if not self._globals_oc:
            self._globals_oc = OmegaConf.create(self._globals)

        interpolated_value = OmegaConf.select(
            self._globals_oc, variable, default=default_value
        )
        if interpolated_value != _NO_VALUE:
            return interpolated_value
        else:
            raise InterpolationResolutionError(
                f"Globals key '{variable}' not found and no default value provided."
            )

    def _get_runtime_value(self, variable: str, default_value: Any = _NO_VALUE) -> Any:
        """Return the runtime params values to the resolver"""
        if not self._runtime_params_oc:
            self._runtime_params_oc = OmegaConf.create(self.runtime_params)

        interpolated_value = OmegaConf.select(
            self._runtime_params_oc, variable, default=default_value
        )
        if interpolated_value != _NO_VALUE:
            return interpolated_value
        else:
            raise InterpolationResolutionError(
                f"Runtime parameter '{variable}' not found and no default value provided."
            )

    @staticmethod
    def _register_new_resolvers(resolvers: dict[str, Callable]) -> None:
        """Register custom resolvers"""
        for name, resolver in resolvers.items():
            if not OmegaConf.has_resolver(name):
                msg = f"Registering new custom resolver: {name}"
                _config_logger.debug(msg)
                OmegaConf.register_new_resolver(name=name, resolver=resolver)

    def _check_duplicates(self, key: str, config_per_file: dict[Path, Any]) -> None:
        if key == "parameters":
            seen_files_to_keys = {
                file: self._get_all_keys(OmegaConf.to_container(config, resolve=False))
                for file, config in config_per_file.items()
            }
        else:
            seen_files_to_keys = {
                file: set(config.keys()) for file, config in config_per_file.items()
            }

        duplicates = []

        filepaths = list(seen_files_to_keys.keys())
        for i, filepath1 in enumerate(filepaths, 1):
            config1 = seen_files_to_keys[filepath1]
            for filepath2 in filepaths[i:]:
                config2 = seen_files_to_keys[filepath2]

                combined_keys = config1 & config2
                overlapping_keys = {
                    key for key in combined_keys if not key.startswith("_")
                }

                if overlapping_keys:
                    sorted_keys = ", ".join(sorted(overlapping_keys))
                    if len(sorted_keys) > 100:  # noqa: PLR2004
                        sorted_keys = sorted_keys[:100] + "..."
                    duplicates.append(
                        f"Duplicate keys found in {filepath1} and {filepath2}: {sorted_keys}"
                    )

        if duplicates:
            dup_str = "\n".join(duplicates)
            raise ValueError(f"{dup_str}")

    @staticmethod
    def _resolve_environment_variables(config: DictConfig) -> None:
        """Use the ``oc.env`` resolver to read environment variables and replace
        them in-place, clearing the resolver after the operation is complete if
        it was not registered beforehand.

        Arguments:
            config {Dict[str, Any]} -- The configuration dictionary to resolve.
        """
        if not OmegaConf.has_resolver("oc.env"):
            OmegaConf.register_new_resolver("oc.env", oc.env)
            OmegaConf.resolve(config)
            OmegaConf.clear_resolver("oc.env")
        else:
            OmegaConf.resolve(config)

    @staticmethod
    def _destructive_merge(
        config: dict[str, Any], env_config: dict[str, Any], env_path: str
    ) -> dict[str, Any]:
        # Destructively merge the two env dirs. The chosen env will override base.
        common_keys = config.keys() & env_config.keys()
        if common_keys:
            sorted_keys = ", ".join(sorted(common_keys))
            msg = (
                "Config from path '%s' will override the following "
                "existing top-level config keys: %s"
            )
            _config_logger.debug(msg, env_path, sorted_keys)

        config.update(env_config)
        return config

    @staticmethod
    def _soft_merge(
        config: dict[str, Any], env_config: dict[str, Any], env_path: str | None = None
    ) -> Any:
        # Soft merge the two env dirs. The chosen env will override base if keys clash.
        return OmegaConf.to_container(OmegaConf.merge(config, env_config))

    def _is_hidden(self, path_str: str) -> bool:
        """Check if path contains any hidden directory or is a hidden file"""
        path = Path(path_str)
        conf_path = Path(self.conf_source).resolve().as_posix()
        if self._protocol == "file":
            path = path.resolve()
        posix_path = path.as_posix()
        if posix_path.startswith(conf_path):
            posix_path = posix_path.replace(conf_path, "")
        parts = posix_path.split(self._fs.sep)  # filesystem specific separator
        HIDDEN = "."
        # Check if any component (folder or file) starts with a dot (.)
        return any(part.startswith(HIDDEN) for part in parts)
