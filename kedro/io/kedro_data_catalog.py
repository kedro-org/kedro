"""``KedroDataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``KedroDataCatalog``, you need to instantiate it with a dictionary of datasets.
Then it will act as a single point of reference for your calls, relaying load and
save functions to the underlying datasets.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Iterator, List  # noqa: UP035

from kedro.io.cached_dataset import CachedDataset
from kedro.io.catalog_config_resolver import CatalogConfigResolver
from kedro.io.core import (
    TYPE_KEY,
    AbstractDataset,
    AbstractVersionedDataset,
    CatalogProtocol,
    DatasetError,
    DatasetNotFoundError,
    Version,
    VersionAlreadyExistsError,
    generate_timestamp,
    parse_dataset_definition,
)
from kedro.io.memory_dataset import MemoryDataset, _is_memory_dataset
from kedro.logging import _format_rich
from kedro.utils import _has_rich_handler


class _LazyDataset:
    """A helper class to store AbstractDataset configuration and materialize dataset object."""

    def __init__(
        self,
        name: str,
        config: dict[str, Any],
        load_version: str | None = None,
        save_version: str | None = None,
    ):
        self.name = name
        self.config = config
        self.load_version = load_version
        self.save_version = save_version

    def __repr__(self) -> str:
        class_type, _ = parse_dataset_definition(self.config)
        return f"{class_type.__module__}.{class_type.__qualname__}"

    def materialize(self) -> AbstractDataset:
        return AbstractDataset.from_config(
            self.name, self.config, self.load_version, self.save_version
        )


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
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = KedroDataCatalog(datasets={"cars": cars})
        """
        self._config_resolver = config_resolver or CatalogConfigResolver()
        self._datasets: dict[str, AbstractDataset] = datasets or {}
        self._lazy_datasets: dict[str, _LazyDataset] = {}
        self._load_versions, self._save_version = self._validate_versions(
            datasets, load_versions or {}, save_version
        )

        self._use_rich_markup = _has_rich_handler()

        for ds_name, ds_config in self._config_resolver.config.items():
            self._add_from_config(ds_name, ds_config)

        raw_data = raw_data or {}
        for ds_name, data in raw_data.items():
            self[ds_name] = data  # type: ignore[has-type]

    @property
    def config_resolver(self) -> CatalogConfigResolver:
        return self._config_resolver

    def __repr__(self) -> str:
        return repr(self._lazy_datasets | self._datasets)

    def __contains__(self, dataset_name: str) -> bool:
        """Check if an item is in the catalog as a materialised dataset or pattern."""
        return (
            dataset_name in self._datasets
            or dataset_name in self._lazy_datasets
            or self._config_resolver.match_pattern(dataset_name) is not None
        )

    def __eq__(self, other) -> bool:  # type: ignore[no-untyped-def]
        """Compares two catalogs based on materialised datasets and datasets patterns."""
        return (
            self._datasets,
            self._lazy_datasets,
            self._config_resolver.list_patterns(),
        ) == (
            other._datasets,
            other._lazy_datasets,
            other.config_resolver.list_patterns(),
        )

    def keys(self) -> List[str]:  # noqa: UP006
        """List all dataset names registered in the catalog."""
        return list(self._lazy_datasets.keys()) + list(self._datasets.keys())

    def values(self) -> List[AbstractDataset]:  # noqa: UP006
        """List all datasets registered in the catalog."""
        return [self.get(key) for key in self]

    def items(self) -> List[tuple[str, AbstractDataset]]:  # noqa: UP006
        """List all dataset names and datasets registered in the catalog."""
        return [(key, self.get(key)) for key in self]

    def __iter__(self) -> Iterator[str]:
        yield from self.keys()

    def __getitem__(self, ds_name: str) -> AbstractDataset:
        """Get a dataset by name from an internal collection of datasets.

        If a dataset is not in the collection but matches any pattern
        it is instantiated and added to the collection first, then returned.

        Args:
            ds_name: A dataset name.

        Returns:
            An instance of AbstractDataset.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
                is not in the collection and does not match patterns.
        """
        return self.get(ds_name)

    def __setitem__(self, key: str, value: Any) -> None:
        """Add dataset to the ``KedroDataCatalog`` using the given key as a datsets name
        and the provided data as the value.

        The value can either be raw data or a Kedro dataset (i.e., an instance of a class
        inheriting from ``AbstractDataset``). If raw data is provided, it will be automatically
        wrapped in a ``MemoryDataset`` before being added to the catalog.

        Args:
            key: Name of the dataset.
            value: Raw data or an instance of a class inheriting from ``AbstractDataset``.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset
            >>> import pandas as pd
            >>>
            >>> df = pd.DataFrame({"col1": [1, 2],
            >>>                    "col2": [4, 5],
            >>>                    "col3": [5, 6]})
            >>>
            >>> catalog = KedroDataCatalog()
            >>> catalog["data_df"] = df  # Add raw data as a MemoryDataset
            >>>
            >>> assert catalog.load("data_df").equals(df)
            >>>
            >>> csv_dataset = CSVDataset(filepath="test.csv")
            >>> csv_dataset.save(df)
            >>> catalog["data_csv_dataset"] = csv_dataset  # Add a dataset instance
            >>>
            >>> assert catalog.load("data_csv_dataset").equals(df)
        """
        if key in self._datasets:
            self._logger.warning("Replacing dataset '%s'", key)
        if isinstance(value, AbstractDataset):
            self._load_versions, self._save_version = self._validate_versions(
                {key: value}, self._load_versions, self._save_version
            )
            self._datasets[key] = value
        elif isinstance(value, _LazyDataset):
            self._lazy_datasets[key] = value
        else:
            self._logger.debug(f"Adding input data as a MemoryDataset - {key}")
            self._datasets[key] = MemoryDataset(data=value)  # type: ignore[abstract]

    def __len__(self) -> int:
        return len(self.keys())

    def get(
        self,
        key: str,
        version: Version | None = None,
        default: AbstractDataset | None = None,
    ) -> AbstractDataset:
        """Get a dataset by name from an internal collection of datasets.

        If a dataset is not in the collection but matches any pattern
        it is instantiated and added to the collection first, then returned.

        Args:
            key: A dataset name.
            version: Optional argument to get a specific version of the dataset.
            default: Optional argument for default dataset to return in case
                requested dataset not in the catalog.

        Returns:
            An instance of AbstractDataset.

        Raises:
            DatasetNotFoundError: When dataset doesn't exist in the catalog.
        """
        if key not in self._datasets and key not in self._lazy_datasets:
            ds_config = self._config_resolver.resolve_pattern(key)
            if ds_config:
                self._add_from_config(key, ds_config)

        lazy_dataset = self._lazy_datasets.pop(key, None)
        if lazy_dataset:
            self[key] = lazy_dataset.materialize()

        dataset = self._datasets.get(key, None) or default

        if version and isinstance(dataset, AbstractVersionedDataset):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            dataset = dataset._copy(_version=version)

        if dataset is None:
            error_msg = f"Dataset '{key}' not found in the catalog"
            raise DatasetNotFoundError(error_msg)

        return dataset

    def _ipython_key_completions_(self) -> list[str]:
        return self.keys()

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

        Args:
            catalog: A dictionary whose keys are the dataset names and
                the values are dictionaries with the constructor arguments
                for classes implementing ``AbstractDataset``. The dataset
                class to be loaded is specified with the key ``type`` and their
                fully qualified class name. All ``kedro.io`` dataset can be
                specified by their class name only, i.e. their module name
                can be omitted.
            credentials: A dictionary containing credentials for different
                datasets. Use the ``credentials`` key in a ``AbstractDataset``
                to refer to the appropriate credentials as shown in the example
                below.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on datasets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all datasets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.

        Returns:
            An instantiated ``KedroDataCatalog`` containing all specified
            datasets, created and ready to use.

        Raises:
            DatasetNotFoundError: When `load_versions` refers to a dataset that doesn't
                exist in the catalog.

        Example:
        ::

            >>> config = {
            >>>     "cars": {
            >>>         "type": "pandas.CSVDataset",
            >>>         "filepath": "cars.csv",
            >>>         "save_args": {
            >>>             "index": False
            >>>         }
            >>>     },
            >>>     "boats": {
            >>>         "type": "pandas.CSVDataset",
            >>>         "filepath": "s3://aws-bucket-name/boats.csv",
            >>>         "credentials": "boats_credentials",
            >>>         "save_args": {
            >>>             "index": False
            >>>         }
            >>>     }
            >>> }
            >>>
            >>> credentials = {
            >>>     "boats_credentials": {
            >>>         "client_kwargs": {
            >>>             "aws_access_key_id": "<your key id>",
            >>>             "aws_secret_access_key": "<your secret>"
            >>>         }
            >>>      }
            >>> }
            >>>
            >>> catalog = KedroDataCatalog.from_config(config, credentials)
            >>>
            >>> df = catalog.load("cars")
            >>> catalog.save("boats", df)
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

    def to_config(
        self,
    ) -> tuple[
        dict[str, dict[str, Any]],
        dict[str, dict[str, Any]],
        dict[str, str | None],
        str | None,
    ]:
        """Converts the `KedroDataCatalog` instance into a configuration format suitable for
        serialization. This includes datasets, credentials, and versioning information.

        This method is only applicable to catalogs that contain datasets initialized with static, primitive
        parameters. For example, it will work fine if one passes credentials as dictionary to
        `GBQQueryDataset` but not as `google.auth.credentials.Credentials` object. See
        https://github.com/kedro-org/kedro-plugins/issues/950 for the details.

        Returns:
            A tuple containing:
                catalog: A dictionary mapping dataset names to their unresolved configurations,
                    excluding in-memory datasets.
                credentials: A dictionary of unresolved credentials extracted from dataset configurations.
                load_versions: A dictionary mapping dataset names to specific versions to be loaded,
                    or `None` if no version is set.
                save_version: A global version identifier for saving datasets, or `None` if not specified.
        Example:
        ::

            >>> from kedro.io import KedroDataCatalog
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(
            >>>     filepath="cars.csv",
            >>>     load_args=None,
            >>>     save_args={"index": False}
            >>> )
            >>> catalog = KedroDataCatalog(datasets={'cars': cars})
            >>>
            >>> config, credentials, load_versions, save_version = catalog.to_config()
            >>>
            >>> new_catalog = KedroDataCatalog.from_config(config, credentials, load_versions, save_version)
        """
        catalog: dict[str, dict[str, Any]] = {}
        credentials: dict[str, dict[str, Any]] = {}
        load_versions: dict[str, str | None] = {}

        for ds_name, ds in self._lazy_datasets.items():
            if _is_memory_dataset(ds.config.get(TYPE_KEY, "")):
                continue
            unresolved_config, unresolved_credentials = (
                self._config_resolver.unresolve_credentials(ds_name, ds.config)
            )
            catalog[ds_name] = unresolved_config
            credentials.update(unresolved_credentials)
            load_versions[ds_name] = self._load_versions.get(ds_name, None)

        for ds_name, ds in self._datasets.items():  # type: ignore[assignment]
            if _is_memory_dataset(ds):  # type: ignore[arg-type]
                continue
            resolved_config = ds.to_config()  # type: ignore[attr-defined]
            unresolved_config, unresolved_credentials = (
                self._config_resolver.unresolve_credentials(ds_name, resolved_config)
            )
            catalog[ds_name] = unresolved_config
            credentials.update(unresolved_credentials)
            load_versions[ds_name] = self._load_versions.get(ds_name, None)

        return catalog, credentials, load_versions, self._save_version

    @staticmethod
    def _validate_dataset_config(ds_name: str, ds_config: Any) -> None:
        if not isinstance(ds_config, dict):
            raise DatasetError(
                f"Catalog entry '{ds_name}' is not a valid dataset configuration. "
                "\nHint: If this catalog entry is intended for variable interpolation, "
                "make sure that the key is preceded by an underscore."
            )

        if "type" not in ds_config:
            raise DatasetError(
                f"An exception occurred when parsing config for dataset '{ds_name}':\n"
                "'type' is missing from dataset catalog configuration."
                "\nHint: If this catalog entry is intended for variable interpolation, "
                "make sure that the top level key is preceded by an underscore."
            )

    def _add_from_config(self, ds_name: str, ds_config: dict[str, Any]) -> None:
        """Create a LazyDataset instance and add it to the catalog.

        Args:
            ds_name: A dataset name.
            ds_config: A dataset configuration.

        Raises:
            DatasetError: When a dataset configuration provided is not valid.
        """
        self._validate_dataset_config(ds_name, ds_config)
        ds = _LazyDataset(
            ds_name,
            ds_config,
            self._load_versions.get(ds_name),
            self._save_version,
        )

        self.__setitem__(ds_name, ds)

    def filter(
        self,
        name_regex: re.Pattern[str] | str | None = None,
        type_regex: re.Pattern[str] | str | None = None,
        by_type: type | list[type] | None = None,
    ) -> List[str]:  # noqa: UP006
        """Filter dataset names registered in the catalog based on name and/or type.

        This method allows filtering datasets by their names and/or types. Regular expressions
        should be precompiled before passing them to `name_regex` or `type_regex`, but plain
        strings are also supported.

        Args:
            name_regex: Optional compiled regex pattern or string to filter dataset names.
            type_regex: Optional compiled regex pattern or string to filter dataset types.
                The provided regex is matched against the full dataset type path, for example:
                `kedro_datasets.pandas.parquet_dataset.ParquetDataset`.
            by_type: Optional dataset type(s) to filter by. This performs an instance type check
                rather than a regex match. It can be a single dataset type or a list of types.

        Returns:
            A list of dataset names that match the filtering criteria.

        Example:
        ::

            >>> import re
            >>> catalog = KedroDataCatalog()
            >>> # get datasets where the substring 'raw' is present
            >>> raw_data = catalog.filter(name_regex='raw')
            >>> # get datasets where names start with 'model_' (precompiled regex)
            >>> model_datasets = catalog.filter(name_regex=re.compile('^model_'))
            >>> # get datasets of a specific type using type_regex
            >>> csv_datasets = catalog.filter(type_regex='pandas.excel_dataset.ExcelDataset')
            >>> # get datasets where names contain 'train' and type matches 'CSV' in the path
            >>> catalog.filter(name_regex="train", type_regex="CSV")
            >>> # get datasets where names include 'data' and are of a specific type
            >>> from kedro_datasets.pandas import SQLQueryDataset
            >>> catalog.filter(name_regex="data", by_type=SQLQueryDataset)
            >>> # get datasets where names include 'data' and are of multiple specific types
            >>> from kedro.io import MemoryDataset
            >>> catalog.filter(name_regex="data", by_type=[MemoryDataset, SQLQueryDataset])
        """
        filtered = self.keys()

        # Apply name filter if specified
        if name_regex:
            filtered = [
                ds_name for ds_name in filtered if re.search(name_regex, ds_name)
            ]

        # Apply type filters if specified
        by_type_set = set()
        if by_type:
            if not isinstance(by_type, list):
                by_type = [by_type]
            for _type in by_type:
                by_type_set.add(f"{_type.__module__}.{_type.__qualname__}")

        if by_type_set or type_regex:
            filtered_types = []
            for ds_name in filtered:
                # Retrieve the dataset type
                if ds_name in self._lazy_datasets:
                    str_type = str(self._lazy_datasets[ds_name])
                else:
                    class_type = type(self._datasets[ds_name])
                    str_type = f"{class_type.__module__}.{class_type.__qualname__}"
                # Match against type_regex and apply by_type filtering
                if (not type_regex or re.search(type_regex, str_type)) and (
                    not by_type_set or str_type in by_type_set
                ):
                    filtered_types.append(ds_name)

            return filtered_types

        return filtered

    def save(self, ds_name: str, data: Any) -> None:
        """Save data to a registered dataset.

        Args:
            ds_name: The name of the dataset to be saved.
            data: A data object to be saved as configured in the registered
                dataset.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
                has not yet been registered.

        Example:
        ::

            >>> import pandas as pd
            >>>
            >>> from kedro.io import KedroDataCatalog
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = KedroDataCatalog(datasets={'cars': cars})
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>> catalog.save("cars", df)
        """
        dataset = self.get(ds_name)

        self._logger.info(
            "Saving data to %s (%s)...",
            _format_rich(ds_name, "dark_orange") if self._use_rich_markup else ds_name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        dataset.save(data)

    def load(self, ds_name: str, version: str | None = None) -> Any:
        """Loads a registered dataset.

        Args:
            ds_name: The name of the dataset to be loaded.
            version: Optional argument for concrete data version to be loaded.
                Works only with versioned datasets.

        Returns:
            The loaded data as configured.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
                has not yet been registered.

        Example:
        ::

            >>> from kedro.io import KedroDataCatalog
            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = KedroDataCatalog(datasets={'cars': cars})
            >>>
            >>> df = catalog.load("cars")
        """
        load_version = Version(version, None) if version else None
        dataset = self.get(ds_name, version=load_version)

        self._logger.info(
            "Loading data from %s (%s)...",
            _format_rich(ds_name, "dark_orange") if self._use_rich_markup else ds_name,
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
        dataset = self.get(name)
        dataset.release()

    def confirm(self, name: str) -> None:
        """Confirm a dataset by its name.
        Args:
            name: Name of the dataset.
        Raises:
            DatasetError: When the dataset does not have `confirm` method.
        """
        self._logger.info("Confirming dataset '%s'", name)
        dataset = self.get(name)

        if hasattr(dataset, "confirm"):
            dataset.confirm()
        else:
            raise DatasetError(f"Dataset '{name}' does not have 'confirm' method")

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
            dataset = self.get(name)
        except DatasetNotFoundError:
            return False
        return dataset.exists()

    @staticmethod
    def _validate_versions(
        datasets: dict[str, AbstractDataset] | None,
        load_versions: dict[str, str],
        save_version: str | None,
    ) -> tuple[dict[str, str], str | None]:
        """Validates and synchronises dataset versions for loading and saving.

        Ensures consistency of dataset versions across a catalog, particularly
        for versioned datasets. It updates load versions and validates that all
        save versions are consistent.

        Args:
            datasets: A dictionary mapping dataset names to their instances.
                if None, no validation occurs.
            load_versions: A mapping between dataset names and versions
                to load.
            save_version: Version string to be used for ``save`` operations
                by all datasets with versioning enabled.

        Returns:
            Updated ``load_versions`` with load versions specified in the ``datasets``
                and resolved ``save_version``.

        Raises:
            VersionAlreadyExistsError: If a dataset's save version conflicts with
                the catalog's save version.
        """
        if not datasets:
            return load_versions, save_version

        cur_load_versions = load_versions.copy()
        cur_save_version = save_version

        for ds_name, ds in datasets.items():
            cur_ds = ds._dataset if isinstance(ds, CachedDataset) else ds

            if isinstance(cur_ds, AbstractVersionedDataset) and cur_ds._version:
                if cur_ds._version.load:
                    cur_load_versions[ds_name] = cur_ds._version.load
                if cur_ds._version.save:
                    cur_save_version = cur_save_version or cur_ds._version.save
                    if cur_save_version != cur_ds._version.save:
                        raise VersionAlreadyExistsError(
                            f"Cannot add a dataset `{ds_name}` with `{cur_ds._version.save}` save version. "
                            f"Save version set for the catalog is `{cur_save_version}`"
                            f"All datasets in the catalog must have the same save version."
                        )

        return cur_load_versions, cur_save_version
