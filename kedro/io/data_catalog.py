# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
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
import logging
from typing import Any, Dict, List, Optional, Type

from kedro.io.core import (
    AbstractDataSet,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    generate_current_version,
)
from kedro.io.memory_data_set import MemoryDataSet

CATALOG_KEY = "catalog"
CREDENTIALS_KEY = "credentials"


def _get_credentials(credentials_name: str, credentials: Dict) -> Dict:
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
    except KeyError:
        raise KeyError(
            "Unable to find credentials '{}': check your data "
            "catalog and credentials configuration. See "
            "https://kedro.readthedocs.io/en/latest/kedro.io.DataCatalog.html "
            "for an example.".format(credentials_name)
        )


class DataCatalog:
    """``DataCatalog`` stores instances of ``AbstractDataSet`` implementations
    to provide ``load`` and ``save`` capabilities from anywhere in the
    program. To use a ``DataCatalog``, you need to instantiate it with
    a dictionary of data sets. Then it will act as a single point of reference
    for your calls, relaying load and save functions
    to the underlying data sets.
    """

    def __init__(
        self,
        data_sets: Dict[str, AbstractDataSet] = None,
        feed_dict: Dict[str, Any] = None,
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

        Example:
        ::

            >>> from kedro.io import CSVLocalDataSet
            >>>
            >>> cars = CSVLocalDataSet(filepath="cars.csv",
            >>>                        load_args=None,
            >>>                        save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
        """
        self._data_sets = data_sets or {}
        if feed_dict:
            self.add_feed_dict(feed_dict)

    @property
    def _logger(self):
        return logging.getLogger(__name__)

    @classmethod
    def from_config(
        cls: Type,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]] = None,
        load_versions: Dict[str, str] = None,
        save_version: str = None,
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
            >>>         "type": "CSVLocalDataSet",
            >>>         "filepath": "cars.csv",
            >>>         "save_args": {
            >>>             "index": False
            >>>         }
            >>>     },
            >>>     "boats": {
            >>>         "type": "CSVS3DataSet",
            >>>         "filepath": "boats.csv",
            >>>         "bucket_name": "mck-147789798-bucket",
            >>>         "credentials": "boats_credentials"
            >>>         "save_args": {
            >>>             "index": False
            >>>         }
            >>>     }
            >>> }
            >>>
            >>> credentials = {
            >>>     "boats_credentials": {
            >>>         "aws_access_key_id": "<your key id>",
            >>>         "aws_secret_access_key": "<your secret>"
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
        save_version = save_version or generate_current_version()
        load_versions = copy.deepcopy(load_versions) or {}

        for ds_name, ds_config in catalog.items():
            if "type" not in ds_config:
                raise DataSetError(
                    "`type` is missing from DataSet '{}' "
                    "catalog configuration".format(ds_name)
                )
            if CREDENTIALS_KEY in ds_config:
                ds_config[CREDENTIALS_KEY] = _get_credentials(
                    ds_config.pop(CREDENTIALS_KEY), credentials  # credentials name
                )
            data_sets[ds_name] = AbstractDataSet.from_config(
                ds_name, ds_config, load_versions.get(ds_name), save_version
            )
        return cls(data_sets=data_sets)

    def load(self, name: str) -> Any:
        """Loads a registered data set.

        Args:
            name: A data set to be loaded.

        Returns:
            The loaded data as configured.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.

        Example:
        ::

            >>> from kedro.io import CSVLocalDataSet, DataCatalog
            >>>
            >>> cars = CSVLocalDataSet(filepath="cars.csv",
            >>>                        load_args=None,
            >>>                        save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
            >>>
            >>> df = io.load("cars")
        """
        if name in self._data_sets:
            self._logger.info(
                "Loading data from `%s` (%s)...",
                name,
                type(self._data_sets[name]).__name__,
            )
            return self._data_sets[name].load()

        raise DataSetNotFoundError("DataSet '{}' not found in the catalog".format(name))

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
            >>> from kedro.io import CSVLocalDataSet
            >>>
            >>> cars = CSVLocalDataSet(filepath="cars.csv",
            >>>                        load_args=None,
            >>>                        save_args={"index": False})
            >>> io = DataCatalog(data_sets={'cars': cars})
            >>>
            >>> df = pd.DataFrame({'col1': [1, 2],
            >>>                    'col2': [4, 5],
            >>>                    'col3': [5, 6]})
            >>> io.save("cars", df)
        """
        if name in self._data_sets:
            self._logger.info(
                "Saving data to `%s` (%s)...",
                name,
                type(self._data_sets[name]).__name__,
            )
            self._data_sets[name].save(data)
        else:
            raise DataSetNotFoundError(
                "DataSet '{}' not found in the catalog".format(name)
            )

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
        if name in self._data_sets:
            data_set = self._data_sets[name]
            if hasattr(data_set, "exists"):
                return data_set.exists()

            self._logger.warning(
                "`exists()` not implemented for `%s`. "
                "Assuming output does not exist.",
                name,
            )
            return False

        raise DataSetNotFoundError("DataSet '{}' not found in the catalog".format(name))

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

            >>> from kedro.io import CSVLocalDataSet
            >>>
            >>> io = DataCatalog(data_sets={
            >>>                   'cars': CSVLocalDataSet(filepath="cars.csv")
            >>>                  })
            >>>
            >>> io.add("boats", CSVLocalDataSet(filepath="boats.csv"))
        """
        if data_set_name in self._data_sets:
            if replace:
                self._logger.warning("Replacing DataSet '%s'", data_set_name)
            else:
                raise DataSetAlreadyExistsError(
                    "DataSet '{}' has already been registered".format(data_set_name)
                )
        self._data_sets[data_set_name] = data_set

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

            >>> from kedro.io import CSVLocalDataSet, ParquetLocalDataSet
            >>>
            >>> io = DataCatalog(data_sets={
            >>>                   "cars": CSVLocalDataSet(filepath="cars.csv")
            >>>                  })
            >>> additional = {
            >>>     "planes": ParquetLocalDataSet("planes.parq"),
            >>>     "boats": CSVLocalDataSet(filepath="boats.csv")
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

    def list(self) -> List[str]:
        """List of ``DataSet`` names registered in the catalog.

        Returns:
            A List of ``DataSet`` names, corresponding to the entries that are
            registered in the current catalog object.

        """
        return list(self._data_sets.keys())

    def shallow_copy(self) -> "DataCatalog":
        """Returns a shallow copy of the current object.

        Returns:
            Copy of the current object.
        """
        return DataCatalog({**self._data_sets})

    def __eq__(self, other):
        return self._data_sets == other._data_sets  # pylint: disable=protected-access
