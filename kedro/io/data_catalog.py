"""``DataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``DataCatalog``, you need to instantiate it with a dictionary of data
sets. Then it will act as a single point of reference for your calls,
relaying load and save functions to the underlying datasets.
"""

from __future__ import annotations

import difflib
import logging
import pprint
import re
import warnings
from typing import Any

from kedro import KedroDeprecationWarning
from kedro.io.catalog_config_resolver import (
    CREDENTIALS_KEY,  # noqa: F401
    CatalogConfigResolver,
    Patterns,
)
from kedro.io.core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
    _validate_versions,
    generate_timestamp,
)
from kedro.io.memory_dataset import MemoryDataset
from kedro.io.warning_utils import is_warning_suppressed, suppress_catalog_warning
from kedro.utils import _has_rich_handler

CATALOG_KEY = "catalog"  # Kept to avoid the breaking change
WORDS_REGEX_PATTERN = re.compile(r"\W+")


def _sub_nonword_chars(dataset_name: str) -> str:
    """Replace non-word characters in dataset names since Kedro 0.16.2.

    Args:
        dataset_name: The dataset name registered in the data catalog.

    Returns:
        The name used in `DataCatalog.datasets`.
    """
    return re.sub(WORDS_REGEX_PATTERN, "__", dataset_name)


class _FrozenDatasets:
    """Helper class to access underlying loaded datasets."""

    def __init__(
        self,
        *datasets_collections: _FrozenDatasets | dict[str, AbstractDataset] | None,
    ):
        """Return a _FrozenDatasets instance from some datasets collections.
        Each collection could either be another _FrozenDatasets or a dictionary.
        """
        self._original_names: dict[str, str] = {}
        for collection in datasets_collections:
            if collection is None:
                continue
            if isinstance(collection, _FrozenDatasets):
                self.__dict__.update(collection.__dict__)
                self._original_names.update(collection._original_names)
            else:
                # Non-word characters in dataset names are replaced with `__`
                # for easy access to transcoded/prefixed datasets.
                for dataset_name, dataset in collection.items():
                    self.__dict__[_sub_nonword_chars(dataset_name)] = dataset
                    self._original_names[dataset_name] = ""

    # Don't allow users to add/change attributes on the fly
    def __setattr__(self, key: str, value: Any) -> None:
        if key == "_original_names":
            super().__setattr__(key, value)
            return
        msg = "Operation not allowed. "
        if key in self.__dict__:
            msg += "Please change datasets through configuration."
        else:
            msg += "Please use DataCatalog.add() instead."
        raise AttributeError(msg)

    def _ipython_key_completions_(self) -> list[str]:
        return list(self._original_names.keys())

    def __getitem__(self, key: str) -> Any:
        return self.__dict__[_sub_nonword_chars(key)]

    def __repr__(self) -> str:  # pragma: no cover
        datasets_repr = {}
        for ds_name in self._original_names.keys():
            datasets_repr[ds_name] = self.__dict__[
                _sub_nonword_chars(ds_name)
            ].__repr__()

        return pprint.pformat(datasets_repr, sort_dicts=False)


