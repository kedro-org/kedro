"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files of yaml or json type from specified paths through OmegaConf.
"""
import io
import logging
import mimetypes
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set  # noqa

import fsspec
from omegaconf import OmegaConf
from omegaconf.resolvers import oc
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from kedro.config.abstract_config import AbstractConfigLoader, MissingConfigException

_config_logger = logging.getLogger(__name__)


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
        >>> conf_logging = conf_loader["logging"]
        >>> logging.config.dictConfig(conf_logging)  # set logging conf
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

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        *,
        config_patterns: Dict[str, List[str]] = None,
        base_env: str = "base",
        default_run_env: str = "local",
    ):
        """Instantiates a ``OmegaConfigLoader``.

        Args:
            conf_source: Path to use as root directory for loading configuration.
            env: Environment that will take precedence over base.
            runtime_params: Extra parameters passed to a Kedro run.
            config_patterns: Regex patterns that specify the naming convention for configuration
                files so they can be loaded. Can be customised by supplying config_patterns as
                in `CONFIG_LOADER_ARGS` in `settings.py`.
            base_env: Name of the base environment. Defaults to `"base"`.
                This is used in the `conf_paths` property method to construct
                the configuration paths.
            default_run_env: Name of the default run environment. Defaults to `"local"`.
                Can be overridden by supplying the `env` argument.
        """
        self.base_env = base_env
        self.default_run_env = default_run_env

        self.config_patterns = {
            "catalog": ["catalog*", "catalog*/**", "**/catalog*"],
            "parameters": ["parameters*", "parameters*/**", "**/parameters*"],
            "credentials": ["credentials*", "credentials*/**", "**/credentials*"],
            "logging": ["logging*", "logging*/**", "**/logging*"],
        }
        self.config_patterns.update(config_patterns or {})

        # In the first iteration of the OmegaConfigLoader we'll keep the resolver turned-off.
        # It's easier to introduce them step by step, but removing them would be a breaking change.
        self._clear_omegaconf_resolvers()

        file_mimetype, _ = mimetypes.guess_type(conf_source)
        if file_mimetype == "application/x-tar":
            self._protocol = "tar"
        elif file_mimetype in (
            "application/zip",
            "application/x-zip-compressed",
            "application/zip-compressed",
        ):
            self._protocol = "zip"
        else:
            self._protocol = "file"
        self._fs = fsspec.filesystem(protocol=self._protocol, fo=conf_source)

        super().__init__(
            conf_source=conf_source,
            env=env,
            runtime_params=runtime_params,
        )

    def __getitem__(self, key) -> Dict[str, Any]:
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
        if key in self:
            return super().__getitem__(key)

        if key not in self.config_patterns:
            raise KeyError(
                f"No config patterns were found for '{key}' in your config loader"
            )
        patterns = [*self.config_patterns[key]]

        read_environment_variables = key == "credentials"

        # Load base env config
        if self._protocol == "file":
            base_path = str(Path(self.conf_source) / self.base_env)
        else:
            base_path = str(Path(self._fs.ls("", detail=False)[-1]) / self.base_env)
        base_config = self.load_and_merge_dir_config(
            base_path, patterns, read_environment_variables
        )
        config = base_config

        # Load chosen env config
        run_env = self.env or self.default_run_env
        if self._protocol == "file":
            env_path = str(Path(self.conf_source) / run_env)
        else:
            env_path = str(Path(self._fs.ls("", detail=False)[-1]) / run_env)
        env_config = self.load_and_merge_dir_config(
            env_path, patterns, read_environment_variables
        )

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

        if not config:
            raise MissingConfigException(
                f"No files of YAML or JSON format found in {base_path} or {env_path} matching"
                f" the glob pattern(s): {[*self.config_patterns[key]]}"
            )
        return config

    def __repr__(self):  # pragma: no cover
        return (
            f"OmegaConfigLoader(conf_source={self.conf_source}, env={self.env}, "
            f"config_patterns={self.config_patterns})"
        )

    def load_and_merge_dir_config(
        self,
        conf_path: str,
        patterns: Iterable[str],
        read_environment_variables: Optional[bool] = False,
    ) -> Dict[str, Any]:
        """Recursively load and merge all configuration files in a directory using OmegaConf,
        which satisfy a given list of glob patterns from a specific path.

        Args:
            conf_path: Path to configuration directory.
            patterns: List of glob patterns to match the filenames against.
            read_environment_variables: Whether to resolve environment variables.

        Raises:
            MissingConfigException: If configuration path doesn't exist or isn't valid.
            ValueError: If two or more configuration files contain the same key(s).
            ParserError: If config file contains invalid YAML or JSON syntax.

        Returns:
            Resulting configuration dictionary.

        """
        # pylint: disable=too-many-locals

        if not self._fs.isdir(Path(conf_path).as_posix()):
            raise MissingConfigException(
                f"Given configuration path either does not exist "
                f"or is not a valid directory: {conf_path}"
            )

        paths = [
            Path(each)
            for pattern in patterns
            for each in self._fs.glob(Path(f"{str(conf_path)}/{pattern}").as_posix())
        ]
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
                if read_environment_variables:
                    self._resolve_environment_variables(config)
                config_per_file[config_filepath] = config
            except (ParserError, ScannerError) as exc:
                line = exc.problem_mark.line  # type: ignore
                cursor = exc.problem_mark.column  # type: ignore
                raise ParserError(
                    f"Invalid YAML or JSON file {Path(conf_path, config_filepath.name).as_posix()},"
                    f" unable to read line {line}, position {cursor}."
                ) from exc

        seen_file_to_keys = {
            file: set(config.keys()) for file, config in config_per_file.items()
        }
        aggregate_config = config_per_file.values()
        self._check_duplicates(seen_file_to_keys)

        if not aggregate_config:
            return {}
        if len(aggregate_config) == 1:
            return list(aggregate_config)[0]
        return dict(OmegaConf.merge(*aggregate_config))

    def _is_valid_config_path(self, path):
        """Check if given path is a file path and file type is yaml or json."""
        posix_path = path.as_posix()
        return self._fs.isfile(str(posix_path)) and path.suffix in [
            ".yml",
            ".yaml",
            ".json",
        ]

    @staticmethod
    def _check_duplicates(seen_files_to_keys: Dict[Path, Set[Any]]):
        duplicates = []

        filepaths = list(seen_files_to_keys.keys())
        for i, filepath1 in enumerate(filepaths, 1):
            config1 = seen_files_to_keys[filepath1]
            for filepath2 in filepaths[i:]:
                config2 = seen_files_to_keys[filepath2]

                overlapping_keys = config1 & config2

                if overlapping_keys:
                    sorted_keys = ", ".join(sorted(overlapping_keys))
                    if len(sorted_keys) > 100:
                        sorted_keys = sorted_keys[:100] + "..."
                    duplicates.append(
                        f"Duplicate keys found in {filepath1} and {filepath2}: {sorted_keys}"
                    )

        if duplicates:
            dup_str = "\n".join(duplicates)
            raise ValueError(f"{dup_str}")

    @staticmethod
    def _resolve_environment_variables(config: Dict[str, Any]) -> None:
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
    def _clear_omegaconf_resolvers():
        """Clear the built-in OmegaConf resolvers."""
        OmegaConf.clear_resolver("oc.env")
        OmegaConf.clear_resolver("oc.create")
        OmegaConf.clear_resolver("oc.deprecated")
        OmegaConf.clear_resolver("oc.decode")
        OmegaConf.clear_resolver("oc.select")
        OmegaConf.clear_resolver("oc.dict.keys")
        OmegaConf.clear_resolver("oc.dict.values")
