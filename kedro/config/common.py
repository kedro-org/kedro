"""This module contains methods and facade interfaces for various ConfigLoader
implementations.
"""
from __future__ import annotations

import logging
from glob import iglob
from pathlib import Path
from typing import AbstractSet, Any, Iterable
from warnings import warn

from yaml.parser import ParserError

from kedro.config.abstract_config import BadConfigException, MissingConfigException

SUPPORTED_EXTENSIONS = [
    ".yml",
    ".yaml",
    ".json",
    ".ini",
    ".pickle",
    ".properties",
    ".xml",
]
_config_logger = logging.getLogger(__name__)


def _get_config_from_patterns(
    conf_paths: Iterable[str],
    patterns: Iterable[str] = None,
    ac_template: bool = False,
    ac_context: dict[str, Any] = None,
) -> dict[str, Any]:
    """Recursively scan for configuration files, load and merge them, and
    return them in the form of a config dictionary.

    Args:
        conf_paths: List of configuration paths to directories
        patterns: Glob patterns to match. Files, which names match
            any of the specified patterns, will be processed.
        ac_template: Boolean flag to indicate whether to use the `ac_template`
            argument of the ``anyconfig.load`` method. Used in the context of
            `_load_config_file` function.
        ac_context: anyconfig context to pass to ``anyconfig.load`` method.
            Used in the context of `_load_config_file` function.

    Raises:
        ValueError: If 2 or more configuration files inside the same
            config path (or its subdirectories) contain the same
            top-level key.
        MissingConfigException: If no configuration files exist within
            a specified config path.
        BadConfigException: If configuration is poorly formatted and
            cannot be loaded.

    Returns:
        Dict[str, Any]:  A Python dictionary with the combined
            configuration from all configuration files. **Note:** any keys
            that start with `_` will be ignored.
    """

    if not patterns:
        raise ValueError(
            "'patterns' must contain at least one glob "
            "pattern to match config filenames against."
        )

    config: dict[str, Any] = {}
    processed_files: set[Path] = set()

    for conf_path in conf_paths:
        if not Path(conf_path).is_dir():
            raise ValueError(
                f"Given configuration path either does not exist "
                f"or is not a valid directory: {conf_path}"
            )

        config_filepaths = _lookup_config_filepaths(
            Path(conf_path), patterns, processed_files, _config_logger
        )
        new_conf = _load_configs(
            config_filepaths=config_filepaths,
            ac_template=ac_template,
            ac_context=ac_context,
        )

        common_keys = config.keys() & new_conf.keys()
        if common_keys:
            sorted_keys = ", ".join(sorted(common_keys))
            msg = (
                "Config from path [magenta]%s[/magenta] will override the "
                "following existing top-level config keys: '%s'"
            )
            _config_logger.info(msg, conf_path, sorted_keys, extra={"markup": True})

        config.update(new_conf)
        processed_files |= set(config_filepaths)

    if not processed_files:
        raise MissingConfigException(
            f"No files found in {conf_paths} matching the glob "
            f"pattern(s): {patterns}"
        )
    return config


def _load_config_file(
    config_file: Path, ac_template: bool = False, ac_context: dict[str, Any] = None
) -> dict[str, Any]:
    """Load an individual config file using `anyconfig` as a backend.

    Args:
        config_file: Path to a config file to process.
        ac_template: Boolean flag to indicate whether to use the `ac_template`
            argument of the ``anyconfig.load`` method.
        ac_context: anyconfig context to pass to ``anyconfig.load`` method.

    Raises:
        BadConfigException: If configuration is poorly formatted and
            cannot be loaded.
        ParserError: If file is invalid and cannot be parsed.

    Returns:
        Parsed configuration.
    """
    # for performance reasons
    import anyconfig  # noqa: import-outside-toplevel

    try:
        # Default to UTF-8, which is Python 3 default encoding, to decode the file
        with open(config_file, encoding="utf8") as yml:
            _config_logger.debug(
                "Loading config file: [bright magenta]%s[/bright magenta]",
                config_file,
                extra={"markup": True},
            )
            return {
                k: v
                for k, v in anyconfig.load(
                    yml, ac_template=ac_template, ac_context=ac_context
                ).items()
                if not k.startswith("_")
            }
    except AttributeError as exc:
        raise BadConfigException(f"Couldn't load config file: {config_file}") from exc

    except ParserError as exc:
        assert exc.problem_mark is not None
        line = exc.problem_mark.line
        cursor = exc.problem_mark.column
        raise ParserError(
            f"Invalid YAML file {config_file}, unable to read line {line}, position {cursor}."
        ) from exc


