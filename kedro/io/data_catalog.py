"""``DataCatalog`` stores instances of ``AbstractDataset`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``DataCatalog``, you need to instantiate it with a dictionary of data
sets. Then it will act as a single point of reference for your calls,
relaying load and save functions to the underlying data sets.
"""
from __future__ import annotations

import copy
import difflib
import logging
import re
from collections import defaultdict
from typing import Any, Dict

from parse import parse

from kedro import KedroDeprecationWarning
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

Patterns = Dict[str, Dict[str, Any]]

CATALOG_KEY = "catalog"
CREDENTIALS_KEY = "credentials"
WORDS_REGEX_PATTERN = re.compile(r"\W+")


def _get_credentials(
    credentials_name: str, credentials: dict[str, Any]
) -> dict[str, Any]:
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


def _sub_nonword_chars(dataset_name: str) -> str:
    """Replace non-word characters in data set names since Kedro 0.16.2.

    Args:
        dataset_name: The data set name registered in the data catalog.

    Returns:
        The name used in `DataCatalog.datasets`.
    """
    return re.sub(WORDS_REGEX_PATTERN, "__", dataset_name)


class _FrozenDatasets:
    """Helper class to access underlying loaded datasets."""

    def __init__(
        self,
        *datasets_collections: _FrozenDatasets | dict[str, AbstractDataset],
    ):
        """Return a _FrozenDatasets instance from some datasets collections.
        Each collection could either be another _FrozenDatasets or a dictionary.
        """
        for collection in datasets_collections:
            if isinstance(collection, _FrozenDatasets):
                self.__dict__.update(collection.__dict__)
            else:
                # Non-word characters in dataset names are replaced with `__`
                # for easy access to transcoded/prefixed datasets.
                self.__dict__.update(
                    {
                        _sub_nonword_chars(dataset_name): dataset
                        for dataset_name, dataset in collection.items()
                    }
                )

    # Don't allow users to add/change attributes on the fly
    def __setattr__(self, key, value):
        msg = "Operation not allowed! "
        if key in self.__dict__:
            msg += "Please change datasets through configuration."
        else:
            msg += "Please use DataCatalog.add() instead."
        raise AttributeError(msg)


