from __future__ import annotations

import abc
import copy
import difflib
import re
from typing import Any

from parse import parse

from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetError,
    DatasetNotFoundError,
    Version,
)

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

    def _map_value(key: str, value: Any) -> Any:
        if key == CREDENTIALS_KEY and isinstance(value, str):
            return _get_credentials(value, credentials)
        if isinstance(value, dict):
            return {k: _map_value(k, v) for k, v in value.items()}
        return value

    return {k: _map_value(k, v) for k, v in config.items()}


def validate_dataset_config(ds_name: str, ds_config: Any) -> None:
    if not isinstance(ds_config, dict):
        raise DatasetError(
            f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
            "\nHint: If this catalog entry is intended for variable interpolation, "
            "make sure that the key is preceded by an underscore."
        )


class AbstractDataCatalog:
    datasets = None

    def __init__(
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self.config = config or {}
        self.resolved_ds_configs = {}
        self.datasets = datasets or {}

        self._dataset_patterns, self._default_pattern = self._get_patterns(
            config, credentials
        )

    def __iter__(self):
        yield from self.datasets.values()

    @staticmethod
    def _is_pattern(pattern: str) -> bool:
        """Check if a given string is a pattern. Assume that any name with '{' is a pattern."""
        return "{" in pattern

    @staticmethod
    def _match_pattern(dataset_patterns: Patterns, dataset_name: str) -> str | None:
        """Match a dataset name against patterns in a dictionary."""
        matches = (
            pattern
            for pattern in dataset_patterns.keys()
            if parse(pattern, dataset_name)
        )
        return next(matches, None)

    @staticmethod
    def _specificity(pattern: str) -> int:
        """Helper function to check the length of exactly matched characters not inside brackets.

        Example:
        ::

            >>> specificity("{namespace}.companies") = 10
            >>> specificity("{namespace}.{dataset}") = 1
            >>> specificity("france.companies") = 16
        """
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
            raise DatasetError(
                f"Multiple catch-all patterns found in the catalog: {', '.join(catch_all)}. Only one catch-all pattern is allowed, remove the extras."
            )
        return {key: dataset_patterns[key] for key in sorted_keys}

    def _init_datasets(
        self,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> None:
        for ds_name, ds_config in config.items():
            if not self._is_pattern(ds_name):
                validate_dataset_config(ds_name, ds_config)
                resolved_ds_config = _resolve_credentials(  # noqa: PLW2901
                    ds_config, credentials
                )
                self.datasets[ds_name] = AbstractDataset.from_config(
                    ds_name,
                    resolved_ds_config,
                )

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
                validate_dataset_config(ds_name, ds_config)
                resolved_ds_config = _resolve_credentials(  # noqa: PLW2901
                    ds_config, credentials
                )
                dataset_patterns[ds_name] = resolved_ds_config

        sorted_patterns = cls._sort_patterns(dataset_patterns)
        if sorted_patterns:
            # If the last pattern is a catch-all pattern, pop it and set it as the default
            if cls._specificity(list(sorted_patterns.keys())[-1]) == 0:
                last_pattern = sorted_patterns.popitem()
                user_default = {last_pattern[0]: last_pattern[1]}

        return sorted_patterns, user_default

    @classmethod
    def _resolve_config(
        cls,
        dataset_name: str,
        matched_pattern: str,
        config: dict,
    ) -> dict[str, Any]:
        """Get resolved AbstractDataset from a factory config"""
        result = parse(matched_pattern, dataset_name)
        # Resolve the factory config for the dataset
        if isinstance(config, dict):
            for key, value in config.items():
                config[key] = cls._resolve_config(dataset_name, matched_pattern, value)
        elif isinstance(config, (list, tuple)):
            config = [
                cls._resolve_config(dataset_name, matched_pattern, value)
                for value in config
            ]
        elif isinstance(config, str) and "}" in config:
            try:
                config = str(config).format_map(result.named)
            except KeyError as exc:
                raise DatasetError(
                    f"Unable to resolve '{config}' from the pattern '{matched_pattern}'. Keys used in the configuration "
                    f"should be present in the dataset factory pattern."
                ) from exc
        return config

    @abc.abstractmethod
    def resolve_patterns(self, datasets: str | list[str], **kwargs):
        # Logic to resolve patterns and extend self.datasets with resolved names
        # and self.resolved_config with resolved config
        pass

    @abc.abstractmethod
    def get_dataset(self, dataset_name: str, suggest: bool = True, **kwargs) -> Any:
        self.resolve_patterns(dataset_name, **kwargs)

        if dataset_name not in self.datasets:
            error_msg = f"Dataset '{dataset_name}' not found in the catalog"

            # Flag to turn on/off fuzzy-matching which can be time consuming and
            # slow down plugins like `kedro-viz`
            if suggest:
                matches = difflib.get_close_matches(dataset_name, self.datasets.keys())
                if matches:
                    suggestions = ", ".join(matches)
                    error_msg += f" - did you mean one of these instead: {suggestions}"
            raise DatasetNotFoundError(error_msg)

        return self.datasets[dataset_name]

    @abc.abstractmethod
    def get_dataset_config(self, dataset_name: str) -> dict:
        # Logic to get dataset config from self.config and self._dataset_patterns, self._default_patterns
        pass


class KedroDataCatalog(AbstractDataCatalog):
    _save_version = None
    _load_versions = None

    def __init__(  # noqa: PLR0913
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> None:
        super().__init__(datasets, config, credentials)

        self._load_versions = load_versions or {}
        self._save_version = save_version

        self._init_datasets(config, credentials)

        missing_keys = [
            key
            for key in load_versions.keys()
            if not (key in config or self._match_pattern(self._dataset_patterns, key))
        ]
        if missing_keys:
            raise DatasetNotFoundError(
                f"'load_versions' keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

    def _init_datasets(
        self,
        config: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None,
    ) -> None:
        for ds_name, ds_config in config.items():
            if not self._is_pattern(ds_name):
                validate_dataset_config(ds_name, ds_config)
                resolved_ds_config = _resolve_credentials(  # noqa: PLW2901
                    ds_config, credentials
                )
                self.datasets[ds_name] = AbstractDataset.from_config(
                    ds_name,
                    resolved_ds_config,
                    self._load_versions.get(ds_name),
                    self._save_version,
                )

    def resolve_patterns(
        self,
        datasets: str | list[str],
        version: Version | None = None,
        suggest: bool = True,
    ) -> None:
        super().resolve_patterns(datasets)
        # KedroDataCatalog related logic

    def get_dataset(
        self, dataset_name: str, suggest: bool = True, version: Version | None = None
    ) -> AbstractDataset:
        dataset = super().get_dataset(dataset_name, suggest)

        if version and isinstance(dataset, AbstractVersionedDataset):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            dataset = dataset._copy(_version=version)

        return dataset

    def get_dataset_config(self, dataset_name: str) -> dict:
        # Logic to get dataset config from self.config and self._dataset_patterns, self._default_patterns
        pass