def _load_configs(
    config_filepaths: list[Path], ac_template: bool, ac_context: dict[str, Any] = None
) -> dict[str, Any]:
    """Recursively load all configuration files, which satisfy
    a given list of glob patterns from a specific path.

    Args:
        config_filepaths: Configuration files sorted in the order of precedence.
        ac_template: Boolean flag to indicate whether to use the `ac_template`
            argument of the ``anyconfig.load`` method. Used in the context of
            `_load_config_file` function.
        ac_context: anyconfig context to pass to ``anyconfig.load`` method.
            Used in the context of `_load_config_file` function.

    Raises:
        ValueError: If 2 or more configuration files contain the same key(s).
        BadConfigException: If configuration is poorly formatted and
            cannot be loaded.

    Returns:
        Resulting configuration dictionary.

    """

    aggregate_config = {}
    seen_file_to_keys: dict[Path, AbstractSet[str]] = {}

    for config_filepath in config_filepaths:
        single_config = _load_config_file(
            config_filepath, ac_template=ac_template, ac_context=ac_context
        )
        _check_duplicate_keys(seen_file_to_keys, config_filepath, single_config)
        seen_file_to_keys[config_filepath] = single_config.keys()
        aggregate_config.update(single_config)

    return aggregate_config


def _lookup_config_filepaths(
    conf_path: Path,
    patterns: Iterable[str],
    processed_files: set[Path],
    logger: Any,
) -> list[Path]:
    config_files = _path_lookup(conf_path, patterns)

    seen_files = config_files & processed_files
    if seen_files:
        logger.warning(
            "Config file(s): %s already processed, skipping loading...",
            ", ".join(str(seen) for seen in sorted(seen_files)),
        )
        config_files -= seen_files

    return sorted(config_files)


def _remove_duplicates(items: Iterable[str]):
    """Remove duplicates while preserving the order."""
    unique_items: list[str] = []
    for item in items:
        if item not in unique_items:
            unique_items.append(item)
        else:
            warn(
                f"Duplicate environment detected! "
                f"Skipping re-loading from configuration path: {item}"
            )
    return unique_items


def _check_duplicate_keys(
    processed_files: dict[Path, AbstractSet[str]], filepath: Path, conf: dict[str, Any]
) -> None:
    duplicates = []

    for processed_file, keys in processed_files.items():
        overlapping_keys = conf.keys() & keys

        if overlapping_keys:
            sorted_keys = ", ".join(sorted(overlapping_keys))
            if len(sorted_keys) > 100:  # noqa: PLR2004
                sorted_keys = sorted_keys[:100] + "..."
            duplicates.append(f"{processed_file}: {sorted_keys}")

    if duplicates:
        dup_str = "\n- ".join(duplicates)
        raise ValueError(f"Duplicate keys found in {filepath} and:\n- {dup_str}")


def _path_lookup(conf_path: Path, patterns: Iterable[str]) -> set[Path]:
    """Return a set of all configuration files from ``conf_path`` or
    its subdirectories, which satisfy a given list of glob patterns.

    Args:
        conf_path: Path to configuration directory.
        patterns: List of glob patterns to match the filenames against.

    Returns:
        A set of paths to configuration files.

    """
    config_files = set()
    conf_path = conf_path.resolve()

    for pattern in patterns:
        # `Path.glob()` ignores the files if pattern ends with "**",
        # therefore iglob is used instead
        for each in iglob(str(conf_path / pattern), recursive=True):
            path = Path(each).resolve()
            if path.is_file() and path.suffix in SUPPORTED_EXTENSIONS:
                config_files.add(path)

    return config_files
