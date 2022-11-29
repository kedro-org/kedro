"""This module provides ``kedro.config`` with the functionality to load one
or more configuration files of yaml or json type from specified paths through OmegaConf.
"""
import logging
from pathlib import Path
from typing import AbstractSet, Any, Dict, Iterable, List, Set  # noqa

from omegaconf import OmegaConf
from yaml.parser import ParserError
from yaml.scanner import ScannerError

from kedro.config import AbstractConfigLoader, MissingConfigException
from kedro.config.common import (
    _check_duplicate_keys,
    _lookup_config_filepaths,
    _remove_duplicates,
)

_config_logger = logging.getLogger(__name__)


class OmegaConfLoader(AbstractConfigLoader):
    """Recursively scan directories (config paths) contained in ``conf_source`` for
    configuration files with a ``yaml``, ``yml`` or ``json`` extension, load and merge
    them through OmegaConf and return them in the form of a config dictionary.

    The first processed config path is the ``base`` directory inside
    ``conf_source``. The optional ``env`` argument can be used to specify a
    subdirectory of ``conf_source`` to process as a config path after ``base``.

    When the same top-level key appears in any 2 config files located in
    the same (sub)directory, a ``ValueError`` is raised.

    When the same key appears in any 2 config files located in different
    (sub)directories, the last processed config path takes precedence
    and overrides this key.

    You can access the different configurations as follows:
    ::

        >>> import logging.config
        >>> from kedro.config import OmegaConfLoader
        >>> from kedro.framework.project import settings
        >>>
        >>> conf_path = str(project_path / settings.CONF_SOURCE)
        >>> conf_loader = OmegaConfLoader(conf_source=conf_path, env="local")
        >>>
        >>> conf_logging = conf_loader["logging"]
        >>> logging.config.dictConfig(conf_logging)  # set logging conf
        >>>
        >>> conf_catalog = conf_loader["catalog"]
        >>> conf_params = conf_loader["parameters"]


    """

    def __init__(
        self,
        conf_source: str,
        env: str = None,
        runtime_params: Dict[str, Any] = None,
        config_patterns: Dict[str, List[str]] = None,
        *,
        base_env: str = "base",
        default_run_env: str = "local",
    ):
        """Instantiates a ``OmegaConfLoader``.

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
            default_run_env: Name of the base environment. Defaults to `"local"`.
                This is used in the `conf_paths` property method to construct
                the configuration paths. Can be overriden by supplying the `env` argument.
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

        super().__init__(
            conf_source=conf_source,
            env=env,
            runtime_params=runtime_params,
        )

    def __getitem__(self, key):
        return self.get(*self.config_patterns[key])

    def __repr__(self):  # pragma: no cover
        return (
            f"OmegaConfLoader(conf_source={self.conf_source}, env={self.env}, "
            f"config_patterns={self.config_patterns})"
        )

    @property
    def conf_paths(self):
        """Property method to return deduplicated configuration paths."""
        return _remove_duplicates(self._build_conf_paths())

    def get(self, *patterns: str) -> Dict[str, Any]:  # type: ignore
        return _get_config_from_patterns_omegaconf(
            conf_paths=self.conf_paths, patterns=list(patterns)
        )

    def _build_conf_paths(self) -> Iterable[str]:
        run_env = self.env or self.default_run_env
        return [
            str(Path(self.conf_source) / self.base_env),
            str(Path(self.conf_source) / run_env),
        ]


def _get_config_from_patterns_omegaconf(
    conf_paths: Iterable[str],
    patterns: Iterable[str] = None,
) -> Dict[str, Any]:
    """Recursively scan for configuration files, load and merge them using OmegaConf, and
    return them in the form of a config dictionary.

    Args:
        conf_paths: List of configuration paths to directories
        patterns: Glob patterns to match. Files, which names match
            any of the specified patterns, will be processed.

    Raises:
        ValueError: If 2 or more configuration files inside the same
            config path (or its subdirectories) contain the same
            top-level key.
        MissingConfigException: If no configuration files exist within
            a specified config path.
        ParserError: If configuration is poorly formatted and
            cannot be loaded.

    Returns:
        Dict[str, Any]:  A Python dictionary with the combined
            configuration from all configuration files.
    """

    if not patterns:
        raise ValueError(
            "'patterns' must contain at least one glob "
            "pattern to match config filenames against."
        )

    aggregate_config = []
    processed_files = set()  # type: Set[Path]

    for conf_path in conf_paths:
        if not Path(conf_path).is_dir():
            raise ValueError(
                f"Given configuration path either does not exist "
                f"or is not a valid directory: {conf_path}"
            )

        config_filepaths = _lookup_config_filepaths(
            Path(conf_path), patterns, processed_files, _config_logger, True
        )

        new_conf = _load_configs_omegaconf(config_filepaths=config_filepaths)

        aggregate_config.append(new_conf)
        processed_files |= set(config_filepaths)

    if not processed_files:
        raise MissingConfigException(
            f"No files of YAML or JSON format found in {conf_paths} matching the glob "
            f"pattern(s): {patterns}"
        )
    return dict(OmegaConf.merge(*aggregate_config))


def _load_configs_omegaconf(config_filepaths: List[Path]) -> Dict[str, Any]:
    """Recursively load and merge all configuration files using OmegaConf, which satisfy
    a given list of glob patterns from a specific path.

    Args:
        config_filepaths: Configuration files sorted in the order of precedence.

    Raises:
        ValueError: If 2 or more configuration files contain the same key(s).
        BadConfigException: If configuration is poorly formatted and
            cannot be loaded.

    Returns:
        Resulting configuration dictionary.

    """

    config = {}
    aggregate_config = []
    seen_file_to_keys = {}  # type: Dict[Path, AbstractSet[str]]

    for config_filepath in config_filepaths:
        try:
            single_config = OmegaConf.load(config_filepath)
            config = single_config
        except (ParserError, ScannerError) as exc:
            assert exc.problem_mark is not None
            line = exc.problem_mark.line
            cursor = exc.problem_mark.column
            raise ParserError(
                f"Invalid YAML file {config_filepath}, unable to read line {line}, "
                f"position {cursor}."
            ) from exc

        _check_duplicate_keys(seen_file_to_keys, config_filepath, dict(single_config))
        seen_file_to_keys[config_filepath] = single_config.keys()
        aggregate_config.append(single_config)

    if len(aggregate_config) > 1:
        return dict(OmegaConf.merge(*aggregate_config))

    return config
