"""``DataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``DataCatalog``, you need to instantiate it with a dictionary of datasets.
Then it will act as a single point of reference for your calls, relaying load and
save functions to the underlying datasets.
"""

from __future__ import annotations

import logging
import re
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import TYPE_CHECKING, Any, ClassVar, Iterator, List  # noqa: UP035

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
from kedro.io.shared_memory_dataset import SharedMemoryDataset
from kedro.utils import _format_rich, _has_rich_handler

if TYPE_CHECKING:
    from multiprocessing.managers import SyncManager


class _LazyDataset:
    """
    A helper class to store `AbstractDataset` configuration and materialize the dataset object.

    This class acts as a placeholder for a dataset, storing its configuration and versioning
    information. The dataset is only materialized (i.e., instantiated) when explicitly requested,
    which helps improve performance by deferring the creation of datasets until they are needed.

    Attributes:
        name (str): The name of the dataset.
        config (dict[str, Any]): The configuration dictionary for the dataset.
        load_version (str | None): The version of the dataset to load, if applicable.
        save_version (str | None): The version of the dataset to save, if applicable.

    Example:
    ```python

        from kedro.io.data_catalog import _LazyDataset
        dataset_config = {"type": "pandas.CSVDataset", "filepath": "example.csv"}
        lazy_dataset = _LazyDataset(
            name="example_dataset",
            config=dataset_config,
            load_version="2023-01-01T00.00.00",
            save_version="2023-01-02T00.00.00",
        )
        print(lazy_dataset)
        # kedro_datasets.pandas.csv_dataset.CSVDataset
        materialized_dataset = lazy_dataset.materialize()
        print(materialized_dataset)
        # CSVDataset(filepath=example.csv, load_args={}, protocol=file, save_args={'index': False})
    ```
    """

    def __init__(
        self,
        name: str,
        config: dict[str, Any],
        load_version: str | None = None,
        save_version: str | None = None,
    ):
        """
        Initialize a `_LazyDataset` instance.

        Args:
            name: The name of the dataset.
            config: The configuration dictionary for the dataset.
            load_version: The version of the dataset to load, if applicable.
            save_version: The version of the dataset to save, if applicable.

        Example:
        ```python

            from kedro.io.data_catalog import _LazyDataset
            dataset_config = {"type": "pandas.CSVDataset", "filepath": "example.csv"}
            lazy_dataset = _LazyDataset(
                name="example_dataset",
                config=dataset_config,
                load_version="2023-01-01T00.00.00",
                save_version="2023-01-02T00.00.00",
            )
            print(lazy_dataset)
            # kedro_datasets.pandas.csv_dataset.CSVDataset
        ```
        """
        self.name = name
        self.config = config
        self.load_version = load_version
        self.save_version = save_version

    def __repr__(self) -> str:
        """
        Return a string representation of the `_LazyDataset`.

        The representation includes the fully qualified class name of the dataset type
        as defined in the configuration.

        Returns:
            The fully qualified class name of the dataset type.

        Example:
        ````python

            from kedro.io.data_catalog import _LazyDataset
            dataset_config = {"type": "pandas.CSVDataset", "filepath": "example.csv"}
            lazy_dataset = _LazyDataset(name="example_dataset", config=dataset_config)
            print(repr(lazy_dataset))
            # kedro_datasets.pandas.csv_dataset.CSVDataset
        ```
        """
        class_type, _ = parse_dataset_definition(self.config)
        return f"{class_type.__module__}.{class_type.__qualname__}"

    def materialize(self) -> AbstractDataset:
        """
        Materialize the `_LazyDataset` into an `AbstractDataset` instance.

        This method uses the stored configuration and versioning information to create
        an instance of the dataset. The dataset is instantiated using the `from_config`
        factory method of `AbstractDataset`.

        Returns:
            The instantiated dataset object.

        Example:
        ``` python

            from kedro.io.data_catalog import _LazyDataset
            dataset_config = {"type": "pandas.CSVDataset", "filepath": "example.csv"}
            lazy_dataset = _LazyDataset(
                name="example_dataset",
                config=dataset_config,
                load_version="2023-01-01T00.00.00",
                save_version="2023-01-02T00.00.00",
            )
            materialized_dataset = lazy_dataset.materialize()
            print(materialized_dataset)
            # CSVDataset(filepath=example.csv, load_args={}, protocol=file, save_args={'index': False})
        ```
        """
        return AbstractDataset.from_config(
            self.name, self.config, self.load_version, self.save_version
        )


