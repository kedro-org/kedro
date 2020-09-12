# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
"""``DataCatalog`` stores instances of ``AbstractDataSet`` implementations to
provide ``load`` and ``save`` capabilities from anywhere in the program. To
use a ``DataCatalog``, you need to instantiate it with a dictionary of data
sets. Then it will act as a single point of reference for your calls,
relaying load and save functions to the underlying data sets.
"""
import copy
import difflib
import logging
import re
from collections import defaultdict
from functools import partial
from typing import Any, Callable, Dict, Iterable, List, Optional, Set, Type, Union
from warnings import warn

from kedro.io.core import (
    AbstractDataSet,
    AbstractVersionedDataSet,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    Version,
    generate_timestamp,
)
from kedro.io.memory_data_set import MemoryDataSet
from kedro.io.transformers import AbstractTransformer
from kedro.versioning import Journal

CATALOG_KEY = "catalog"
CREDENTIALS_KEY = "credentials"


def _get_credentials(
    credentials_name: str, credentials: Dict[str, Any]
) -> Dict[str, Any]:
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
    config: Dict[str, Any], credentials: Dict[str, Any]
) -> Dict[str, Any]:
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


def _sub_nonword_chars(data_set_name: str) -> str:
    """Replace non-word characters in data set names since Kedro 0.16.2.

    Args:
        data_set_name: The data set name registered in the data catalog.

    Returns:
        The name used in `DataCatalog.datasets`.
    """
    return re.sub(r"\W+", "__", data_set_name)


class _FrozenDatasets:
    """Helper class to access underlying loaded datasets"""

    def __init__(self, datasets):
        # Non-word characters in dataset names are replaced with `__`
        # for easy access to transcoded/prefixed datasets.
        datasets = {_sub_nonword_chars(key): value for key, value in datasets.items()}
        self.__dict__.update(**datasets)

    # Don't allow users to add/change attributes on the fly
    def __setattr__(self, key, value):
        msg = "Operation not allowed! "
        if key in self.__dict__.keys():
            msg += "Please change datasets through configuration."
        else:
            msg += "Please use DataCatalog.add() instead."
        raise AttributeError(msg)


