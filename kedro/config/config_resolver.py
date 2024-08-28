import copy
import logging
import re
from typing import Any

from parse import parse

Patterns = dict[str, dict[str, Any]]

CREDENTIALS_KEY = "credentials"


def _get_credentials(credentials_name: str, credentials: dict[str, Any]) -> Any:
    """Return a set of credentials from the provided credentials dict.

    Args:
        credentials_name: Credentials name.
        credentials: A dictionary with all credentials.

    Returns:
        The set of requested credentials.

    Raises:
        KeyError: When a data set with the given name has not yet been
            registered.

    """
    try:
        return credentials[credentials_name]
    except KeyError as exc:
        raise KeyError(
            f"Unable to find credentials '{credentials_name}': check your data "
            "catalog and credentials configuration. See "
            "https://kedro.readthedocs.io/en/stable/kedro.io.DataCatalog.html "
            "for an example."
        ) from exc


def _resolve_credentials(
    config: dict[str, Any], credentials: dict[str, Any] | None
) -> dict[str, Any]:
    """Return the dataset configuration where credentials are resolved using
    credentials dictionary provided.

    Args:
        config: Original dataset config, which may contain unresolved credentials.
        credentials: A dictionary with all credentials.

    Returns:
        The dataset config, where all the credentials are successfully resolved.
    """
    config = copy.deepcopy(config)

    def _map_value(key: str, value: Any) -> Any:
        if key == CREDENTIALS_KEY and isinstance(value, str):
            return _get_credentials(value, credentials)
        if isinstance(value, dict):
            return {k: _map_value(k, v) for k, v in value.items()}
        return value

    return {k: _map_value(k, v) for k, v in config.items()}


def _resolve_config(
    ds_name: str,
    matched_pattern: str,
    config: dict,
) -> dict[str, Any]:
    """Get resolved AbstractDataset from a factory config"""
    result = parse(matched_pattern, ds_name)
    # Resolve the factory config for the dataset
    if isinstance(config, dict):
        for key, value in config.items():
            config[key] = _resolve_config(ds_name, matched_pattern, value)
    elif isinstance(config, (list, tuple)):
        config = [_resolve_config(ds_name, matched_pattern, value) for value in config]
    elif isinstance(config, str) and "}" in config:
        try:
            config = str(config).format_map(result.named)
        except KeyError as exc:
            raise KeyError(
                f"Unable to resolve '{config}' from the pattern '{matched_pattern}'. Keys used in the configuration "
                f"should be present in the dataset factory pattern."
            ) from exc
    return config


