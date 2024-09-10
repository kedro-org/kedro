"""``KedroDataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``KedroDataCatalog``, you need to instantiate it with a dictionary of data
sets. Then it will act as a single point of reference for your calls,
relaying load and save functions to the underlying data sets.
"""

from __future__ import annotations

import copy
import difflib
import logging
import re
from typing import Any, Union

from kedro.io import DataCatalog
from kedro.io.catalog_config_resolver import CatalogConfigResolver, Patterns
from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
    generate_timestamp,
)
from kedro.io.memory_dataset import MemoryDataset
from kedro.utils import _format_rich, _has_rich_handler


class KedroDataCatalog:
    def __init__(
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        feed_dict: dict[str, Any] | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
        config_resolver: CatalogConfigResolver | None = None,
    ) -> None:
        self._config_resolver = config_resolver or CatalogConfigResolver()
        self._datasets = datasets or {}
        self._load_versions = load_versions or {}
        self._save_version = save_version

        self._use_rich_markup = _has_rich_handler()

        for ds_name, ds_config in self._config_resolver.config.items():
            self._add_from_config(ds_name, ds_config)

        if feed_dict:
            self.add_from_dict(feed_dict)

    @property
    def datasets(self) -> dict[str, Any]:
        return copy.deepcopy(self._datasets)

    @datasets.setter
    def datasets(self, value: Any) -> None:
        raise AttributeError(
            "Operation not allowed! Please change datasets through configuration."
        )

    @property
    def config_resolver(self) -> CatalogConfigResolver:
        return self._config_resolver

    def __iter__(self) -> AbstractDataset:
        yield from self._datasets.values()

    def __getitem__(self, ds_name: str) -> AbstractDataset:
        return self.get_dataset(ds_name)

    def __contains__(self, dataset_name: str) -> bool:
        """Check if an item is in the catalog as a materialised dataset or pattern"""
        return (
            dataset_name in self._datasets
            or self._config_resolver.match_pattern(dataset_name) is not None
        )

    def __eq__(self, other) -> bool:  # type: ignore[no-untyped-def]
        return (self._datasets, self._config_resolver.list_patterns()) == (
            other.datasets,
            other.config_resolver.list_patterns(),
        )

    def _ipython_key_completions_(self) -> list[str]:
        return list(self._datasets.keys())

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    @classmethod
    def from_config(
        cls,
        catalog: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> KedroDataCatalog:
        """Create a ``KedroDataCatalog`` instance from configuration. This is a
        factory method used to provide developers with a way to instantiate
        ``KedroDataCatalog`` with configuration parsed from configuration files.
        """
        catalog = catalog or {}
        config_resolver = CatalogConfigResolver(catalog, credentials)
        save_version = save_version or generate_timestamp()
        load_versions = load_versions or {}

        missing_keys = [
            ds_name
            for ds_name in load_versions
            if not (
                ds_name in config_resolver.config
                or config_resolver.match_pattern(ds_name)
            )
        ]
        if missing_keys:
            raise DatasetNotFoundError(
                f"'load_versions' keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

        return cls(
            load_versions=load_versions,
            save_version=save_version,
            config_resolver=config_resolver,
        )

    @staticmethod
    def _validate_dataset_config(ds_name: str, ds_config: Any) -> None:
        if not isinstance(ds_config, dict):
            raise DatasetError(
                f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
                "\nHint: If this catalog entry is intended for variable interpolation, "
                "make sure that the key is preceded by an underscore."
            )

    def _add_from_config(self, ds_name: str, ds_config: dict[str, Any]) -> None:
        # Add lazy loading feature to store the configuration but not to init actual dataset
        # Initialise actual dataset when load or save
        self._validate_dataset_config(ds_name, ds_config)
        ds = AbstractDataset.from_config(
            ds_name,
            ds_config,
            self._load_versions.get(ds_name),
            self._save_version,
        )

        self.add(ds_name, ds)

    def get_dataset(
        self, ds_name: str, version: Version | None = None, suggest: bool = True
    ) -> AbstractDataset:
        ds_config = self._config_resolver.resolve_dataset_pattern(ds_name)

        if ds_name not in self._datasets and ds_config is not None:
            self._init_dataset(ds_name, ds_config)  # type: ignore[arg-type]

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

    def _get_dataset(
        self, dataset_name: str, version: Version | None = None, suggest: bool = True
    ) -> AbstractDataset:
        # TODO: remove when removing old catalog
        return self.get_dataset(dataset_name, version, suggest)

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

    def add_from_dict(self, datasets: dict[str, Any], replace: bool = False) -> None:
        # Consider changing to add memory datasets only, to simplify the method,
        # adding AbstractDataset can be done via add() method
        for ds_name, ds_data in datasets.items():
            dataset = (
                ds_data
                if isinstance(ds_data, AbstractDataset)
                else MemoryDataset(data=ds_data)  # type: ignore[abstract]
            )
            self.add(ds_name, dataset, replace)

    def add_feed_dict(self, feed_dict: dict[str, Any], replace: bool = False) -> None:
        # TODO: remove when removing old catalog
        return self.add_from_dict(feed_dict, replace)

    def shallow_copy(
        self, extra_dataset_patterns: Patterns | None = None
    ) -> KedroDataCatalog:
        # TODO: remove when old catalog
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        if extra_dataset_patterns:
            self._config_resolver.add_runtime_patterns(extra_dataset_patterns)
        return self

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
            dataset = self._get_dataset(name)
        except DatasetNotFoundError:
            return False
        return dataset.exists()


BaseDataCatalog = Union[DataCatalog, KedroDataCatalog]