class DataCatalog:
    """``DataCatalog`` stores instances of ``AbstractDataset`` implementations
    to provide ``load`` and ``save`` capabilities from anywhere in the
    program. To use a ``DataCatalog``, you need to instantiate it with
    a dictionary of data sets. Then it will act as a single point of reference
    for your calls, relaying load and save functions
    to the underlying data sets.
    """

    def __init__(  # noqa: too-many-arguments
        self,
        datasets: dict[str, AbstractDataset] = None,
        feed_dict: dict[str, Any] = None,
        layers: dict[str, set[str]] = None,
        dataset_patterns: Patterns = None,
        load_versions: dict[str, str] = None,
        save_version: str = None,
    ) -> None:
        """``DataCatalog`` stores instances of ``AbstractDataset``
        implementations to provide ``load`` and ``save`` capabilities from
        anywhere in the program. To use a ``DataCatalog``, you need to
        instantiate it with a dictionary of data sets. Then it will act as a
        single point of reference for your calls, relaying load and save
        functions to the underlying data sets.

        Args:
            datasets: A dictionary of data set names and data set instances.
            feed_dict: A feed dict with data to be added in memory.
            layers: A dictionary of data set layers. It maps a layer name
                to a set of data set names, according to the
                data engineering convention. For more details, see
                https://docs.kedro.org/en/stable/resources/glossary.html#layers-data-engineering-convention
            dataset_patterns: A dictionary of data set factory patterns
                and corresponding data set configuration
            load_versions: A mapping between data set names and versions
                to load. Has no effect on data sets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all data sets with enabled versioning. It must: a) be a
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
            >>> io = DataCatalog(datasets={'cars': cars})
        """
        self._datasets = dict(datasets or {})
        self.datasets = _FrozenDatasets(self._datasets)
        self.layers = layers
        # Keep a record of all patterns in the catalog.
        # {dataset pattern name : dataset pattern body}
        self._dataset_patterns = dataset_patterns or {}
        self._load_versions = load_versions or {}
        self._save_version = save_version

        if feed_dict:
            self.add_feed_dict(feed_dict)

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    @classmethod
    def from_config(
        cls,
        catalog: dict[str, dict[str, Any]] | None,
        credentials: dict[str, dict[str, Any]] = None,
        load_versions: dict[str, str] = None,
        save_version: str = None,
    ) -> DataCatalog:
        """Create a ``DataCatalog`` instance from configuration. This is a
        factory method used to provide developers with a way to instantiate
        ``DataCatalog`` with configuration parsed from configuration files.

        Args:
            catalog: A dictionary whose keys are the data set names and
                the values are dictionaries with the constructor arguments
                for classes implementing ``AbstractDataset``. The data set
                class to be loaded is specified with the key ``type`` and their
                fully qualified class name. All ``kedro.io`` data set can be
                specified by their class name only, i.e. their module name
                can be omitted.
            credentials: A dictionary containing credentials for different
                data sets. Use the ``credentials`` key in a ``AbstractDataset``
                to refer to the appropriate credentials as shown in the example
                below.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on data sets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all data sets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.

        Returns:
            An instantiated ``DataCatalog`` containing all specified
            data sets, created and ready to use.

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
        datasets = {}
        dataset_patterns = {}
        catalog = copy.deepcopy(catalog) or {}
        credentials = copy.deepcopy(credentials) or {}
        save_version = save_version or generate_timestamp()
        load_versions = copy.deepcopy(load_versions) or {}
        layers: dict[str, set[str]] = defaultdict(set)

        for ds_name, ds_config in catalog.items():
            ds_config = _resolve_credentials(  # noqa: redefined-loop-name
                ds_config, credentials
            )
            if cls._is_pattern(ds_name):
                # Add each factory to the dataset_patterns dict.
                dataset_patterns[ds_name] = ds_config

            else:
                # Check if 'layer' attribute is defined at the top level
                if "layer" in ds_config:
                    import warnings

                    warnings.warn(
                        "Defining the 'layer' attribute at the top level is deprecated "
                        "and will be removed in Kedro 0.19.0. Please move 'layer' inside the 'metadata' -> "
                        "'kedro-viz' attributes. See https://docs.kedro.org/en/latest/visualisation/kedro"
                        "-viz_visualisation.html#visualise-layers for more information.",
                        KedroDeprecationWarning,
                    )
                ds_layer = ds_config.pop("layer", None)
                if ds_layer is not None:
                    layers[ds_layer].add(ds_name)
                datasets[ds_name] = AbstractDataset.from_config(
                    ds_name, ds_config, load_versions.get(ds_name), save_version
                )
        dataset_layers = layers or None
        sorted_patterns = cls._sort_patterns(dataset_patterns)
        missing_keys = [
            key
            for key in load_versions.keys()
            if not (key in catalog or cls._match_pattern(sorted_patterns, key))
        ]
        if missing_keys:
            raise DatasetNotFoundError(
                f"'load_versions' keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

        return cls(
            datasets=datasets,
            layers=dataset_layers,
            dataset_patterns=sorted_patterns,
            load_versions=load_versions,
            save_version=save_version,
        )

    @staticmethod
    def _is_pattern(pattern: str):
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
        return {key: dataset_patterns[key] for key in sorted_keys}

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

    def _get_dataset(
        self, dataset_name: str, version: Version = None, suggest: bool = True
    ) -> AbstractDataset:
        matched_pattern = self._match_pattern(self._dataset_patterns, dataset_name)
        if dataset_name not in self._datasets and matched_pattern:
            # If the dataset is a patterned dataset, materialise it and add it to
            # the catalog
            config_copy = copy.deepcopy(self._dataset_patterns[matched_pattern])
            dataset_config = self._resolve_config(
                dataset_name, matched_pattern, config_copy
            )
            ds_layer = dataset_config.pop("layer", None)
            if ds_layer:
                self.layers = self.layers or {}
                self.layers.setdefault(ds_layer, set()).add(dataset_name)
            dataset = AbstractDataset.from_config(
                dataset_name,
                dataset_config,
                self._load_versions.get(dataset_name),
                self._save_version,
            )
            if self._specificity(matched_pattern) == 0:
                self._logger.warning(
                    "Config from the dataset factory pattern '%s' in the catalog will be used to "
                    "override the default MemoryDataset creation for the dataset '%s'",
                    matched_pattern,
                    dataset_name,
                )

            self.add(dataset_name, dataset)
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
            dataset = dataset._copy(_version=version)  # noqa: protected-access

        return dataset

    def __contains__(self, dataset_name):
        """Check if an item is in the catalog as a materialised dataset or pattern"""
        matched_pattern = self._match_pattern(self._dataset_patterns, dataset_name)
        if dataset_name in self._datasets or matched_pattern:
            return True
        return False

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

    def load(self, name: str, version: str = None) -> Any:
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
            >>> io = DataCatalog(datasets={'cars': cars})
            >>>
            >>> df = io.load("cars")
        """
        load_version = Version(version, None) if version else None
        dataset = self._get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from [dark_orange]%s[/dark_orange] (%s)...",
            name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        result = dataset.load()

        return result

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
            >>> io = DataCatalog(datasets={'cars': cars})
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>> io.save("cars", df)
        """
        dataset = self._get_dataset(name)

        self._logger.info(
            "Saving data to [dark_orange]%s[/dark_orange] (%s)...",
            name,
            type(dataset).__name__,
            extra={"markup": True},
        )

        dataset.save(data)

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

    def release(self, name: str):
        """Release any cached data associated with a data set

        Args:
            name: A data set to be checked.

        Raises:
            DatasetNotFoundError: When a data set with the given name
                has not yet been registered.
        """
        dataset = self._get_dataset(name)
        dataset.release()

    def add(
        self, dataset_name: str, dataset: AbstractDataset, replace: bool = False
    ) -> None:
        """Adds a new ``AbstractDataset`` object to the ``DataCatalog``.

        Args:
            dataset_name: A unique data set name which has not been
                registered yet.
            dataset: A data set object to be associated with the given data
                set name.
            replace: Specifies whether to replace an existing dataset
                with the same name is allowed.

        Raises:
            DatasetAlreadyExistsError: When a data set with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset
            >>>
            >>> io = DataCatalog(datasets={
            >>>                   'cars': CSVDataset(filepath="cars.csv")
            >>>                  })
            >>>
            >>> io.add("boats", CSVDataset(filepath="boats.csv"))
        """
        if dataset_name in self._datasets:
            if replace:
                self._logger.warning("Replacing dataset '%s'", dataset_name)
            else:
                raise DatasetAlreadyExistsError(
                    f"Dataset '{dataset_name}' has already been registered"
                )
        self._datasets[dataset_name] = dataset
        self.datasets = _FrozenDatasets(self.datasets, {dataset_name: dataset})

    def add_all(
        self, datasets: dict[str, AbstractDataset], replace: bool = False
    ) -> None:
        """Adds a group of new data sets to the ``DataCatalog``.

        Args:
            datasets: A dictionary of dataset names and dataset
                instances.
            replace: Specifies whether to replace an existing dataset
                with the same name is allowed.

        Raises:
            DatasetAlreadyExistsError: When a data set with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro_datasets.pandas import CSVDataset, ParquetDataset
            >>>
            >>> io = DataCatalog(datasets={
            >>>                   "cars": CSVDataset(filepath="cars.csv")
            >>>                  })
            >>> additional = {
            >>>     "planes": ParquetDataset("planes.parq"),
            >>>     "boats": CSVDataset(filepath="boats.csv")
            >>> }
            >>>
            >>> io.add_all(additional)
            >>>
            >>> assert io.list() == ["cars", "planes", "boats"]
        """
        for name, dataset in datasets.items():
            self.add(name, dataset, replace)

    def add_feed_dict(self, feed_dict: dict[str, Any], replace: bool = False) -> None:
        """Adds instances of ``MemoryDataset``, containing the data provided
        through feed_dict.

        Args:
            feed_dict: A feed dict with data to be added in memory.
            replace: Specifies whether to replace an existing dataset
                with the same name is allowed.

        Example:
        ::

            >>> import pandas as pd
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>>
            >>> io = DataCatalog()
            >>> io.add_feed_dict({
            >>>     'data': df
            >>> }, replace=True)
            >>>
            >>> assert io.load("data").equals(df)
        """
        for dataset_name in feed_dict:
            if isinstance(feed_dict[dataset_name], AbstractDataset):
                dataset = feed_dict[dataset_name]
            else:
                dataset = MemoryDataset(data=feed_dict[dataset_name])

            self.add(dataset_name, dataset, replace)

    def list(self, regex_search: str | None = None) -> list[str]:
        """
        List of all dataset names registered in the catalog.
        This can be filtered by providing an optional regular expression
        which will only return matching keys.

        Args:
            regex_search: An optional regular expression which can be provided
                to limit the data sets returned by a particular pattern.
        Returns:
            A list of dataset names available which match the
            `regex_search` criteria (if provided). All data set names are returned
            by default.

        Raises:
            SyntaxError: When an invalid regex filter is provided.

        Example:
        ::

            >>> io = DataCatalog()
            >>> # get data sets where the substring 'raw' is present
            >>> raw_data = io.list(regex_search='raw')
            >>> # get data sets which start with 'prm' or 'feat'
            >>> feat_eng_data = io.list(regex_search='^(prm|feat)')
            >>> # get data sets which end with 'time_series'
            >>> models = io.list(regex_search='.+time_series$')
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
        return [dset_name for dset_name in self._datasets if pattern.search(dset_name)]

    def shallow_copy(self) -> DataCatalog:
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        return DataCatalog(
            datasets=self._datasets,
            layers=self.layers,
            dataset_patterns=self._dataset_patterns,
            load_versions=self._load_versions,
            save_version=self._save_version,
        )

    def __eq__(self, other):
        return (self._datasets, self.layers, self._dataset_patterns) == (
            other._datasets,
            other.layers,
            other._dataset_patterns,
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
            dataset.confirm()  # type: ignore
        else:
            raise DatasetError(f"Dataset '{name}' does not have 'confirm' method")