class DataCatalog:
    """``DataCatalog`` stores instances of ``AbstractDataset`` implementations
    to provide ``load`` and ``save`` capabilities from anywhere in the
    program. To use a ``DataCatalog``, you need to instantiate it with
    a dictionary of datasets. Then it will act as a single point of reference
    for your calls, relaying load and save functions
    to the underlying datasets.
    """

    def __init__(  # noqa: PLR0913
        self,
        datasets: dict[str, AbstractDataset] | None = None,
        feed_dict: dict[str, Any] | None = None,
        dataset_patterns: Patterns | None = None,  # Kept for interface compatibility
        load_versions: dict[str, str] | None = None,
        save_version: str | None = None,
        default_pattern: Patterns | None = None,  # Kept for interface compatibility
        config_resolver: CatalogConfigResolver | None = None,
    ) -> None:
        """``DataCatalog`` stores instances of ``AbstractDataset``
        implementations to provide ``load`` and ``save`` capabilities from
        anywhere in the program. To use a ``DataCatalog``, you need to
        instantiate it with a dictionary of datasets. Then it will act as a
        single point of reference for your calls, relaying load and save
        functions to the underlying datasets.

        Args:
            datasets: A dictionary of dataset names and dataset instances.
            feed_dict: A feed dict with data to be added in memory.
            dataset_patterns: A dictionary of dataset factory patterns
                and corresponding dataset configuration. When fetched from catalog configuration
                these patterns will be sorted by:
                1. Decreasing specificity (number of characters outside the curly brackets)
                2. Decreasing number of placeholders (number of curly bracket pairs)
                3. Alphabetically
                A pattern of specificity 0 is a catch-all pattern and will overwrite the default
                pattern provided through the runners if it comes before "default" in the alphabet.
                Such an overwriting pattern will emit a warning. The `"{default}"` name will
                not emit a warning.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on datasets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all datasets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.
            default_pattern: A dictionary of the default catch-all pattern that overrides the default
                pattern provided through the runners.
            config_resolver: An instance of CatalogConfigResolver to resolve dataset patterns and configurations.


        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> cars = CSVDataset(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> catalog = DataCatalog(datasets={'cars': cars})
        """
        if not is_warning_suppressed():
            warnings.warn(
                "Several APIs currently available, "
                "including `datasets`, `get_datasets`, `_get_datasets`, `add`, `list`, "
                "`add_feed_dict`, and `shallow_copy`, will be removed or replaced in Kedro 1.0.0. "
                "For more details, refer to the documentation: "
                "https://docs.kedro.org/en/0.19.13/data/index.html#kedrodatacatalog-experimental-feature",
                KedroDeprecationWarning,
                stacklevel=2,
            )
        self._config_resolver = config_resolver or CatalogConfigResolver()
        # Kept to avoid breaking changes
        if not config_resolver:
            self._config_resolver._dataset_patterns = dataset_patterns or {}
            self._config_resolver._default_pattern = default_pattern or {}

        self._load_versions, self._save_version = _validate_versions(
            datasets, load_versions or {}, save_version
        )

        self._datasets: dict[str, AbstractDataset] = {}
        self.datasets: _FrozenDatasets | None = None

        self.add_all(datasets or {})

        self._use_rich_markup = _has_rich_handler()

        if feed_dict:
            self.add_feed_dict(feed_dict)

    def __repr__(self) -> str:  # pragma: no cover
        return self.datasets.__repr__()

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

    @property
    def config_resolver(self) -> CatalogConfigResolver:
        return self._config_resolver

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
            DatasetError: When the method fails to create any of the data
                sets from their config.
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
            >>> catalog = DataCatalog.from_config(config, credentials)
            >>>
            >>> df = catalog.load("cars")
            >>> catalog.save("boats", df)
        """
        catalog = catalog or {}
        datasets = {}
        config_resolver = CatalogConfigResolver(catalog, credentials)
        save_version = save_version or generate_timestamp()
        load_versions = load_versions or {}

        for ds_name in catalog:
            if not config_resolver.is_pattern(ds_name):
                datasets[ds_name] = AbstractDataset.from_config(
                    ds_name,
                    config_resolver.config.get(ds_name, {}),
                    load_versions.get(ds_name),
                    save_version,
                )

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
            datasets=datasets,
            dataset_patterns=config_resolver._dataset_patterns,
            load_versions=load_versions,
            save_version=save_version,
            default_pattern=config_resolver._default_pattern,
            config_resolver=config_resolver,
        )

    def _get_dataset(
        self,
        dataset_name: str,
        version: Version | None = None,
        suggest: bool = True,
    ) -> AbstractDataset:
        ds_config = self._config_resolver.resolve_pattern(dataset_name)

        if dataset_name not in self._datasets and ds_config:
            ds = AbstractDataset.from_config(
                dataset_name,
                ds_config,
                self._load_versions.get(dataset_name),
                self._save_version,
            )
            self.add(dataset_name, ds)
        if dataset_name not in self._datasets:
            error_msg = f"Dataset '{dataset_name}' not found in the catalog"

            # Flag to turn on/off fuzzy-matching which can be time consuming and
            # slow down plugins like `kedro-viz`
            if suggest:
                matches = difflib.get_close_matches(dataset_name, self._datasets.keys())
                if matches:
                    suggestions = ", ".join(matches)
                    error_msg += f" - did you mean one of these instead: {suggestions}"
            raise DatasetNotFoundError(error_msg)

        dataset = self._datasets[dataset_name]

        if version and isinstance(dataset, AbstractVersionedDataset):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            dataset = dataset._copy(_version=version)

        return dataset

    def load(self, name: str, version: str | None = None) -> Any:
        """Loads a registered dataset.

        Args:
            name: A dataset to be loaded.
            version: Optional argument for concrete data version to be loaded.
                Works only with versioned datasets.

        Returns:
            The loaded data as configured.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
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
        dataset = self._get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from %s (%s)...",
            name,
            type(dataset).__name__,
            extra={"rich_format": ["dark_orange"]},
        )

        result = dataset.load()

        return result

    def save(self, name: str, data: Any) -> None:
        """Save data to a registered dataset.

        Args:
            name: A dataset to be saved to.
            data: A data object to be saved as configured in the registered
                dataset.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
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
        dataset = self._get_dataset(name)

        self._logger.info(
            "Saving data to %s (%s)...",
            name,
            type(dataset).__name__,
            extra={"rich_format": ["dark_orange"]},
        )

        dataset.save(data)

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

    def release(self, name: str) -> None:
        """Release any cached data associated with a dataset

        Args:
            name: A dataset to be checked.

        Raises:
            DatasetNotFoundError: When a dataset with the given name
                has not yet been registered.
        """
        dataset = self._get_dataset(name)
        dataset.release()

    def add(
        self,
        dataset_name: str,
        dataset: AbstractDataset,
        replace: bool = False,
    ) -> None:
        """Adds a new ``AbstractDataset`` object to the ``DataCatalog``.

        Args:
            dataset_name: A unique dataset name which has not been
                registered yet.
            dataset: A dataset object to be associated with the given data
                set name.
            replace: Specifies whether to replace an existing dataset
                with the same name is allowed.

        Raises:
            DatasetAlreadyExistsError: When a dataset with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> catalog = DataCatalog(datasets={
            >>>                   'cars': CSVDataset(filepath="cars.csv")
            >>>                  })
            >>>
            >>> catalog.add("boats", CSVDataset(filepath="boats.csv"))
        """
        if dataset_name in self._datasets:
            if replace:
                self._logger.warning("Replacing dataset '%s'", dataset_name)
            else:
                raise DatasetAlreadyExistsError(
                    f"Dataset '{dataset_name}' has already been registered"
                )
        self._load_versions, self._save_version = _validate_versions(
            {dataset_name: dataset}, self._load_versions, self._save_version
        )
        self._datasets[dataset_name] = dataset
        self.datasets = _FrozenDatasets(self.datasets, {dataset_name: dataset})

    def add_all(
        self,
        datasets: dict[str, AbstractDataset],
        replace: bool = False,
    ) -> None:
        """Adds a group of new datasets to the ``DataCatalog``.

        Args:
            datasets: A dictionary of dataset names and dataset
                instances.
            replace: Specifies whether to replace an existing dataset
                with the same name is allowed.

        Raises:
            DatasetAlreadyExistsError: When a dataset with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset, ParquetDataset
            >>>
            >>> catalog = DataCatalog(datasets={
            >>>                   "cars": CSVDataset(filepath="cars.csv")
            >>>                  })
            >>> additional = {
            >>>     "planes": ParquetDataset("planes.parq"),
            >>>     "boats": CSVDataset(filepath="boats.csv")
            >>> }
            >>>
            >>> catalog.add_all(additional)
            >>>
            >>> assert catalog.list() == ["cars", "planes", "boats"]
        """
        for ds_name, ds in datasets.items():
            self.add(ds_name, ds, replace)

    def add_feed_dict(self, feed_dict: dict[str, Any], replace: bool = False) -> None:
        """Add datasets to the ``DataCatalog`` using the data provided through the `feed_dict`.

        `feed_dict` is a dictionary where the keys represent dataset names and the values can either be raw data or
        Kedro datasets - instances of classes that inherit from ``AbstractDataset``. If raw data is provided,
        it will be automatically wrapped in a ``MemoryDataset`` before being added to the ``DataCatalog``.

        Args:
            feed_dict: A dictionary with data to be added to the ``DataCatalog``. Keys are dataset names and
                values can be raw data or instances of classes that inherit from ``AbstractDataset``.
            replace: Specifies whether to replace an existing dataset with the same name in the ``DataCatalog``.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset
            >>> import pandas as pd
            >>>
            >>> df = pd.DataFrame({"col1": [1, 2],
            >>>                    "col2": [4, 5],
            >>>                    "col3": [5, 6]})
            >>>
            >>> catalog = DataCatalog()
            >>> catalog.add_feed_dict({
            >>>     "data_df": df
            >>> }, replace=True)
            >>>
            >>> assert catalog.load("data_df").equals(df)
            >>>
            >>> csv_dataset = CSVDataset(filepath="test.csv")
            >>> csv_dataset.save(df)
            >>> catalog.add_feed_dict({"data_csv_dataset": csv_dataset})
            >>>
            >>> assert catalog.load("data_csv_dataset").equals(df)
        """
        for ds_name, ds_data in feed_dict.items():
            dataset = (
                ds_data
                if isinstance(ds_data, AbstractDataset)
                else MemoryDataset(data=ds_data)  # type: ignore[abstract]
            )
            self.add(ds_name, dataset, replace)

    def list(self, regex_search: str | None = None) -> list[str]:
        """
        List of all dataset names registered in the catalog.
        This can be filtered by providing an optional regular expression
        which will only return matching keys.

        Args:
            regex_search: An optional regular expression which can be provided
                to limit the datasets returned by a particular pattern.
        Returns:
            A list of dataset names available which match the
            `regex_search` criteria (if provided). All dataset names are returned
            by default.

        Raises:
            SyntaxError: When an invalid regex filter is provided.

        Example:
        ::

            >>> catalog = DataCatalog()
            >>> # get datasets where the substring 'raw' is present
            >>> raw_data = catalog.list(regex_search='raw')
            >>> # get datasets which start with 'prm' or 'feat'
            >>> feat_eng_data = catalog.list(regex_search='^(prm|feat)')
            >>> # get datasets which end with 'time_series'
            >>> models = catalog.list(regex_search='.+time_series$')
        """

        if regex_search is None:
            return list(self._datasets.keys())

        if not regex_search.strip():
            self._logger.warning("The empty string will not match any datasets")
            return []

        try:
            pattern = re.compile(regex_search, flags=re.IGNORECASE)

        except re.error as exc:
            raise SyntaxError(
                f"Invalid regular expression provided: '{regex_search}'"
            ) from exc
        return [ds_name for ds_name in self._datasets if pattern.search(ds_name)]

    def shallow_copy(
        self, extra_dataset_patterns: Patterns | None = None
    ) -> DataCatalog:
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        with suppress_catalog_warning():
            if extra_dataset_patterns:
                self._config_resolver.add_runtime_patterns(extra_dataset_patterns)
            return self.__class__(
                datasets=self._datasets,
                dataset_patterns=self._config_resolver._dataset_patterns,
                default_pattern=self._config_resolver._default_pattern,
                load_versions=self._load_versions,
                save_version=self._save_version,
                config_resolver=self._config_resolver,
            )

    def confirm(self, name: str) -> None:
        """Confirm a dataset by its name.

        Args:
            name: Name of the dataset.
        Raises:
            DatasetError: When the dataset does not have `confirm` method.

        """
        self._logger.info("Confirming dataset '%s'", name)
        dataset = self._get_dataset(name)

        if hasattr(dataset, "confirm"):
            dataset.confirm()
        else:
            raise DatasetError(f"Dataset '{name}' does not have 'confirm' method")
