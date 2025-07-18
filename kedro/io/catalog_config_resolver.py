"""``CatalogConfigResolver`` resolves dataset configurations and datasets'
patterns based on catalog configuration and credentials provided.
"""

from __future__ import annotations

import copy
import logging
import re
from typing import TYPE_CHECKING, Any

from parse import parse

from kedro.io.core import DatasetError

if TYPE_CHECKING:
    from collections.abc import Generator, Iterable

Patterns = dict[str, dict[str, Any]]

CREDENTIALS_KEY = "credentials"
DEFAULT_RUNTIME_PATTERN = {"{default}": {"type": "kedro.io.MemoryDataset"}}


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
            "https://docs.kedro.org/en/stable/data/index.html#DataCatalog "
            "for an example."
        ) from exc


def _resolve_credentials(
    config: dict[str, Any], credentials: dict[str, Any]
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
            return _fetch_credentials(value, credentials)
        if isinstance(value, dict):
            return {k: _resolve_value(k, v) for k, v in value.items()}
        return value

    return {k: _resolve_value(k, v) for k, v in config.items()}


class CatalogConfigResolver:
    """
    Resolves dataset configurations based on dataset factory patterns and credentials.

    The `CatalogConfigResolver` is responsible for managing dataset factory patterns, resolving
    credentials, and dynamically generating dataset configurations. It supports advanced
    features like pattern matching, user-set catch-all patterns, and runtime patterns, enabling
    flexible and reusable dataset configurations.

    Attributes:
        _default_runtime_patterns (Patterns): Runtime patterns used for resolving datasets.
        _dataset_patterns (dict): Sorted dataset factory patterns extracted from the catalog configuration.
        _user_catch_all_pattern (dict): User provided catch all pattern.
        _resolved_configs (dict): Resolved dataset configurations with credentials applied.

    Example:
    ``` python
    from kedro.io.catalog_config_resolver import CatalogConfigResolver

    config = {
        "{namespace}.int_{name}": {
            "type": "pandas.CSVDataset",
            "filepath": "{name}.csv",
            "credentials": "db_credentials",
        }
    }
    credentials = {"db_credentials": {"user": "username", "pass": "pass"}}
    resolver = CatalogConfigResolver(config=config, credentials=credentials)
    resolved_config = resolver.resolve_pattern("data.int_customers")
    print(resolved_config)
    # {'type': 'pandas.CSVDataset', 'filepath': 'customers.csv', 'credentials': {'user': 'username', 'pass': 'pass'}}
    ```
    """

    def __init__(
        self,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
        default_runtime_patterns: Patterns | None = None,
    ):
        """
        Initialize the `CatalogConfigResolver`.

        Args:
            config: Dataset configurations from the catalog.
            credentials: Credentials for datasets.
            default_runtime_patterns: Runtime patterns for resolving datasets.

        Example:
        ``` python
        from kedro.io.catalog_config_resolver import CatalogConfigResolver

        config = {
            "{namespace}.int_{name}": {
                "type": "pandas.CSVDataset",
                "filepath": "{name}.csv",
            }
        }
        resolver = CatalogConfigResolver(config=config)
        resolver._dataset_patterns
        # {'{namespace}.int_{name}': {'type': 'pandas.CSVDataset', 'filepath': '{name}.csv'}}
        ```
        """
        if default_runtime_patterns is None:
            self._logger.warning(
                f"Since runtime patterns are not provided, setting "
                f"the runtime pattern to default value: {DEFAULT_RUNTIME_PATTERN}"
            )
        self._default_runtime_patterns = (
            default_runtime_patterns or DEFAULT_RUNTIME_PATTERN
        )
        self._dataset_patterns, self._user_catch_all_pattern = self._extract_patterns(
            config, credentials
        )
        self._resolved_configs = self._resolve_credentials(config, credentials)

    @property
    def config(self) -> dict[str, dict[str, Any]]:
        """
        Get the resolved dataset configurations.

        Returns:
            Resolved dataset configurations.

        Example:
        ``` python
        from kedro.io.catalog_config_resolver import CatalogConfigResolver

        config = {
            "companies": {
                "type": "pandas.CSVDataset",
                "filepath": "companies.csv",
                "credentials": "db_credentials",
            }
        }
        credentials = {"db_credentials": {"user": "username", "pass": "pass"}}
        resolver = CatalogConfigResolver(config, credentials)
        print(resolver.config)
        # {'companies': {'type': 'pandas.CSVDataset', 'filepath': 'companies.csv', 'credentials': {'user': 'username', 'pass': 'pass'}}}
        ```
        """
        return self._resolved_configs

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @staticmethod
    def is_pattern(pattern: str) -> bool:
        """
        Check if a given string is a pattern. Assume that any name with '{' is a pattern.

        Args:
            pattern: The string to check.

        Returns:
            True if the string is a pattern, False otherwise.

        Example:
        ``` python
        CatalogConfigResolver.is_pattern("{namespace}.int_{name}")
        # True
        CatalogConfigResolver.is_pattern("example_dataset")
        # False
        ```
        """
        return "{" in pattern

    @staticmethod
    def _pattern_specificity(pattern: str) -> int:
        """
        Calculate the specificity of a pattern based on characters outside curly brackets.

        Args:
            pattern: The pattern to analyze.

        Returns:
            The number of characters outside curly brackets.

        Example:
        ``` python
        CatalogConfigResolver._pattern_specificity("{namespace}.int_{name}")
        # 5
        ```
        """
        # Remove all the placeholders from the pattern and count the number of remaining chars
        result = re.sub(r"\{.*?\}", "", pattern)
        return len(result)

    @classmethod
    def _sort_patterns(cls, dataset_patterns: Patterns) -> Patterns:
        """Sort a dictionary of dataset patterns according to parsing rules.

        Patterns are sorted in the following order:
        1. Decreasing specificity (number of characters outside the curly brackets)
        2. Decreasing number of placeholders (number of curly bracket pairs)
        3. Alphabetically

        Args:
            dataset_patterns: A dictionary of dataset patterns.

        Returns:
            A sorted dictionary of dataset patterns.

        Raises:
            DatasetError: If multiple catch-all patterns are found.

        Example:
        ``` python
        patterns = {
            "{namespace}.int_{name}{a}": {},
            "{namespace}.{name}": {},
            "{name}": {},
            "{namespace}.ant_{name}{c}": {},
        }
        sorted_patterns = CatalogConfigResolver._sort_patterns(patterns)
        print(sorted_patterns.keys())
        # dict_keys(['{namespace}.ant_{name}{c}', '{namespace}.int_{name}{a}', '{namespace}.{name}', '{name}'])
        ```
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

    @classmethod
    def _validate_pattern_config(cls, ds_name: str, ds_config: dict[str, Any]) -> None:
        """Checks whether a dataset pattern configuration is valid - all
        keys used in the configuration present in the dataset pattern name.

        Args:
            ds_name: Dataset pattern name.
            ds_config: Dataset pattern configuration.

        Raises:
            DatasetError: when keys used in the configuration do not present in the dataset pattern name.

        Example:
        ``` python
        pattern = "{namespace}.int_{name}"
        config = {"filepath": "{name}.csv"}
        CatalogConfigResolver._validate_pattern_config(pattern, config)
        # No error
        pattern = "{namespace}.int_{name}"
        config = {"filepath": "{nam}.csv"}
        CatalogConfigResolver._validate_pattern_config(pattern, config)
        # DatasetError: Incorrect dataset configuration provided. Keys used in the configuration {'{nam}'} should present in
        # the dataset pattern name {namespace}.int_{name}.
        ```
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
                f"should present in the dataset pattern name {ds_name}."
            )

    @classmethod
    def _resolve_dataset_config(
        cls,
        ds_name: str,
        pattern: str,
        config: Any,
    ) -> Any:
        """
        Resolve dataset configuration based on the provided pattern.

        Args:
            ds_name: The dataset name to resolve.
            pattern: The pattern to use for resolution.
            config: The dataset configuration.

        Returns:
            The resolved dataset configuration.

        Example:
        ``` python
        pattern = "{namespace}.int_{name}"
        config = {"filepath": "{name}.csv"}
        resolved_config = CatalogConfigResolver._resolve_dataset_config(
            "data.int_customers", pattern, config
        )
        print(resolved_config)
        # {"filepath": "customers.csv"}
        ```
        """
        resolved_vars = parse(pattern, ds_name)
        # Resolve the pattern config for the dataset
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
        """
        List all patterns available in the catalog.

        Returns:
            A list of dataset patterns.

        Example:
        ``` python
        config = {
            "{namespace}.int_{name}": {
                "type": "pandas.CSVDataset",
                "filepath": "{name}.csv",
            }
        }
        resolver = CatalogConfigResolver(config)
        print(resolver.list_patterns())
        # ['{namespace}.int_{name}', '{default}']
        ```
        """
        # User defined patterns
        patterns = list(self._dataset_patterns.keys()) + list(
            self._user_catch_all_pattern.keys()
        )

        # All patterns excluding duplicates
        for pattern in self._default_runtime_patterns.keys():
            if pattern not in patterns:
                patterns.append(pattern)

        return patterns

    @classmethod
    def _get_matches(cls, pattens: Iterable[str], ds_name: str) -> Generator[str]:
        """
        Find all patterns that match a given dataset name.

        This method iterates over a collection of patterns and checks if the given
        dataset name matches any of them using the `parse` function.

        Args:
            pattens: A collection of patterns to match against.
            ds_name: The name of the dataset to match.

        Returns:
            A generator yielding patterns that match the dataset name.

        Example:
        ``` python
        patterns = ["{namespace}.int_{name}", "{name}"]
        matches = CatalogConfigResolver._get_matches(patterns, "data.int_customers")
        print(list(matches))
        # ['{namespace}.int_{name}']
        ```
        """
        return (pattern for pattern in pattens if parse(pattern, ds_name))

    def match_dataset_pattern(self, ds_name: str) -> str | None:
        """
        Match a dataset name against dataset patterns.

        This method checks if the given dataset name matches any of the dataset
        patterns defined in the catalog. If a match is found, the first matching
        pattern is returned.

        Args:
            ds_name: The name of the dataset to match.

        Returns:
            The first matching pattern, or `None` if no match is found.

        Example:
        ``` python
        config = {
            "{namespace}.int_{name}": {"type": "pandas.CSVDataset"},
            "{name}": {"type": "MemoryDataset"},
        }
        resolver = CatalogConfigResolver(config=config)
        match = resolver.match_dataset_pattern("data.int_customers")
        print(match)
        # {namespace}.int_{name}
        ```
        """
        matches = self._get_matches(self._dataset_patterns.keys(), ds_name)
        return next(matches, None)

    def match_user_catch_all_pattern(self, ds_name: str) -> str | None:
        """
        Match a dataset name against the user-defined catch-all pattern.

        This method checks if the given dataset name matches any of the user-defined
        catch-all patterns. If a match is found, the first matching pattern is returned.

        Args:
            ds_name: The name of the dataset to match.

        Returns:
            The first matching pattern, or `None` if no match is found.

        Example:
        ``` python
        config = {"{name}": {"type": "MemoryDataset"}}
        resolver = CatalogConfigResolver(config=config)
        match = resolver.match_user_catch_all_pattern("example_dataset")
        print(match)
        # {name}
        ```
        """
        user_catch_all_pattern = set(self._user_catch_all_pattern.keys())
        matches = self._get_matches(user_catch_all_pattern, ds_name)
        return next(matches, None)

    def match_runtime_pattern(self, ds_name: str) -> str:
        """
        Match a dataset name against the default runtime pattern.

        This method checks if the given dataset name matches any of the default
        runtime patterns. It assumes that a runtime pattern always matches.

        Args:
            ds_name: The name of the dataset to match.

        Returns:
            The first matching runtime pattern.

        Example:
        ``` python
        runtime_patterns = {"{default_example}": {"type": "MemoryDataset"}}
        resolver = CatalogConfigResolver(default_runtime_patterns=runtime_patterns)
        match = resolver.match_runtime_pattern("example_dataset")
        print(match)
        # {default_example}
        ```
        """
        default_patters = set(self._default_runtime_patterns.keys())
        matches = self._get_matches(default_patters, ds_name)
        # We assume runtime pattern always matches at the end
        return next(matches)

    def _get_pattern_config(self, pattern: str) -> dict[str, Any]:
        """
        Retrieve the configuration for a given dataset pattern.

        This method searches for the configuration of the specified pattern in the
        dataset patterns, user-set catch-all patterns, and runtime patterns. If the pattern is
        not found in any of these, an empty dictionary is returned.

        Args:
            pattern: The dataset pattern to retrieve the configuration for.

        Returns:
            The configuration dictionary for the specified pattern,
            or an empty dictionary if the pattern is not found.

        Example:
        ``` python
        resolver = CatalogConfigResolver(config={"example": {"type": "MemoryDataset"}})
        resolver._get_pattern_config("{default}")
        # {'type': 'kedro.io.MemoryDataset'}
        ```
        """
        return (
            self._dataset_patterns.get(pattern)
            or self._user_catch_all_pattern.get(pattern)
            or self._default_runtime_patterns.get(pattern)
            or {}
        )

    @classmethod
    def _extract_patterns(
        cls,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> tuple[Patterns, Patterns]:
        """
        Extract and sort patterns from the catalog configuration.

        This method identifies dataset patterns from the catalog configuration and
        sorts them based on specificity. It also identifies a catch-all pattern (if any)
        and sets it as the default pattern.

        Args:
            config: The catalog configuration containing dataset patterns.
            credentials: The credentials for datasets.

        Returns:
            A tuple containing:
                - Sorted dataset patterns.
                - The default pattern (if a catch-all pattern is found).

        Example:
        ``` python
        config = {
            "{namespace}.int_{name}": {"type": "pandas.CSVDataset"},
            "{name}": {"type": "MemoryDataset"},
        }
        sorted_patterns, default_pattern = CatalogConfigResolver._extract_patterns(
            config, None
        )
        print(sorted_patterns.keys())
        # dict_keys(['{namespace}.int_{name}'])
        print(default_pattern.keys())
        # dict_keys(['{name}'])
        ```
        """
        config = config or {}
        credentials = credentials or {}
        dataset_patterns = {}
        user_default = {}

        for ds_name, ds_config in config.items():
            if cls.is_pattern(ds_name):
                cls._validate_pattern_config(ds_name, ds_config)
                dataset_patterns[ds_name] = _resolve_credentials(ds_config, credentials)

        sorted_patterns = cls._sort_patterns(dataset_patterns)
        if sorted_patterns:
            # If the last pattern is a catch-all pattern, pop it and set it as the default
            if cls._pattern_specificity(list(sorted_patterns.keys())[-1]) == 0:
                last_pattern = sorted_patterns.popitem()
                user_default = {last_pattern[0]: last_pattern[1]}

        return sorted_patterns, user_default

    @classmethod
    def _resolve_credentials(
        cls,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> dict[str, dict[str, Any]]:
        """
        Resolve credentials for datasets in the catalog configuration.

        This method replaces credential references in the dataset configuration with
        the actual credentials from the provided credentials dictionary.

        Args:
            config: The catalog configuration containing datasets.
            credentials: The credentials for datasets.

        Returns:
            The dataset configurations with resolved credentials.

        Raises:
            DatasetError: If a dataset configuration is invalid (e.g., not a dictionary).

        Example:
        ``` python
        config = {
            "example": {
                "type": "pandas.CSVDataset",
                "credentials": "db_credentials",
            }
        }
        credentials = {"db_credentials": {"user": "username", "pass": "pass"}}
        resolved_configs = CatalogConfigResolver._resolve_credentials(
            config, credentials
        )
        print(resolved_configs)
        # {'example': {'type': 'pandas.CSVDataset', 'credentials': {'user': 'username', 'pass': 'pass'}}}
        ```
        """
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
                resolved_configs[ds_name] = _resolve_credentials(ds_config, credentials)

        return resolved_configs

    @staticmethod
    def _unresolve_credentials(
        cred_name: str, ds_config: dict[str, dict[str, Any]] | None
    ) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
        """
        Extracts and replaces credentials in a dataset configuration with
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

        Example:
        ``` python
        config = {
            "type": "pandas.CSVDataset",
            "credentials": {"user": "username", "pass": "pass"},
        }
        ds_config, creds = CatalogConfigResolver._unresolve_credentials(
            "example", config
        )
        print(ds_config)
        # {'type': 'pandas.CSVDataset', 'credentials': 'example_credentials'}
        print(creds)
        # {'example_credentials': {'user': 'username', 'pass': 'pass'}}
        ```
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
        """
        Resolve a dataset name to its configuration based on patterns.

        This method matches the dataset name against catalog patterns and resolves
        its configuration. If the dataset name matches a user-defined catch-all pattern, a warning
        is logged.

        Args:
            ds_name: The name of the dataset to resolve.

        Returns:
            The resolved dataset configuration.

        Example:
        ``` python
        config = {
            "{namespace}.int_{name}": {
                "type": "pandas.CSVDataset",
                "filepath": "{name}.csv",
            }
        }
        resolver = CatalogConfigResolver(config=config)
        resolved_config = resolver.resolve_pattern("data.int_customers")
        print(resolved_config)
        # {'type': 'pandas.CSVDataset', 'filepath': 'customers.csv'}
        ```
        """
        if ds_name not in self._resolved_configs:
            matched_pattern = (
                self.match_dataset_pattern(ds_name)
                or self.match_user_catch_all_pattern(ds_name)
                or self.match_runtime_pattern(ds_name)
            )
            pattern_config = self._get_pattern_config(matched_pattern)
            ds_config = self._resolve_dataset_config(
                ds_name, matched_pattern, copy.deepcopy(pattern_config)
            )

            if (
                self._pattern_specificity(matched_pattern) == 0
                and matched_pattern in self._user_catch_all_pattern
            ):
                self._logger.warning(
                    "Config from the dataset pattern '%s' in the catalog will be used to "
                    "override the default dataset creation for '%s'",
                    matched_pattern,
                    ds_name,
                )
            return ds_config  # type: ignore[no-any-return]

        return self._resolved_configs[ds_name]
