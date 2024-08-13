from __future__ import annotations

import abc
import copy
import difflib
import logging
import re
from typing import Any

from parse import parse

from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
)
from kedro.io.memory_dataset import MemoryDataset
from kedro.logging import _format_rich, _has_rich_handler

Patterns = dict[str, dict[str, Any]]

CREDENTIALS_KEY = "credentials"


class DatasetConfigurationNotFoundError(DatasetError):
    """``DatasetConfigurationNotFoundError`` raised by ``DataCatalog`` class in case of
    trying to get non-existing dataset configuration.
    """

    pass


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


def validate_dataset_config(ds_name: str, ds_config: Any) -> None:
    if not isinstance(ds_config, dict):
        raise DatasetError(
            f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
            "\nHint: If this catalog entry is intended for variable interpolation, "
            "make sure that the key is preceded by an underscore."
        )


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
            raise DatasetError(
                f"Unable to resolve '{config}' from the pattern '{matched_pattern}'. Keys used in the configuration "
                f"should be present in the dataset factory pattern."
            ) from exc
    return config


class AbstractDataCatalog(abc.ABC):
    def __init__(
        self,
        datasets: dict[str, Any] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
    ) -> None:
        self._config = config or {}
        self._resolved_ds_configs = {}
        self._datasets = datasets or {}
        self._dataset_patterns = {}
        self._default_pattern = {}
        self._runtime_patterns = {}

        if datasets:
            for ds_name in datasets:
                self._resolved_ds_configs[ds_name] = {}

        if config:
            self._dataset_patterns, self._default_pattern = self._get_patterns(
                config, credentials
            )
            self._update_ds_configs(config, credentials)
            self._init_datasets(config)

    @property
    def datasets(self):
        return copy.deepcopy(self._datasets)

    @datasets.setter
    def datasets(self, value: Any):
        msg = "Operation not allowed! Please change datasets through configuration."
        raise AttributeError(msg)

    @property
    def resolved_ds_configs(self):
        return copy.deepcopy(self._resolved_ds_configs)

    @resolved_ds_configs.setter
    def resolved_ds_configs(self, value: Any):
        msg = "Operation not allowed! Please change datasets through configuration."
        raise AttributeError(msg)

    @property
    def dataset_patterns(self):
        return self._dataset_patterns

    @property
    def default_pattern(self):
        return self._default_pattern

    def __iter__(self):
        yield from self._datasets.values()

    def __getitem__(self, ds_name: str) -> Any:
        return self.get_dataset(ds_name)

    def __contains__(self, ds_name: str) -> bool:
        """Check if an item is in the catalog as a materialised dataset or pattern"""
        matched_pattern = self.match_pattern(ds_name)
        if ds_name in self._datasets or matched_pattern:
            return True
        return False

    def _ipython_key_completions_(self) -> list[str]:
        return list(self._datasets.keys())

    def _update_ds_configs(
        self,
        config: dict[str, dict[str, Any]],
        credentials: dict[str, dict[str, Any]] | None,
    ) -> None:
        config = copy.deepcopy(config) or {}
        credentials = copy.deepcopy(credentials) or {}
        for ds_name, ds_config in config.items():
            if not self._is_pattern(ds_name):
                validate_dataset_config(ds_name, ds_config)
                self._resolved_ds_configs[ds_name] = _resolve_credentials(
                    ds_config, credentials
                )

    @staticmethod
    def _is_pattern(pattern: str) -> bool:
        """Check if a given string is a pattern. Assume that any name with '{' is a pattern."""
        return "{" in pattern

    def match_pattern(self, ds_name: str) -> str | None:
        """Match a dataset name against patterns in a dictionary."""
        all_patterns = list(self._dataset_patterns.keys())
        all_patterns.extend(list(self._default_pattern.keys()))
        all_patterns.extend(list(self._runtime_patterns.keys()))
        matches = (pattern for pattern in all_patterns if parse(pattern, ds_name))
        return next(matches, None)

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
            raise DatasetError(
                f"Multiple catch-all patterns found in the catalog: {', '.join(catch_all)}. Only one catch-all pattern is allowed, remove the extras."
            )
        return {key: dataset_patterns[key] for key in sorted_keys}

    @abc.abstractmethod
    def _init_dataset(self, ds_name: str, config: dict[str, Any]) -> None:
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataCatalog and "
            f"it must implement the '_init_dataset' method"
        )

    def _init_datasets(
        self,
        config: dict[str, dict[str, Any]] | None,
    ) -> None:
        for ds_name in config:
            if not self._is_pattern(ds_name):
                ds_resolved_config = self._resolved_ds_configs.get(ds_name, None)
                if not ds_resolved_config:
                    raise DatasetConfigurationNotFoundError(
                        f"Dataset '{ds_name}' configuration is missing."
                    )
                self._init_dataset(ds_name, ds_resolved_config)

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
                resolved_ds_config = _resolve_credentials(ds_config, credentials)
                dataset_patterns[ds_name] = resolved_ds_config

        sorted_patterns = cls._sort_patterns(dataset_patterns)
        if sorted_patterns:
            # If the last pattern is a catch-all pattern, pop it and set it as the default
            if cls._specificity(list(sorted_patterns.keys())[-1]) == 0:
                last_pattern = sorted_patterns.popitem()
                user_default = {last_pattern[0]: last_pattern[1]}

        return sorted_patterns, user_default

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
            if matched_pattern and ds_name not in self._datasets:
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
            elif ds_name in self._datasets:
                resolved_configs.append(self._resolved_ds_configs.get(ds_name, {}))
            else:
                resolved_configs.append(None)

        if isinstance(datasets, str):
            return resolved_configs[0]
        else:
            return resolved_configs

    def get_dataset(self, ds_name: str, suggest: bool = True) -> Any:
        ds_config = self.resolve_patterns(ds_name)

        if ds_config is None:
            error_msg = f"Dataset '{ds_name}' not found in the catalog"

            # Flag to turn on/off fuzzy-matching which can be time consuming and
            # slow down plugins like `kedro-viz`
            if suggest:
                matches = difflib.get_close_matches(ds_name, self._datasets.keys())
                if matches:
                    suggestions = ", ".join(matches)
                    error_msg += f" - did you mean one of these instead: {suggestions}"
            raise DatasetNotFoundError(error_msg)
        elif ds_name not in self._datasets:
            self._resolved_ds_configs[ds_name] = ds_config
            self._init_dataset(ds_name, ds_config)

        return self._datasets[ds_name]

    @abc.abstractmethod
    def add_from_dict(self, datasets: dict[str, Any], **kwargs) -> None:
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataCatalog and "
            f"it must implement the 'add_from_dict' method"
        )

    def add(self, ds_name: str, dataset: Any, **kwargs) -> None:
        """Adds a new dataset object to the ``AbstractDataCatalog``."""
        if ds_name in self._datasets:
            raise DatasetAlreadyExistsError(
                f"Dataset '{ds_name}' has already been registered"
            )
        self._datasets[ds_name] = dataset
        self._resolved_ds_configs[ds_name] = {}

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def list(self, regex_search: str | None = None) -> list[str]:
        """
        List of all dataset names registered in the catalog.
        This can be filtered by providing an optional regular expression
        which will only return matching keys.
        """

        if regex_search is None:
            return list(self._datasets.keys())

        if not regex_search.strip():
            self._logger.warning("The empty string will not match any data sets")
            return []

        try:
            pattern = re.compile(regex_search, flags=re.IGNORECASE)

        except re.error as exc:
            raise SyntaxError(
                f"Invalid regular expression provided: '{regex_search}'"
            ) from exc
        return [ds_name for ds_name in self._datasets if pattern.search(ds_name)]

    @abc.abstractmethod
    def load(self, name: str, **kwargs) -> Any:
        raise NotImplementedError(
            f"'{self.__class__.__name__}' is a subclass of AbstractDataCatalog and "
            f"it must implement the 'load' method"
        )

    def save(self, name: str, data: Any) -> None:
        """Save data to a registered data set.

        Args:
            name: A data set to be saved to.
            data: A data object to be saved as configured in the registered
                data set.

        Raises:
            DatasetNotFoundError: When a data set with the given name
                has not yet been registered.

        Example:
        ::

            >>> import pandas as pd
            >>>
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = DataCatalog(datasets={'cars': cars})
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>> catalog.save("cars", df)
        """
        dataset = self.get_dataset(name)

        self._logger.info(
            "Saving data to %s (%s)...",
            _format_rich(name, "dark_orange")
            if _has_rich_handler(self._logger)
            else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        dataset.save(data)

    def release(self, name: str) -> None:
        pass

    def confirm(self, name: str) -> None:
        pass

    def add_runtime_patterns(self, dataset_patterns: Patterns) -> None:
        self._runtime_patterns = {**self._runtime_patterns, **dataset_patterns}
        self._runtime_patterns = self._sort_patterns(self._runtime_patterns)

    def exists(self, name: str) -> bool:
        return True


class KedroDataCatalog(AbstractDataCatalog):
    def __init__(  # noqa: PLR0913
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
        credentials: dict[str, dict[str, Any]] | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> None:
        self._load_versions = load_versions or {}
        self._save_version = save_version

        super().__init__(datasets, config, credentials)

        self._validate_missing_keys()

    def _validate_missing_keys(self) -> None:
        missing_keys = [
            key
            for key in self._load_versions.keys()
            if not (key in self._config or self.match_pattern(key))
        ]
        if missing_keys:
            raise DatasetNotFoundError(
                f"'load_versions' keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

    def _init_dataset(self, ds_name: str, config: dict[str, Any]):
        # Add LazyAbstractDataset to store the configuration but not to init actual dataset
        # Initialise actual dataset when load or save
        # Add is_ds_init property
        self._datasets[ds_name] = AbstractDataset.from_config(
            ds_name,
            config,
            self._load_versions.get(ds_name),
            self._save_version,
        )

    def get_dataset(
        self, ds_name: str, suggest: bool = True, version: Version | None = None
    ) -> AbstractDataset:
        dataset = super().get_dataset(ds_name, suggest)

        if version and isinstance(dataset, AbstractVersionedDataset):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            dataset = dataset._copy(_version=version)

        return dataset

    def add(
        self, ds_name: str, dataset: AbstractDataset, replace: bool = False
    ) -> None:
        """Adds a new ``AbstractDataset`` object to the ``KedroDataCatalog``."""
        if ds_name in self._datasets:
            if replace:
                self._logger.warning("Replacing dataset '%s'", ds_name)
            else:
                raise DatasetAlreadyExistsError(
                    f"Dataset '{ds_name}' has already been registered"
                )
        self._datasets[ds_name] = dataset
        self._resolved_ds_configs[ds_name] = {}

    def add_from_dict(self, datasets: dict[str, Any], replace: bool = False) -> None:
        for ds_name in datasets:
            if isinstance(datasets[ds_name], AbstractDataset):
                dataset = datasets[ds_name]
            else:
                dataset = MemoryDataset(data=datasets[ds_name])  # type: ignore[abstract]

            self.add(ds_name, dataset, replace)

    def load(self, name: str, version: str | None = None) -> Any:
        """Loads a registered data set.

        Args:
            name: A data set to be loaded.
            version: Optional argument for concrete data version to be loaded.
                Works only with versioned datasets.

        Returns:
            The loaded data as configured.

        Raises:
            DatasetNotFoundError: When a data set with the given name
                has not yet been registered.

        Example:
        ::

            >>> from kedro.io import DataCatalog
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = DataCatalog(datasets={'cars': cars})
            >>>
            >>> df = catalog.load("cars")
        """
        load_version = Version(version, None) if version else None
        dataset = self.get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from %s (%s)...",
            _format_rich(name, "dark_orange")
            if _has_rich_handler(self._logger)
            else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        result = dataset.load()

        return result

    def release(self, name: str) -> None:
        """Release any cached data associated with a data set

        Args:
            name: A data set to be checked.

        Raises:
            DatasetNotFoundError: When a data set with the given name
                has not yet been registered.
        """
        dataset = self.get_dataset(name)
        dataset.release()

    def confirm(self, name: str) -> None:
        """Confirm a dataset by its name.

        Args:
            name: Name of the dataset.
        Raises:
            DatasetError: When the dataset does not have `confirm` method.

        """
        self._logger.info("Confirming dataset '%s'", name)
        dataset = self.get_dataset(name)

        if hasattr(dataset, "confirm"):
            dataset.confirm()
        else:
            raise DatasetError(f"Dataset '{name}' does not have 'confirm' method")

    def exists(self, name: str) -> bool:
        """Checks whether registered data set exists by calling its `exists()`
        method. Raises a warning and returns False if `exists()` is not
        implemented.

        Args:
            name: A data set to be checked.

        Returns:
            Whether the data set output exists.

        """
        try:
            dataset = self.get_dataset(name)
        except DatasetNotFoundError:
            return False
        return dataset.exists()