class DataCatalog(CatalogProtocol):
    """
    A centralized registry for managing datasets in a Kedro project.

    The `DataCatalog` provides a unified interface for loading and saving datasets,
    enabling seamless interaction with various data sources and formats. It supports
    features such as lazy loading, versioning, and dynamic dataset creation using dataset
    factory patterns.

    This class is the core component of Kedro's data management system, allowing
    datasets to be defined, accessed, and manipulated in a consistent and reusable way.

    Attributes:
        default_runtime_patterns (ClassVar): A dictionary defining the default runtime pattern
            for datasets of type `kedro.io.MemoryDataset`.
        _datasets: A dictionary of fully initialized datasets.
        _lazy_datasets: A dictionary of `_LazyDataset` instances for deferred initialization.
        _load_versions: A mapping of dataset names to specific versions to load.
        _save_version: The global version string for saving datasets.
        _config_resolver: Resolves dataset factory patterns and configurations.

    Example:
    ``` python
        from kedro.io import DataCatalog, MemoryDataset

        # Define datasets
        datasets = {
            "cars": MemoryDataset(data={"type": "car", "capacity": 5}),
            "planes": MemoryDataset(data={"type": "jet", "capacity": 200}),
        }

        # Initialize the catalog
        catalog = DataCatalog(datasets=datasets)

        # Load data
        cars_data = catalog.load("cars")
        print(cars_data)

        # Save data
        catalog.save("planes", {"type": "propeller", "capacity": 100})
        planes_data = catalog.load("planes")
        print(planes_data)
    ```
    """

    default_runtime_patterns: ClassVar = {
        "{default}": {"type": "kedro.io.MemoryDataset"}
    }

    def __init__(
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        config_resolver: CatalogConfigResolver | None = None,
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
    ) -> None:
        """Initializes a ``DataCatalog`` to manage datasets with loading, saving, and versioning capabilities.

        This catalog combines datasets passed directly via the `datasets` argument and dynamic datasets
        resolved from config (e.g., from YAML).

        If a dataset name is present in both `datasets` and the resolved config, the dataset from `datasets`
        takes precedence. A warning is logged, and the config-defined dataset is skipped and removed from
        the internal config.

        Args:
            datasets: A dictionary of dataset names and dataset instances.
            config_resolver: An instance of CatalogConfigResolver to resolve dataset factory patterns and configurations.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on datasets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all datasets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.

        Example:
        ``` python

            from kedro.io import DataCatalog, MemoryDataset
            from kedro_datasets.pandas import CSVDataset

            # Define datasets
            datasets = {
                "cars": CSVDataset(filepath="cars.csv"),
                "planes": MemoryDataset(data={"type": "jet", "capacity": 200}),
            }

            # Initialize the catalog
            catalog = DataCatalog(
                datasets=datasets,
                load_versions={"cars": "2023-01-01T00.00.00"},
                save_version="2023-01-02T00.00.00",
            )

            print(catalog)
        ```
        """
        self._config_resolver = config_resolver or CatalogConfigResolver(
            default_runtime_patterns=self.default_runtime_patterns
        )
        self._datasets: dict[str, AbstractDataset] = datasets or {}
        self._lazy_datasets: dict[str, _LazyDataset] = {}
        self._load_versions, self._save_version = self._validate_versions(
            datasets, load_versions or {}, save_version
        )

        self._use_rich_markup = _has_rich_handler()

        for ds_name in list(self._config_resolver.config):
            if ds_name in self._datasets:
                self._logger.warning(
                    f"Cannot register dataset '{ds_name}' from config: a dataset with the same name "
                    f"was already provided in the `datasets` argument."
                )
                self._config_resolver.config.pop(ds_name)
            else:
                self._add_from_config(ds_name, self._config_resolver.config[ds_name])

    @property
    def config_resolver(self) -> CatalogConfigResolver:
        """
        Get the `CatalogConfigResolver` instance associated with this `DataCatalog`.

        The `CatalogConfigResolver` is responsible for resolving dataset factory patterns
        and configurations dynamically.

        Returns:
            CatalogConfigResolver: The configuration resolver for the catalog.

        Example:
        ``` python

            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            resolver = catalog.config_resolver
            print(resolver)
        ```
        """
        return self._config_resolver

    def __repr__(self) -> str:
        """
        Return a string representation of the `DataCatalog`.

        The representation includes both lazy and fully initialized datasets
        in the catalog.

        Returns:
            A string representation of the catalog.

        Example:
        ```python

            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            print(repr(catalog))
            # "example: kedro.io.memory_dataset.MemoryDataset()"
        ```
        """
        combined = self._lazy_datasets | self._datasets
        lines = []
        for key, dataset in combined.items():
            lines.append(f"'{key}': {dataset!r}")
        return "\n".join(lines)

    def __contains__(self, dataset_name: str) -> bool:
        """
        Check if a dataset is registered in the catalog
        or matches a dataset/user catch all pattern

        Args:
            dataset_name: The name of the dataset to check.

        Returns:
            True if the dataset is registered or matches a pattern, False otherwise.

        Example:
        ```python

            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            "example" in catalog
            # True
            "nonexistent" in catalog
            # False
        ```
        """
        return (
            dataset_name in self._datasets
            or dataset_name in self._lazy_datasets
            or self._config_resolver.match_dataset_pattern(dataset_name) is not None
            or self._config_resolver.match_user_catch_all_pattern(dataset_name)
            is not None
        )

    def __eq__(self, other) -> bool:  # type: ignore[no-untyped-def]
        """
        Compare two catalogs based on materialized datasets, lazy datasets and all dataset factory patterns.

        Args:
            other: Another `DataCatalog` instance to compare.

        Returns:
            True if the catalogs are equivalent, False otherwise.

        Example:
        ```python
            catalog1 = DataCatalog(datasets={"example": MemoryDataset()})
            catalog2 = DataCatalog(datasets={"example": MemoryDataset()})
            catalog1 == catalog2
            # False
        ```
        """
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
        """
        List all dataset names registered in the catalog, including both materialized and lazy datasets.

        Returns:
            A list of all dataset names.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            catalog.keys()
            # ['example']
        ```
        """
        return list(self._lazy_datasets.keys()) + list(self._datasets.keys())

    def values(self) -> List[AbstractDataset]:  # noqa: UP006
        """
        Retrieve all datasets registered in the catalog.

        This method returns a list of all dataset instances currently registered
        in the catalog, including both materialized and lazy datasets.

        Returns:
            A list of dataset instances.

        Example:
        ```python
            from kedro.io import DataCatalog, MemoryDataset
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            dataset_values = catalog.values()
            print(dataset_values)
            # [kedro.io.memory_dataset.MemoryDataset()]
        ```
        """
        return [self[key] for key in self]

    def items(self) -> List[tuple[str, AbstractDataset]]:  # noqa: UP006
        """
        Retrieve all dataset names and their corresponding dataset instances.

        This method returns a list of tuples, where each tuple contains a dataset
        name and its corresponding dataset instance.

        Returns:
            A list of tuples containing dataset names and their corresponding dataset instances.

        Example:
        ```python

            from kedro.io import DataCatalog, MemoryDataset
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            dataset_items = catalog.items()
            print(dataset_items)
            # [('example', kedro.io.memory_dataset.MemoryDataset())]
        ```
        """
        return [(key, self[key]) for key in self]

    def __iter__(self) -> Iterator[str]:
        """
        Iterate over all dataset names in the catalog, including both materialized and lazy datasets.

        Yields:
            Dataset names.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            for dataset_name in catalog:
                print(dataset_name)
            # example
        ```
        """
        yield from self.keys()

    def __getitem__(self, ds_name: str) -> AbstractDataset:
        """
        Get a dataset by name from the catalog.

        If a dataset is not materialized but matches dataset_pattern or user_catch_all_pattern
        by default or runtime_patterns if fallback_to_runtime_pattern is enabled,
        it is instantiated and added to the catalog first, then returned.

        Args:
            ds_name: The name of the dataset.

        Returns:
            The dataset instance.

        Raises:
            DatasetNotFoundError: If the dataset is not found.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            dataset = catalog["example"]
            print(dataset)
            # MemoryDataset()
        ```
        """
        dataset = self.get(ds_name)
        if dataset is None:
            raise DatasetNotFoundError(f"Dataset '{ds_name}' not found in the catalog")
        return dataset

    def __setitem__(self, key: str, value: Any) -> None:
        """Registers a dataset or raw data into the catalog using the specified name.

        If the name already exists, the dataset will be replaced and relevant internal mappings
        (lazy datasets, config, versions) will be cleared to avoid conflicts.

        The value can either be raw data or a Kedro dataset (i.e., an instance of a class
        inheriting from ``AbstractDataset``). If raw data is provided, it will be automatically
        wrapped in a ``MemoryDataset`` before being added to the catalog.

        Args:
            key: Name of the dataset.
            value: Either an instance of `AbstractDataset`, `_LazyDataset`, or raw data (e.g., DataFrame, list).
                If raw data is provided, it is automatically wrapped as a `MemoryDataset`.

        Example:
        ```python

            from kedro_datasets.pandas import CSVDataset
            import pandas as pd
            df = pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})
            catalog = DataCatalog()
            catalog["data_df"] = df  # Add raw data as a MemoryDataset

            assert catalog.load("data_df").equals(df)

            csv_dataset = CSVDataset(filepath="test.csv")
            csv_dataset.save(df)
            catalog["data_csv_dataset"] = csv_dataset  # Add a dataset instance

            assert catalog.load("data_csv_dataset").equals(df)
        ```
        """
        if key in self._datasets or key in self._lazy_datasets:
            self._logger.warning("Replacing dataset '%s'", key)
            self._datasets.pop(key, None)
            self._lazy_datasets.pop(key, None)
            self._config_resolver.config.pop(key, None)
            self._load_versions.pop(key, None)
        if isinstance(value, AbstractDataset):
            self._load_versions, self._save_version = self._validate_versions(
                {key: value}, self._load_versions, self._save_version
            )
            self._datasets[key] = value
        elif isinstance(value, _LazyDataset):
            self._lazy_datasets[key] = value
        else:
            self._logger.debug(f"Adding input data {key} as a default MemoryDataset")
            self._datasets[key] = MemoryDataset(data=value)  # type: ignore[abstract]

    def __len__(self) -> int:
        """
        Get the number of datasets registered in the catalog, including both materialized and lazy datasets.

        Returns:
            The number of datasets.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            len(catalog)
            # 1
        ```
        """
        return len(self.keys())

    def get(
        self,
        key: str,
        fallback_to_runtime_pattern: bool = False,
        version: Version | None = None,
    ) -> AbstractDataset | None:
        """Get a dataset by name from an internal collection of datasets.

        If a dataset is not materialized but matches dataset_pattern or user_catch_all_pattern
        by default or runtime_patterns if fallback_to_runtime_pattern is enabled
        it is instantiated and added to the catalog first, then returned.

        Args:
            key: A dataset name.
            fallback_to_runtime_pattern: Whether to use runtime_pattern to resolve dataset.
            version: Optional argument to get a specific version of the dataset.

        Returns:
            The dataset instance if found, otherwise None.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            dataset = catalog.get("example")
            print(dataset)
            # MemoryDataset()

            missing = catalog.get("nonexistent")
            print(missing)
            # None
        ```
        """
        if key not in self and not fallback_to_runtime_pattern:
            return None

        if not (key in self._datasets or key in self._lazy_datasets):
            ds_config = self._config_resolver.resolve_pattern(key)
            if ds_config:
                self._add_from_config(key, ds_config)

        lazy_dataset = self._lazy_datasets.pop(key, None)
        if lazy_dataset:
            self[key] = lazy_dataset.materialize()

        dataset = self._datasets[key]

        if version and isinstance(dataset, AbstractVersionedDataset):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            dataset = dataset._copy(_version=version)

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
    ) -> DataCatalog:
        """Create a ``DataCatalog`` instance from configuration. This is a
        factory method used to provide developers with a way to instantiate
        ``DataCatalog`` with configuration parsed from configuration files.

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
            An instantiated ``DataCatalog`` containing all specified
            datasets, created and ready to use.

        Raises:
            DatasetNotFoundError: When `load_versions` refers to a dataset that doesn't
                exist in the catalog.

        Example:
        ```python
            config = {
                "cars": {
                    "type": "pandas.CSVDataset",
                    "filepath": "cars.csv",
                    "save_args": {"index": False}
                },
                "boats": {
                    "type": "pandas.CSVDataset",
                    "filepath": "s3://aws-bucket-name/boats.csv",
                    "credentials": "boats_credentials",
                    "save_args": {"index": False}
                }
            }
            credentials = {
                "boats_credentials": {
                    "client_kwargs": {
                        "aws_access_key_id": "<your key id>",
                        "aws_secret_access_key": "<your secret>"
                    }
                }
            }

            catalog = DataCatalog.from_config(config, credentials)
            df = catalog.load("cars")

            catalog.save("boats", df)
        ```
        """
        catalog = catalog or {}
        config_resolver = CatalogConfigResolver(
            catalog, credentials, cls.default_runtime_patterns
        )
        save_version = save_version or generate_timestamp()
        load_versions = load_versions or {}

        missing_keys = [
            ds_name
            for ds_name in load_versions
            if not (
                ds_name in config_resolver.config
                or config_resolver.match_dataset_pattern(ds_name)
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
        """Converts the `DataCatalog` instance into a configuration format suitable for
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
        ```python
            from kedro.io import DataCatalog
            from kedro_datasets.pandas import CSVDataset

            cars = CSVDataset(
                filepath="cars.csv",
                load_args=None,
                save_args={"index": False}
            )
            catalog = DataCatalog(datasets={'cars': cars})

            config, credentials, load_versions, save_version = catalog.to_config()

            new_catalog = DataCatalog.from_config(config, credentials, load_versions, save_version)
        ```
        """
        catalog: dict[str, dict[str, Any]] = {}
        credentials: dict[str, dict[str, Any]] = {}
        load_versions: dict[str, str | None] = {}

        for ds_name, ds in self._lazy_datasets.items():
            if _is_memory_dataset(ds.config.get(TYPE_KEY, "")):
                continue
            unresolved_config, unresolved_credentials = (
                self._config_resolver._unresolve_credentials(ds_name, ds.config)
            )
            catalog[ds_name] = unresolved_config
            credentials.update(unresolved_credentials)
            load_versions[ds_name] = self._load_versions.get(ds_name, None)

        for ds_name, ds in self._datasets.items():  # type: ignore[assignment]
            if _is_memory_dataset(ds):  # type: ignore[arg-type]
                continue
            resolved_config = ds._init_config()  # type: ignore[attr-defined]
            unresolved_config, unresolved_credentials = (
                self._config_resolver._unresolve_credentials(ds_name, resolved_config)
            )
            catalog[ds_name] = unresolved_config
            credentials.update(unresolved_credentials)
            load_versions[ds_name] = self._load_versions.get(ds_name, None)

        return catalog, credentials, load_versions, self._save_version

    @staticmethod
    def _validate_dataset_config(ds_name: str, ds_config: Any) -> None:
        """
        Validate the configuration of a dataset in the catalog.

        This method ensures that the dataset configuration is a dictionary and contains
        the required "type" key. If the configuration is invalid, it raises a `DatasetError`
        with a helpful error message.

        Args:
            ds_name: The name of the dataset being validated.
            ds_config: The configuration of the dataset to validate.

        Raises:
            DatasetError: If the dataset configuration is not a dictionary or if the
                "type" key is missing from the configuration.

        Example:
        ```python
            config = {
                "example_dataset": {
                    "type": "pandas.CSVDataset",
                    "filepath": "example.csv",
                }
            }
            DataCatalog._validate_dataset_config("example_dataset", config["example_dataset"])
            # No error raised

            invalid_config = {"example_dataset": {"filepath": "example.csv"}}
            DataCatalog._validate_dataset_config("example_dataset", invalid_config["example_dataset"])
            # Raises DatasetError: 'type' is missing from dataset catalog configuration.
        ```
        """
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
        """
        Create a `_LazyDataset` instance from the provided configuration and add it to the catalog.

        This method validates the dataset configuration, creates a `_LazyDataset` instance,
        and registers it in the catalog. The `_LazyDataset` is a placeholder for a dataset
        that will be materialized only when accessed.

        Args:
            ds_name: The name of the dataset to be added.
            ds_config: The configuration dictionary for the dataset.

        Raises:
            DatasetError: If the provided dataset configuration is invalid (e.g., missing
                required keys like "type" or improperly formatted).

        Example:
        ```python
            catalog = DataCatalog()
            dataset_config = {"type": "pandas.CSVDataset", "filepath": "example.csv"}
            catalog._add_from_config("example_dataset", dataset_config)
            "example_dataset" in catalog
            # True
        ```
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
        ```python
            import re
            catalog = DataCatalog()
            # get datasets where the substring 'raw' is present
            raw_data = catalog.filter(name_regex='raw')
            # get datasets where names start with 'model_' (precompiled regex)
            model_datasets = catalog.filter(name_regex=re.compile('^model_'))
            # get datasets of a specific type using type_regex
            csv_datasets = catalog.filter(type_regex='pandas.excel_dataset.ExcelDataset')
            # get datasets where names contain 'train' and type matches 'CSV' in the path
            catalog.filter(name_regex="train", type_regex="CSV")
            # get datasets where names include 'data' and are of a specific type
            from kedro_datasets.pandas import SQLQueryDataset
            catalog.filter(name_regex="data", by_type=SQLQueryDataset)
            # get datasets where names include 'data' and are of multiple specific types
            from kedro.io import MemoryDataset
            catalog.filter(name_regex="data", by_type=[MemoryDataset, SQLQueryDataset])
        ```

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
                str_type = self.get_type(ds_name) or ""
                # Match against type_regex and apply by_type filtering
                if (not type_regex or re.search(type_regex, str_type)) and (
                    not by_type_set or str_type in by_type_set
                ):
                    filtered_types.append(ds_name)

            return filtered_types

        return filtered

    def get_type(self, ds_name: str) -> str | None:
        """
        Access dataset type without adding resolved dataset to the catalog.

        Args:
            ds_name: The name of the dataset whose type is to be retrieved.

        Returns:
            The fully qualified type of the dataset (e.g., `kedro.io.memory_dataset.MemoryDataset`)
            or None if dataset does not match dataset_patterns or user_catch_all_pattern.

        Example:
        ```python
            from kedro.io import DataCatalog, MemoryDataset
            catalog = DataCatalog(datasets={"example": MemoryDataset()})
            dataset_type = catalog.get_type("example")
            print(dataset_type)
            # kedro.io.memory_dataset.MemoryDataset

            missing_type = catalog.get_type("nonexistent")
            print(missing_type)
            # None
        ```
        """
        if ds_name not in self:
            return None

        if ds_name not in self._datasets and ds_name not in self._lazy_datasets:
            ds_config = self._config_resolver.resolve_pattern(ds_name)
            return str(_LazyDataset(ds_name, ds_config))

        if ds_name in self._lazy_datasets:
            return str(self._lazy_datasets[ds_name])

        class_type = type(self._datasets[ds_name])
        return f"{class_type.__module__}.{class_type.__qualname__}"

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
        ```python
            import pandas as pd

            from kedro.io import DataCatalog
            from kedro_datasets.pandas import CSVDataset

            cars = CSVDataset(filepath="cars.csv", load_args=None, save_args={"index": False})
            catalog = DataCatalog(datasets={'cars': cars})
            df = pd.DataFrame({'col1': [1, 2], 'col2': [4, 5], 'col3': [5, 6]})
            catalog.save("cars", df)
        ```
        """
        dataset = self[ds_name]

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
        ```python
            from kedro.io import DataCatalog
            from kedro_datasets.pandas import CSVDataset
            cars = CSVDataset(filepath="cars.csv", load_args=None, save_args={"index": False})
            catalog = DataCatalog(datasets={'cars': cars})
            df = catalog.load("cars")
        ```
        """
        load_version = Version(version, None) if version else None
        dataset = self.get(ds_name, version=load_version)

        if dataset is None:
            error_msg = f"Dataset '{ds_name}' not found in the catalog"
            raise DatasetNotFoundError(error_msg)

        self._logger.info(
            "Loading data from %s (%s)...",
            _format_rich(ds_name, "dark_orange") if self._use_rich_markup else ds_name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        return dataset.load()

    def release(self, ds_name: str) -> None:
        """Release any cached data associated with a dataset
        Args:
            ds_name: A dataset to be checked.
        Raises:
            DatasetNotFoundError: When a dataset with the given name
                has not yet been registered.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset(data=[1, 2, 3])})
            catalog.release("example")
        ```
        """
        dataset = self[ds_name]

        dataset.release()

    def confirm(self, ds_name: str) -> None:
        """Confirm a dataset by its name.
        Args:
            ds_name: Name of the dataset.
        Raises:
            DatasetNotFoundError: When a dataset with the given name
                has not yet been registered
            DatasetError: When the dataset does not have `confirm` method.
        """
        self._logger.info("Confirming dataset '%s'", ds_name)

        dataset = self[ds_name]

        if hasattr(dataset, "confirm"):
            dataset.confirm()
        else:
            raise DatasetError(f"Dataset '{ds_name}' does not have 'confirm' method")

    def exists(self, ds_name: str) -> bool:
        """Checks whether registered dataset exists by calling its `exists()`
        method. Raises a warning and returns False if `exists()` is not
        implemented.

        Args:
            ds_name: A dataset to be checked.

        Returns:
            Whether the dataset and its output exist.

        Example:
        ```python
            catalog = DataCatalog(datasets={"example": MemoryDataset(data=[1, 2, 3])})
            catalog.exists("example")
            True
        ```
        """
        dataset = self.get(ds_name)
        return dataset.exists() if dataset else False

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


class SharedMemoryDataCatalog(DataCatalog):
    """
    A specialized `DataCatalog` for managing datasets in a shared memory context.

    The `SharedMemoryDataCatalog` extends the base `DataCatalog` to support multiprocessing
    by ensuring that datasets are serializable and synchronized across threads or processes.
    It provides additional functionality for managing shared memory datasets, such as setting
    a multiprocessing manager and validating dataset compatibility with multiprocessing.

    Attributes:
        default_runtime_patterns (ClassVar): A dictionary defining the default runtime pattern
            for datasets of type `kedro.io.SharedMemoryDataset`.

    Example:
    ``` python

        from multiprocessing.managers import SyncManager
        from kedro.io import MemoryDataset
        from kedro.io.data_catalog import SharedMemoryDataCatalog

        # Create a shared memory catalog
        catalog = SharedMemoryDataCatalog(
            datasets={"shared_data": MemoryDataset(data=[1, 2, 3])}
        )

        # Set a multiprocessing manager
        manager = SyncManager()
        manager.start()
        catalog.set_manager_datasets(manager)

        # Validate the catalog for multiprocessing compatibility
        catalog.validate_catalog()
    ```
    """

    default_runtime_patterns: ClassVar = {
        "{default}": {"type": "kedro.io.SharedMemoryDataset"}
    }

    def set_manager_datasets(self, manager: SyncManager) -> None:
        """
        Associate a multiprocessing manager with all shared memory datasets in the catalog.

        This method iterates through all datasets in the catalog and sets the provided
        multiprocessing manager for datasets of type `SharedMemoryDataset`. This ensures
        that these datasets are properly synchronized across threads or processes.

        Args:
            manager: A multiprocessing manager to be associated with
                shared memory datasets.

        Example:
        ```python
            from multiprocessing.managers import SyncManager
            from kedro.io.data_catalog import SharedMemoryDataCatalog
            catalog = SharedMemoryDataCatalog(datasets={"shared_data": MemoryDataset(data=[1, 2, 3])})
            manager = SyncManager()
            manager.start()
            catalog.set_manager_datasets(manager)
            print(catalog)
            # {'shared_data': kedro.io.memory_dataset.MemoryDataset(data='<list>')}
        ```
        """
        for _, ds in self._datasets.items():
            if isinstance(ds, SharedMemoryDataset):
                ds.set_manager(manager)

    def validate_catalog(self) -> None:
        """
        Validate the catalog to ensure all datasets are serializable and compatible with multiprocessing.

        This method checks that all datasets in the catalog are serializable and do not
        include non-proxied memory datasets as outputs. Non-serializable datasets or
        datasets that rely on single-process memory cannot be used in a multiprocessing
        context. If any such datasets are found, an exception is raised with details.

        Raises:
            AttributeError: If any datasets are found to be non-serializable or incompatible
                with multiprocessing.

        Example:
        ```python
            from kedro.io.data_catalog import SharedMemoryDataCatalog

            catalog = SharedMemoryDataCatalog(datasets={"shared_data": MemoryDataset(data=[1, 2, 3])})
            try:
                catalog.validate_catalog()
            except AttributeError as e:
                print(f"Validation failed: {e}")
            # No error
        ```
        """
        unserialisable = []
        for name, dataset in self._datasets.items():
            if getattr(dataset, "_SINGLE_PROCESS", False):  # SKIP_IF_NO_SPARK
                unserialisable.append(name)
                continue
            try:
                ForkingPickler.dumps(dataset)
            except (AttributeError, PicklingError):
                unserialisable.append(name)

        if unserialisable:
            raise AttributeError(
                f"The following datasets cannot be used with multiprocessing: "
                f"{sorted(unserialisable)}\nIn order to utilize multiprocessing you "
                f"need to make sure all datasets are serialisable, i.e. datasets "
                f"should not make use of lambda functions, nested functions, closures "
                f"etc.\nIf you are using custom decorators ensure they are correctly "
                f"decorated using functools.wraps()."
            )