class DataCatalog:
    """``DataCatalog`` stores instances of ``AbstractDataSet`` implementations
    to provide ``load`` and ``save`` capabilities from anywhere in the
    program. To use a ``DataCatalog``, you need to instantiate it with
    a dictionary of data sets. Then it will act as a single point of reference
    for your calls, relaying load and save functions
    to the underlying data sets.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        data_sets: Dict[str, AbstractDataSet] = None,
        feed_dict: Dict[str, Any] = None,
        transformers: Dict[str, List[AbstractTransformer]] = None,
        default_transformers: List[AbstractTransformer] = None,
        journal: Journal = None,
        layers: Dict[str, Set[str]] = None,
    ) -> None:
        """``DataCatalog`` stores instances of ``AbstractDataSet``
        implementations to provide ``load`` and ``save`` capabilities from
        anywhere in the program. To use a ``DataCatalog``, you need to
        instantiate it with a dictionary of data sets. Then it will act as a
        single point of reference for your calls, relaying load and save
        functions to the underlying data sets.

        Args:
            data_sets: A dictionary of data set names and data set instances.
            feed_dict: A feed dict with data to be added in memory.
            transformers: A dictionary of lists of transformers to be applied
                to the data sets.
            default_transformers: A list of transformers to be applied to any
                new data sets.
            journal: Instance of Journal.
            layers: A dictionary of data set layers. It maps a layer name
                to a set of data set names, according to the
                data engineering convention. For more details, see
                https://kedro.readthedocs.io/en/stable/11_faq/01_faq.html#what-is-data-engineering-convention
        Raises:
            DataSetNotFoundError: When transformers are passed for a non
                existent data set.

        Example:
        ::

            >>> from kedro.extras.datasets.pandas import CSVDataSet
            >>>
            >>> cars = CSVDataSet(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
        """
        self._data_sets = dict(data_sets or {})
        self.datasets = _FrozenDatasets(self._data_sets)
        self.layers = layers

        self._transformers = {k: list(v) for k, v in (transformers or {}).items()}
        self._default_transformers = list(default_transformers or [])
        self._check_and_normalize_transformers()
        self._journal = journal
        # import the feed dict
        if feed_dict:
            self.add_feed_dict(feed_dict)

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    def _check_and_normalize_transformers(self):
        data_sets = self._data_sets.keys()
        transformers = self._transformers.keys()
        excess_transformers = transformers - data_sets
        missing_transformers = data_sets - transformers

        if excess_transformers:
            raise DataSetNotFoundError(
                "Unexpected transformers for missing data_sets {}".format(
                    ", ".join(excess_transformers)
                )
            )

        for data_set_name in missing_transformers:
            self._transformers[data_set_name] = list(self._default_transformers)

    # pylint: disable=too-many-arguments
    @classmethod
    def from_config(
        cls: Type,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]] = None,
        load_versions: Dict[str, str] = None,
        save_version: str = None,
        journal: Journal = None,
    ) -> "DataCatalog":
        """Create a ``DataCatalog`` instance from configuration. This is a
        factory method used to provide developers with a way to instantiate
        ``DataCatalog`` with configuration parsed from configuration files.

        Args:
            catalog: A dictionary whose keys are the data set names and
                the values are dictionaries with the constructor arguments
                for classes implementing ``AbstractDataSet``. The data set
                class to be loaded is specified with the key ``type`` and their
                fully qualified class name. All ``kedro.io`` data set can be
                specified by their class name only, i.e. their module name
                can be omitted.
            credentials: A dictionary containing credentials for different
                data sets. Use the ``credentials`` key in a ``AbstractDataSet``
                to refer to the appropriate credentials as shown in the example
                below.
            load_versions: A mapping between dataset names and versions
                to load. Has no effect on data sets without enabled versioning.
            save_version: Version string to be used for ``save`` operations
                by all data sets with enabled versioning. It must: a) be a
                case-insensitive string that conforms with operating system
                filename limitations, b) always return the latest version when
                sorted in lexicographical order.
            journal: Instance of Journal.

        Returns:
            An instantiated ``DataCatalog`` containing all specified
            data sets, created and ready to use.

        Raises:
            DataSetError: When the method fails to create any of the data
                sets from their config.

        Example:
        ::

            >>> config = {
            >>>     "cars": {
            >>>         "type": "pandas.CSVDataSet",
            >>>         "filepath": "cars.csv",
            >>>         "save_args": {
            >>>             "index": False
            >>>         }
            >>>     },
            >>>     "boats": {
            >>>         "type": "pandas.CSVDataSet",
            >>>         "filepath": "s3://aws-bucket-name/boats.csv",
            >>>         "credentials": "boats_credentials"
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
        data_sets = {}
        catalog = copy.deepcopy(catalog) or {}
        credentials = copy.deepcopy(credentials) or {}
        run_id = journal.run_id if journal else None
        save_version = save_version or run_id or generate_timestamp()
        load_versions = copy.deepcopy(load_versions) or {}

        missing_keys = load_versions.keys() - catalog.keys()
        if missing_keys:
            warn(
                f"`load_versions` keys [{', '.join(sorted(missing_keys))}] "
                f"are not found in the catalog."
            )

        layers = defaultdict(set)  # type: Dict[str, Set[str]]
        for ds_name, ds_config in catalog.items():
            ds_layer = ds_config.pop("layer", None)
            if ds_layer is not None:
                layers[ds_layer].add(ds_name)

            ds_config = _resolve_credentials(ds_config, credentials)
            data_sets[ds_name] = AbstractDataSet.from_config(
                ds_name, ds_config, load_versions.get(ds_name), save_version
            )

        dataset_layers = layers or None
        return cls(data_sets=data_sets, journal=journal, layers=dataset_layers)

    def _get_dataset(
        self, data_set_name: str, version: Version = None
    ) -> AbstractDataSet:
        if data_set_name not in self._data_sets:
            error_msg = f"DataSet '{data_set_name}' not found in the catalog"

            matches = difflib.get_close_matches(data_set_name, self._data_sets.keys())
            if matches:
                suggestions = ", ".join(matches)  # type: ignore
                error_msg += f" - did you mean one of these instead: {suggestions}"

            raise DataSetNotFoundError(error_msg)

        data_set = self._data_sets[data_set_name]
        if version and isinstance(data_set, AbstractVersionedDataSet):
            # we only want to return a similar-looking dataset,
            # not modify the one stored in the current catalog
            data_set = data_set._copy(  # pylint: disable=protected-access
                _version=version
            )

        return data_set

    def _get_transformed_dataset_function(
        self, data_set_name: str, operation: str, data_set: AbstractDataSet
    ) -> Callable:
        func = getattr(data_set, operation)
        for transformer in reversed(self._transformers[data_set_name]):
            func = partial(getattr(transformer, operation), data_set_name, func)
        return func

    def load(self, name: str, version: str = None) -> Any:
        """Loads a registered data set.

        Args:
            name: A data set to be loaded.
            version: Optional argument for concrete data version to be loaded.
                Works only with versioned datasets.

        Returns:
            The loaded data as configured.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.

        Example:
        ::

            >>> from kedro.io import DataCatalog
            >>> from kedro.extras.datasets.pandas import CSVDataSet
            >>>
            >>> cars = CSVDataSet(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
            >>>
            >>> df = io.load("cars")
        """
        load_version = Version(version, None) if version else None
        dataset = self._get_dataset(name, version=load_version)

        self._logger.info(
            "Loading data from `%s` (%s)...", name, type(dataset).__name__
        )

        func = self._get_transformed_dataset_function(name, "load", dataset)
        result = func()

        version = (
            dataset.resolve_load_version()
            if isinstance(dataset, AbstractVersionedDataSet)
            else None
        )

        # Log only if versioning is enabled for the data set
        if self._journal and version:
            self._journal.log_catalog(name, "load", version)
        return result

    def save(self, name: str, data: Any) -> None:
        """Save data to a registered data set.

        Args:
            name: A data set to be saved to.
            data: A data object to be saved as configured in the registered
                data set.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.

        Example:
        ::

            >>> import pandas as pd
            >>>
            >>> from kedro.extras.datasets.pandas import CSVDataSet
            >>>
            >>> cars = CSVDataSet(filepath="cars.csv",
            >>>                   load_args=None,
            >>>                   save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>> io.save("cars", df)
        """
        dataset = self._get_dataset(name)

        self._logger.info("Saving data to `%s` (%s)...", name, type(dataset).__name__)

        func = self._get_transformed_dataset_function(name, "save", dataset)
        func(data)

        version = (
            dataset.resolve_save_version()
            if isinstance(dataset, AbstractVersionedDataSet)
            else None
        )

        # Log only if versioning is enabled for the data set
        if self._journal and version:
            self._journal.log_catalog(name, "save", version)

    def exists(self, name: str) -> bool:
        """Checks whether registered data set exists by calling its `exists()`
        method. Raises a warning and returns False if `exists()` is not
        implemented.

        Args:
            name: A data set to be checked.

        Returns:
            Whether the data set output exists.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.
        """
        dataset = self._get_dataset(name)
        return dataset.exists()

    def release(self, name: str):
        """Release any cached data associated with a data set

        Args:
            name: A data set to be checked.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.
        """
        dataset = self._get_dataset(name)
        dataset.release()

    def add(
        self, data_set_name: str, data_set: AbstractDataSet, replace: bool = False
    ) -> None:
        """Adds a new ``AbstractDataSet`` object to the ``DataCatalog``.

        Args:
            data_set_name: A unique data set name which has not been
                registered yet.
            data_set: A data set object to be associated with the given data
                set name.
            replace: Specifies whether to replace an existing ``DataSet``
                with the same name is allowed.

        Raises:
            DataSetAlreadyExistsError: When a data set with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro.extras.datasets.pandas import CSVDataSet
            >>>
            >>> io = DataCatalog(data_sets={
            >>>                   'cars': CSVDataSet(filepath="cars.csv")
            >>>                  })
            >>>
            >>> io.add("boats", CSVDataSet(filepath="boats.csv"))
        """
        if data_set_name in self._data_sets:
            if replace:
                self._logger.warning("Replacing DataSet '%s'", data_set_name)
            else:
                raise DataSetAlreadyExistsError(
                    "DataSet '{}' has already been registered".format(data_set_name)
                )
        self._data_sets[data_set_name] = data_set
        self._transformers[data_set_name] = list(self._default_transformers)
        self.datasets = _FrozenDatasets(self._data_sets)

    def add_all(
        self, data_sets: Dict[str, AbstractDataSet], replace: bool = False
    ) -> None:
        """Adds a group of new data sets to the ``DataCatalog``.

        Args:
            data_sets: A dictionary of ``DataSet`` names and data set
                instances.
            replace: Specifies whether to replace an existing ``DataSet``
                with the same name is allowed.

        Raises:
            DataSetAlreadyExistsError: When a data set with the same name
                has already been registered.

        Example:
        ::

            >>> from kedro.extras.datasets.pandas import CSVDataSet, ParquetDataSet
            >>>
            >>> io = DataCatalog(data_sets={
            >>>                   "cars": CSVDataSet(filepath="cars.csv")
            >>>                  })
            >>> additional = {
            >>>     "planes": ParquetDataSet("planes.parq"),
            >>>     "boats": CSVDataSet(filepath="boats.csv")
            >>> }
            >>>
            >>> io.add_all(additional)
            >>>
            >>> assert io.list() == ["cars", "planes", "boats"]
        """
        for name, data_set in data_sets.items():
            self.add(name, data_set, replace)

    def add_feed_dict(self, feed_dict: Dict[str, Any], replace: bool = False) -> None:
        """Adds instances of ``MemoryDataSet``, containing the data provided
        through feed_dict.

        Args:
            feed_dict: A feed dict with data to be added in memory.
            replace: Specifies whether to replace an existing ``DataSet``
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
        for data_set_name in feed_dict:
            if isinstance(feed_dict[data_set_name], AbstractDataSet):
                data_set = feed_dict[data_set_name]
            else:
                data_set = MemoryDataSet(data=feed_dict[data_set_name])

            self.add(data_set_name, data_set, replace)

    def add_transformer(
        self,
        transformer: AbstractTransformer,
        data_set_names: Union[str, Iterable[str]] = None,
    ):
        """Add a ``DataSet`` Transformer to the``DataCatalog``.
        Transformers can modify the way Data Sets are loaded and saved.

        Args:
            transformer: The transformer instance to add.
            data_set_names: The Data Sets to add the transformer to.
                Or None to add the transformer to all Data Sets.
        Raises:
            DataSetNotFoundError: When a transformer is being added to a non
                existent data set.
            TypeError: When transformer isn't an instance of ``AbstractTransformer``
        """
        if not isinstance(transformer, AbstractTransformer):
            raise TypeError(
                "Object of type {} is not an instance of AbstractTransformer".format(
                    type(transformer)
                )
            )
        if data_set_names is None:
            self._default_transformers.append(transformer)
            data_set_names = self._transformers.keys()
        elif isinstance(data_set_names, str):
            data_set_names = [data_set_names]
        for data_set_name in data_set_names:
            if data_set_name not in self._data_sets:
                raise DataSetNotFoundError(
                    "No data set called {}".format(data_set_name)
                )
            self._transformers[data_set_name].append(transformer)

    def list(self, regex_search: Optional[str] = None) -> List[str]:
        """
        List of all ``DataSet`` names registered in the catalog.
        This can be filtered by providing an optional regular expression
        which will only return matching keys.

        Args:
            regex_search: An optional regular expression which can be provided
                to limit the data sets returned by a particular pattern.
        Returns:
            A list of ``DataSet`` names available which match the
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
            return list(self._data_sets.keys())

        if not regex_search.strip():
            logging.warning("The empty string will not match any data sets")
            return []

        try:
            pattern = re.compile(regex_search, flags=re.IGNORECASE)
        except re.error as exc:
            raise SyntaxError(
                f"Invalid regular expression provided: `{regex_search}`"
            ) from exc
        return [dset_name for dset_name in self._data_sets if pattern.search(dset_name)]

    def shallow_copy(self) -> "DataCatalog":
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        return DataCatalog(
            data_sets=self._data_sets,
            transformers=self._transformers,
            default_transformers=self._default_transformers,
            journal=self._journal,
        )

    def __eq__(self, other):
        return (
            self._data_sets,
            self._transformers,
            self._default_transformers,
            self._journal,
        ) == (
            other._data_sets,
            other._transformers,
            other._default_transformers,
            other._journal,
        )

    def confirm(self, name: str) -> None:
        """Confirm a dataset by its name.

        Args:
            name: Name of the dataset.
        Raises:
            DataSetError: When the dataset does not have `confirm` method.

        """
        self._logger.info("Confirming DataSet '%s'", name)
        data_set = self._get_dataset(name)

        if hasattr(data_set, "confirm"):
            data_set.confirm()  # type: ignore
        else:
            raise DataSetError(
                "DataSet '{}' does not have 'confirm' method".format(name)
            )
