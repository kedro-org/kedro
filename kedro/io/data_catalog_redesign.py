from __future__ import annotations

import copy
import difflib
import logging
import re
from typing import Any

from kedro.io.catalog_config_resolver import DataCatalogConfigResolver
from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
)
from kedro.io.memory_dataset import MemoryDataset
from kedro.utils import _format_rich, _has_rich_handler

CREDENTIALS_KEY = "credentials"


def validate_dataset_config(ds_name: str, ds_config: Any) -> None:
    if not isinstance(ds_config, dict):
        raise DatasetError(
            f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
            "\nHint: If this catalog entry is intended for variable interpolation, "
            "make sure that the key is preceded by an underscore."
        )


class KedroDataCatalog:
    def __init__(
        self,
        datasets: dict[str, Any] | None = None,
        config: dict[str, dict[str, Any]] | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> None:
        self._config_resolver = DataCatalogConfigResolver()
        self._config = config or {}
        self._datasets = datasets or {}
        self._load_versions = load_versions or {}
        self._save_version = save_version
        self._use_rich_markup = _has_rich_handler()

        for ds_name in self._datasets:
            # TODO: API to get configuration from dataset
            self._config[ds_name] = {}

        for ds_name, ds_config in self._config.items():
            self.init_dataset(ds_name, ds_config)

        self._validate_missing_keys()

    @property
    def datasets(self) -> dict[str, Any]:
        return copy.deepcopy(self._datasets)

    @datasets.setter
    def datasets(self, value: Any):
        raise AttributeError(
            "Operation not allowed! Please change datasets through configuration."
        )

    @property
    def config(self):
        return copy.deepcopy(self._config)

    @config.setter
    def config(self, value: Any) -> dict[str, dict[str, Any]]:
        raise AttributeError(
            "Operation not allowed! Please change datasets through configuration."
        )

    def __iter__(self):
        yield from self._datasets.values()

    def __getitem__(self, ds_name: str) -> AbstractDataset:
        return self.get_dataset(ds_name)

    def __contains__(self, ds_name: str) -> bool:
        """Check if an item is in the catalog"""
        return ds_name in self._datasets

    def _ipython_key_completions_(self) -> list[str]:
        return list(self._datasets.keys())

    def init_dataset(self, ds_name: str, ds_config: dict[str, Any]) -> None:
        # Add lazy loading feature to store the configuration but not to init actual dataset
        # Initialise actual dataset when load or save
        # Add is_init property
        validate_dataset_config(ds_name, ds_config)
        if ds_name in self._datasets:
            raise DatasetAlreadyExistsError(
                f"Dataset '{ds_name}' has already been registered"
            )
        self._config[ds_name] = ds_config
        self._datasets[ds_name] = AbstractDataset.from_config(
            ds_name,
            ds_config,
            self._load_versions.get(ds_name),
            self._save_version,
        )

    def get_dataset(
        self, ds_name: str, suggest: bool = True, version: Version | None = None
    ) -> AbstractDataset:
        dataset = self._datasets.get(ds_name, None)

        if dataset is None:
            error_msg = f"Dataset '{ds_name}' not found in the catalog"
            # Flag to turn on/off fuzzy-matching which can be time consuming and
            # slow down plugins like `kedro-viz`
            if suggest:
                matches = difflib.get_close_matches(ds_name, self._datasets.keys())
                if matches:
                    suggestions = ", ".join(matches)
                    error_msg += f" - did you mean one of these instead: {suggestions}"
            raise DatasetNotFoundError(error_msg)

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
        # TODO: API to get configuration from dataset
        self._config[ds_name] = {}

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

    def save(self, name: str, data: Any) -> None:
        """Save data to a registered data set."""
        dataset = self.get_dataset(name)

        self._logger.info(
            "Saving data to %s (%s)...",
            _format_rich(name, "dark_orange") if self._use_rich_markup else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        dataset.save(data)

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

    def _validate_missing_keys(self) -> None:
        missing_keys = [key for key in self._load_versions if key not in self._config]
        if missing_keys:
            raise DatasetNotFoundError(
                f"'load_versions' keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

    def load(self, name: str, version: str | None = None) -> Any:
        """Loads a registered data set."""
        load_version = Version(version, None) if version else None
        dataset = self.get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from %s (%s)...",
            _format_rich(name, "dark_orange") if self._use_rich_markup else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        return dataset.load()

    def add_feed_dict(self, datasets: dict[str, Any], replace: bool = False) -> None:
        # TODO: rename to add_from_dict after removing old catalog
        # Consider changing to add memory datasets only, to simplify the method,
        # adding AbstractDataset can be done via add() method
        for ds_name, ds_data in datasets.items():
            dataset = (
                ds_data
                if isinstance(ds_data, AbstractDataset)
                else MemoryDataset(data=ds_data)
            )  # type: ignore[abstract]
            self.add(ds_name, dataset, replace)

    # def shallow_copy(
    #     self, extra_dataset_patterns: Patterns | None = None
    # ) -> KedroDataCatalog:
    #     """Returns a shallow copy of the current object.
    #
    #     Returns:
    #         Copy of the current object.
    #     """
    #     if extra_dataset_patterns:
    #         self._config_resolver.add_runtime_patterns(extra_dataset_patterns)
    #     return self.__class__(
    #         datasets=self._datasets,
    #         dataset_patterns=self._config_resolver.dataset_patterns,
    #         default_pattern=self._config_resolver.default_pattern,
    #         load_versions=self._load_versions,
    #         save_version=self._save_version,
    #         config_resolver=self._config_resolver,
    #     )
