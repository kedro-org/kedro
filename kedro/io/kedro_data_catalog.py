"""``KedroDataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``KedroDataCatalog``, you need to instantiate it with a dictionary of datasets.
Then it will act as a single point of reference for your calls, relaying load and
save functions to the underlying datasets.

``KedroDataCatalog`` is an experimental feature aimed to replace ``DataCatalog`` in the future.
Expect possible breaking changes while using it.
"""

from __future__ import annotations

import copy
import difflib
import logging
import re
from typing import Any, List  # noqa: UP035

from kedro.io.catalog_config_resolver import CatalogConfigResolver, Patterns
from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    CatalogProtocol,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
    generate_timestamp,
)
from kedro.io.memory_dataset import MemoryDataset
from kedro.utils import _format_rich, _has_rich_handler


class KedroDataCatalog(CatalogProtocol):
    def __init__(
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        raw_data: dict[str, Any] | None = None,
        config_resolver: CatalogConfigResolver | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> None:
        """``KedroDataCatalog`` stores instances of ``AbstractDataset``
        implementations to provide ``load`` and ``save`` capabilities from
        anywhere in the program. To use a ``KedroDataCatalog``, you need to
        instantiate it with a dictionary of datasets. Then it will act as a
        single point of reference for your calls, relaying load and save
        functions to the underlying datasets.

        Note: ``KedroDataCatalog`` is an experimental feature and is under active development. Therefore, it is possible we'll introduce breaking changes to this class, so be mindful of that if you decide to use it already.

        Args:
            datasets: A dictionary of dataset names and dataset instances.
            raw_data: A dictionary with data to be added in memory as `MemoryDataset`` instances.
                Keys represent dataset names and the values are raw data.
            config_resolver: An instance of CatalogConfigResolver to resolve dataset patterns and configurations.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on datasets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all datasets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.

        Example:
        ::
            >>> # settings.py
            >>> from kedro.io import KedroDataCatalog
            >>>
            >>> DATA_CATALOG_CLASS = KedroDataCatalog
        """
        self._config_resolver = config_resolver or CatalogConfigResolver()
        self._datasets = datasets or {}
        self._load_versions = load_versions or {}
        self._save_version = save_version

        self._use_rich_markup = _has_rich_handler()

        for ds_name, ds_config in self._config_resolver.config.items():
            self._add_from_config(ds_name, ds_config)

        if raw_data:
            self.add_feed_dict(raw_data)

    @property
    def datasets(self) -> dict[str, Any]:
        # TODO: remove when removing old catalog
        return copy.copy(self._datasets)

    @datasets.setter
    def datasets(self, value: Any) -> None:
        # TODO: remove when removing old catalog
        raise AttributeError(
            "Operation not allowed. Please use KedroDataCatalog.add() instead."
        )

    @property
    def config_resolver(self) -> CatalogConfigResolver:
        return self._config_resolver

    def __repr__(self) -> str:
        return repr(self._datasets)

    def __contains__(self, dataset_name: str) -> bool:
        """Check if an item is in the catalog as a materialised dataset or pattern"""
        return (
            dataset_name in self._datasets
            or self._config_resolver.match_pattern(dataset_name) is not None
        )

    def __eq__(self, other) -> bool:  # type: ignore[no-untyped-def]
        return (self._datasets, self._config_resolver.list_patterns()) == (
            other._datasets,
            other.config_resolver.list_patterns(),
        )

    def keys(self, regex_search: str | None = None) -> List[str]:  # noqa: UP006
        return self._filter_keys(regex_search)

    def values(self) -> List[AbstractDataset]:  # noqa: UP006
        return [self._datasets[key] for key in self]

    def items(
        self, regex_search: str | None = None
    ) -> List[tuple[str, AbstractDataset]]:  # noqa: UP006
        return [(key, self._datasets[key]) for key in self._filter_keys(regex_search)]

    def __iter__(self) -> str:
        yield from self._datasets.keys()

    def __getitem__(self, ds_name: str) -> AbstractDataset | None:
        return self.get_dataset(ds_name)

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self._datasets:
            self._logger.warning("Replacing dataset '%s'", key)
        if isinstance(value, AbstractDataset):
            self._datasets[key] = value
        else:
            self._datasets[key] = MemoryDataset(data=value)  # type: ignore[abstract]

    def __len__(self) -> int:
        return len(self.keys())

    def get(
        self, key: str, default: AbstractDataset | None = None
    ) -> AbstractDataset | None:
        """Get a dataset by name from an internal collection of datasets."""
        if key not in self._datasets:
            ds_config = self._config_resolver.resolve_pattern(key)
            if ds_config:
                self._add_from_config(key, ds_config)

        dataset = self._datasets.get(key, None)

        return dataset or default

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
        # TODO: Add lazy loading feature to store the configuration but not to init actual dataset
        # TODO: Initialise actual dataset when load or save
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
        # TODO: remove when removing old catalog
        """Get a dataset by name from an internal collection of datasets.

        If a dataset is not in the collection but matches any pattern
        it is instantiated and added to the collection first, then returned.

        Args:
            ds_name: A dataset name.
            version: Optional argument for concrete dataset version to be loaded.
                Works only with versioned datasets.
            suggest: Optional argument whether to suggest fuzzy-matching datasets' names
                in the DatasetNotFoundError message.

        Returns:
            An instance of AbstractDataset.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
                is not in the collection and do not match patterns.
        """
        dataset = self.get(ds_name)

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
        # TODO: remove when removing old catalog
        """Adds a new ``AbstractDataset`` object to the ``KedroDataCatalog``."""
        if ds_name in self._datasets and not replace:
            raise DatasetAlreadyExistsError(
                f"Dataset '{ds_name}' has already been registered"
            )
        self.__setitem__(ds_name, dataset)

    def list(self, regex_search: str | None = None) -> List[str]:  # noqa: UP006
        # TODO: remove when removing old catalog
        """
        List of all dataset names registered in the catalog.
        This can be filtered by providing an optional regular expression
        which will only return matching keys.
        """
        if regex_search == "":
            self._logger.warning("The empty string will not match any datasets")
            return []

        return self.keys(regex_search)

    def _filter_keys(self, regex_search: str | None) -> List[str]:  # noqa: UP006
        if regex_search is None:
            return list(self._datasets.keys())

        try:
            pattern = re.compile(regex_search, flags=re.IGNORECASE)
        except re.error as exc:
            raise SyntaxError(
                f"Invalid regular expression provided: '{regex_search}'"
            ) from exc
        return [ds_name for ds_name in self._datasets if pattern.search(ds_name)]

    def save(self, name: str, data: Any) -> None:
        # TODO: remove when removing old catalog
        """Save data to a registered dataset."""
        self.save_data(name, data)

    def save_data(self, name: str, data: Any) -> None:
        """Save data to a registered dataset."""
        dataset = self.get_dataset(name)

        self._logger.info(
            "Saving data to %s (%s)...",
            _format_rich(name, "dark_orange") if self._use_rich_markup else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        dataset.save(data)

    def load(self, name: str, version: str | None = None) -> Any:
        # TODO: remove when removing old catalog
        return self.load_data(name, version)

    def load_data(self, name: str, version: str | None = None) -> Any:
        """Loads a registered dataset."""
        load_version = Version(version, None) if version else None
        dataset = self.get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from %s (%s)...",
            _format_rich(name, "dark_orange") if self._use_rich_markup else name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        return dataset.load()

    def release(self, name: str) -> None:
        """Release any cached data associated with a dataset
        Args:
            name: A dataset to be checked.
        Raises:
            DatasetNotFoundError: When a dataset with the given name
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

    def add_feed_dict(self, feed_dict: dict[str, Any], replace: bool = False) -> None:
        # TODO: remove when removing old catalog
        # This method was simplified to add memory datasets only, since
        # adding AbstractDataset can be done via add() method
        for ds_name, ds_data in feed_dict.items():
            self.add(ds_name, MemoryDataset(data=ds_data), replace)  # type: ignore[abstract]

    def shallow_copy(
        self, extra_dataset_patterns: Patterns | None = None
    ) -> KedroDataCatalog:
        # TODO: remove when removing old catalog
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        if extra_dataset_patterns:
            self._config_resolver.add_runtime_patterns(extra_dataset_patterns)
        return self

    def exists(self, name: str) -> bool:
        """Checks whether registered dataset exists by calling its `exists()`
        method. Raises a warning and returns False if `exists()` is not
        implemented.

        Args:
            name: A dataset to be checked.

        Returns:
            Whether the dataset output exists.

        """
        try:
            dataset = self._get_dataset(name)
        except DatasetNotFoundError:
            return False
        return dataset.exists()
