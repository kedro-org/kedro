"""``CatalogConfigResolver`` resolves dataset configurations and datasets'
patterns based on catalog configuration and credentials provided.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import Any

from parse import parse

from kedro.io.core import DatasetError

Patterns = dict[str, dict[str, Any]]

CREDENTIALS_KEY = "credentials"


class CatalogConfigResolver:
    """Resolves dataset configurations based on patterns and credentials."""

    def __init__(
        self,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
    ):
        self._runtime_patterns: Patterns = {}
        self._dataset_patterns, self._default_pattern = self._extract_patterns(
            config, credentials
        )
        self._resolved_configs = self.resolve_credentials(config, credentials)

    @property
    def config(self) -> dict[str, dict[str, Any]]:
        return self._resolved_configs

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @staticmethod
    def is_pattern(pattern: str) -> bool:
        """Check if a given string is a pattern. Assume that any name with '{' is a pattern."""
        return "{" in pattern

    @staticmethod
    def _pattern_specificity(pattern: str) -> int:
        """Calculate the specificity of a pattern based on characters outside curly brackets."""
        # Remove all the placeholders from the pattern and count the number of remaining chars
        result = re.sub(r"\{.*?\}", "", pattern)
        return len(result)

    @classmethod
    def _sort_patterns(cls, dataset_patterns: Patterns) -> Patterns:
        """Sort a dictionary of dataset patterns according to parsing rules.

        In order:
        1. Decreasing specificity (number of characters outside the curly brackets)
        2. Decreasing number of placeholders (number of curly bracket pairs)
        3. Alphabetically
        """
        sorted_keys = sorted(
            dataset_patterns,
            key=lambda pattern: (
                -(cls._pattern_specificity(pattern)),
                -pattern.count("{"),
                pattern,
            ),
        )
        catch_all = [
            pattern for pattern in sorted_keys if cls._pattern_specificity(pattern) == 0
        ]
        if len(catch_all) > 1:
            raise DatasetError(
                f"Multiple catch-all patterns found in the catalog: {', '.join(catch_all)}. Only one catch-all pattern is allowed, remove the extras."
            )
        return {key: dataset_patterns[key] for key in sorted_keys}

    @staticmethod
    def _fetch_credentials(credentials_name: str, credentials: dict[str, Any]) -> Any:
        """Fetch the specified credentials from the provided credentials dictionary.

        Args:
            credentials_name: Credentials name.
            credentials: A dictionary with all credentials.

        Returns:
            The set of requested credentials.

        Raises:
            KeyError: When a dataset with the given name has not yet been
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

    @classmethod
    def _resolve_credentials(
        cls, config: dict[str, Any], credentials: dict[str, Any]
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

        def _resolve_value(key: str, value: Any) -> Any:
            if key == CREDENTIALS_KEY and isinstance(value, str):
                return cls._fetch_credentials(value, credentials)
            if isinstance(value, dict):
                return {k: _resolve_value(k, v) for k, v in value.items()}
            return value

        return {k: _resolve_value(k, v) for k, v in config.items()}

    @classmethod
    def _validate_pattern_config(cls, ds_name: str, ds_config: dict[str, Any]) -> None:
        """Checks whether a dataset factory pattern configuration is valid - all
        keys used in the configuration present in the dataset factory pattern name.

        Args:
            ds_name: Dataset factory pattern name.
            ds_config: Dataset pattern configuration.

        Raises:
            DatasetError: when keys used in the configuration do not present in the dataset factory pattern name.

        """
        # Find all occurrences of {} in the string including brackets
        search_regex = r"\{.*?\}"
        name_placeholders = set(re.findall(search_regex, ds_name))
        config_placeholders = set()

        def _traverse_config(config: Any) -> None:
            if isinstance(config, dict):
                for value in config.values():
                    _traverse_config(value)
            elif isinstance(config, (list, tuple)):
                for value in config:
                    _traverse_config(value)
            elif isinstance(config, str) and "}" in config:
                config_placeholders.update(set(re.findall(search_regex, config)))

        _traverse_config(ds_config)

        if config_placeholders - name_placeholders:
            raise DatasetError(
                f"Incorrect dataset configuration provided. "
                f"Keys used in the configuration {config_placeholders - name_placeholders} "
                f"should present in the dataset factory pattern name {ds_name}."
            )

    @classmethod
    def _resolve_dataset_config(
        cls,
        ds_name: str,
        pattern: str,
        config: Any,
    ) -> Any:
        """Resolve dataset configuration based on the provided pattern."""
        resolved_vars = parse(pattern, ds_name)
        # Resolve the factory config for the dataset
        if isinstance(config, dict):
            for key, value in config.items():
                config[key] = cls._resolve_dataset_config(ds_name, pattern, value)
        elif isinstance(config, (list, tuple)):
            config = [
                cls._resolve_dataset_config(ds_name, pattern, value) for value in config
            ]
        elif isinstance(config, str) and "}" in config:
            config = config.format_map(resolved_vars.named)
        return config

    def list_patterns(self) -> list[str]:
        """List al patterns available in the catalog."""
        return (
            list(self._dataset_patterns.keys())
            + list(self._default_pattern.keys())
            + list(self._runtime_patterns.keys())
        )

    def match_pattern(self, ds_name: str) -> str | None:
        """Match a dataset name against patterns in a dictionary."""
        all_patterns = self.list_patterns()
        matches = (pattern for pattern in all_patterns if parse(pattern, ds_name))
        return next(matches, None)

    def _get_pattern_config(self, pattern: str) -> dict[str, Any]:
        return (
            self._dataset_patterns.get(pattern)
            or self._default_pattern.get(pattern)
            or self._runtime_patterns.get(pattern)
            or {}
        )

    @classmethod
    def _extract_patterns(
        cls,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> tuple[Patterns, Patterns]:
        """Extract and sort patterns from the configuration."""
        config = config or {}
        credentials = credentials or {}
        dataset_patterns = {}
        user_default = {}

        for ds_name, ds_config in config.items():
            if cls.is_pattern(ds_name):
                cls._validate_pattern_config(ds_name, ds_config)
                dataset_patterns[ds_name] = cls._resolve_credentials(
                    ds_config, credentials
                )

        sorted_patterns = cls._sort_patterns(dataset_patterns)
        if sorted_patterns:
            # If the last pattern is a catch-all pattern, pop it and set it as the default
            if cls._pattern_specificity(list(sorted_patterns.keys())[-1]) == 0:
                last_pattern = sorted_patterns.popitem()
                user_default = {last_pattern[0]: last_pattern[1]}

        return sorted_patterns, user_default

    @classmethod
    def resolve_credentials(
        cls,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        """Initialize the dataset configuration with resolved credentials."""
        config = config or {}
        credentials = credentials or {}
        resolved_configs = {}

        for ds_name, ds_config in config.items():
            if not isinstance(ds_config, dict):
                raise DatasetError(
                    f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
                    "\nHint: If this catalog entry is intended for variable interpolation, "
                    "make sure that the key is preceded by an underscore."
                )
            if not cls.is_pattern(ds_name):
                resolved_configs[ds_name] = cls._resolve_credentials(
                    ds_config, credentials
                )

        return resolved_configs

    @staticmethod
    def unresolve_credentials(
        cred_name: str, ds_config: dict[str, dict[str, Any]] | None
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """Extracts and replaces credentials in a dataset configuration with
        references, ensuring separation of credentials from the dataset configuration.

        Credentials are searched for recursively in the dataset configuration.
        The first occurrence of the `CREDENTIALS_KEY` is replaced with a generated
        reference key.

        Args:
            cred_name: A unique identifier for the credentials being unresolved.
                This is used to generate a reference key for the credentials.
            ds_config: The dataset configuration containing potential credentials
                under the key `CREDENTIALS_KEY`.

        Returns:
            A tuple containing:
                ds_config_copy : A deep copy of the original dataset
                    configuration with credentials replaced by reference keys.
                credentials: A dictionary mapping generated reference keys to the original credentials.
        """
        ds_config_copy = copy.deepcopy(ds_config) or {}
        credentials: dict[str, Any] = {}
        credentials_ref = f"{cred_name}_{CREDENTIALS_KEY}"

        def unresolve(config: Any) -> None:
            # We don't expect credentials key appears more than once within the same dataset config,
            # So once we found the key first time we unresolve it and stop iterating after
            for key, val in config.items():
                if key == CREDENTIALS_KEY and config[key]:
                    credentials[credentials_ref] = config[key]
                    config[key] = credentials_ref
                    return
                if isinstance(val, dict):
                    unresolve(val)

        unresolve(ds_config_copy)

        return ds_config_copy, credentials

    def resolve_pattern(self, ds_name: str) -> dict[str, Any]:
        """Resolve dataset patterns and return resolved configurations based on the existing patterns."""
        matched_pattern = self.match_pattern(ds_name)

        if matched_pattern and ds_name not in self._resolved_configs:
            pattern_config = self._get_pattern_config(matched_pattern)
            ds_config = self._resolve_dataset_config(
                ds_name, matched_pattern, copy.deepcopy(pattern_config)
            )

            if (
                self._pattern_specificity(matched_pattern) == 0
                and matched_pattern in self._default_pattern
            ):
                self._logger.warning(
                    "Config from the dataset factory pattern '%s' in the catalog will be used to "
                    "override the default dataset creation for '%s'",
                    matched_pattern,
                    ds_name,
                )
            return ds_config  # type: ignore[no-any-return]

        return self._resolved_configs.get(ds_name, {})

    def add_runtime_patterns(self, dataset_patterns: Patterns) -> None:
        """Add new runtime patterns and re-sort them."""
        self._runtime_patterns = {**self._runtime_patterns, **dataset_patterns}
        self._runtime_patterns = self._sort_patterns(self._runtime_patterns)

    def remove_runtime_patterns(self, dataset_patterns: Patterns) -> None:
        """Remove runtime patterns and re-sort them."""
        for pattern_name in dataset_patterns:
            if pattern_name in self._runtime_patterns:
                del self._runtime_patterns[pattern_name]
        self._runtime_patterns = self._sort_patterns(self._runtime_patterns)