class ConfigResolver:
    def __init__(
        self,
        config: dict[str, dict[str, Any]],
        credentials: dict[str, dict[str, Any]] | None = None,
    ):
        self._runtime_patterns = {}
        self._dataset_patterns, self._default_pattern = self._get_patterns(
            config, credentials
        )

        self._ds_configs = self._get_ds_configs(config, credentials)

    @property
    def config(self):
        return copy.deepcopy(self._ds_configs)

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @staticmethod
    def _is_pattern(pattern: str) -> bool:
        """Check if a given string is a pattern. Assume that any name with '{' is a pattern."""
        return "{" in pattern

    @staticmethod
    def _specificity(pattern: str) -> int:
        """Helper function to check the length of exactly matched characters not inside brackets."""
        # Remove all the placeholders from the pattern and count the number of remaining chars
        result = re.sub(r"\{.*?\}", "", pattern)
        return len(result)

    @classmethod
    def _sort_patterns(cls, dataset_patterns: Patterns) -> dict[str, dict[str, Any]]:
        """Sort a dictionary of dataset patterns according to parsing rules.

        In order:

        1. Decreasing specificity (number of characters outside the curly brackets)
        2. Decreasing number of placeholders (number of curly bracket pairs)
        3. Alphabetically
        """
        sorted_keys = sorted(
            dataset_patterns,
            key=lambda pattern: (
                -(cls._specificity(pattern)),
                -pattern.count("{"),
                pattern,
            ),
        )
        catch_all = [
            pattern for pattern in sorted_keys if cls._specificity(pattern) == 0
        ]
        if len(catch_all) > 1:
            raise ValueError(
                f"Multiple catch-all patterns found in the catalog: {', '.join(catch_all)}. Only one catch-all pattern is allowed, remove the extras."
            )
        return {key: dataset_patterns[key] for key in sorted_keys}

    def match_pattern(self, ds_name: str) -> str | None:
        """Match a dataset name against patterns in a dictionary."""
        all_patterns = list(self._dataset_patterns.keys())
        all_patterns.extend(list(self._default_pattern.keys()))
        all_patterns.extend(list(self._runtime_patterns.keys()))
        matches = (pattern for pattern in all_patterns if parse(pattern, ds_name))
        return next(matches, None)

    @classmethod
    def _get_patterns(
        cls,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> tuple[Patterns, Patterns]:
        dataset_patterns = {}
        config = copy.deepcopy(config) or {}
        credentials = copy.deepcopy(credentials) or {}
        user_default = {}

        for ds_name, ds_config in config.items():
            if cls._is_pattern(ds_name):
                resolved_ds_config = _resolve_credentials(ds_config, credentials)
                dataset_patterns[ds_name] = resolved_ds_config

        sorted_patterns = cls._sort_patterns(dataset_patterns)
        if sorted_patterns:
            # If the last pattern is a catch-all pattern, pop it and set it as the default
            if cls._specificity(list(sorted_patterns.keys())[-1]) == 0:
                last_pattern = sorted_patterns.popitem()
                user_default = {last_pattern[0]: last_pattern[1]}

        return sorted_patterns, user_default

    def _get_ds_configs(
        self,
        config: dict[str, dict[str, Any]],
        credentials: dict[str, dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        config = copy.deepcopy(config) or {}
        credentials = copy.deepcopy(credentials) or {}
        ds_configs = {}
        for ds_name, ds_config in config.items():
            if not self._is_pattern(ds_name):
                ds_configs[ds_name] = _resolve_credentials(ds_config, credentials)

        return ds_configs

    def resolve_patterns(
        self, datasets: str | list[str]
    ) -> dict[str, Any] | list[dict[str, Any]]:
        if isinstance(datasets, str):
            datasets_lst = [datasets]
        else:
            datasets_lst = datasets

        resolved_configs = []

        for ds_name in datasets_lst:
            matched_pattern = self.match_pattern(ds_name)
            if matched_pattern and ds_name not in self._ds_configs:
                # If the dataset is a patterned dataset, materialise it and add it to
                # the catalog
                config_copy = copy.deepcopy(
                    self._dataset_patterns.get(matched_pattern)
                    or self._default_pattern.get(matched_pattern)
                    or self._runtime_patterns.get(matched_pattern)
                    or {}
                )
                ds_config = _resolve_config(ds_name, matched_pattern, config_copy)

                if (
                    self._specificity(matched_pattern) == 0
                    and matched_pattern in self._default_pattern
                ):
                    self._logger.warning(
                        "Config from the dataset factory pattern '%s' in the catalog will be used to "
                        "override the default dataset creation for '%s'",
                        matched_pattern,
                        ds_name,
                    )
                resolved_configs.append(ds_config)
            elif ds_name in self._ds_configs:
                resolved_configs.append(self._ds_configs.get(ds_name))
            else:
                resolved_configs.append(None)

        if isinstance(datasets, str):
            return resolved_configs[0]
        else:
            return resolved_configs

    def add_runtime_patterns(self, dataset_patterns: Patterns) -> None:
        self._runtime_patterns = {**self._runtime_patterns, **dataset_patterns}
        self._runtime_patterns = self._sort_patterns(self._runtime_patterns)
