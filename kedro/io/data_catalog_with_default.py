# Copyright 2020 QuantumBlack Visual Analytics Limited
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
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""A ``DataCatalog`` with a default ``DataSet`` implementation for any data set
which is not registered in the catalog.
"""
from typing import Any, Callable, Dict, Optional

from kedro.io.core import AbstractDataSet
from kedro.io.data_catalog import DataCatalog
from kedro.versioning import Journal


class DataCatalogWithDefault(DataCatalog):
    """A ``DataCatalog`` with a default ``DataSet`` implementation for any
    data set which is not registered in the catalog.
    """

    def __init__(
        self,
        data_sets: Dict[str, AbstractDataSet] = None,
        default: Callable[[str], AbstractDataSet] = None,
        remember: bool = False,
    ):
        """A ``DataCatalog`` with a default ``DataSet`` implementation for any
        data set which is not registered in the catalog.

        Args:
            data_sets: A dictionary of data set names and data set instances.
            default: A callable which accepts a single argument of type string,
                the key of the data set, and returns an ``AbstractDataSet``.
                ``load`` and ``save`` calls on data sets which are not
                registered to the catalog will be delegated to this
                ``AbstractDataSet``.
            remember: If True, then store in the catalog any
                ``AbstractDataSet``s provided by the ``default`` callable
                argument. Useful when one want to transition from a
                ``DataCatalogWithDefault`` to a ``DataCatalog``: just call
                ``DataCatalogWithDefault.to_yaml``, after all required data
                sets have been saved/loaded, and use the generated YAML file
                with a new ``DataCatalog``.
        Raises:
            TypeError: If default is not a callable.

        Example:
        ::

            >>> from kedro.extras.datasets.pandas import CSVDataSet
            >>>
            >>> def default_data_set(name):
            >>>     return CSVDataSet(filepath='data/01_raw/' + name)
            >>>
            >>> io = DataCatalog(data_sets={},
            >>>                  default=default_data_set)
            >>>
            >>> # load the file in data/raw/cars.csv
            >>> df = io.load("cars.csv")
        """
        super().__init__(data_sets)

        if not callable(default):
            raise TypeError(
                "Default must be a callable with a single input "
                "string argument: the key of the requested data "
                "set."
            )
        self._default = default
        self._remember = remember

    def load(self, name: str, version: str = None) -> Any:
        """Loads a registered data set

        Args:
            name: A data set to be loaded.
            version: Optional version to be loaded.


        Returns:
            The loaded data as configured.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.

        """
        data_set = self._data_sets.get(name, self._default(name))

        if self._remember and name not in self._data_sets:
            self._data_sets[name] = data_set

        return data_set.load()

    def save(self, name: str, data: Any):
        """Save data to a registered data set.

        Args:
            name: A data set to be saved to.
            data: A data object to be saved as configured in the registered
                data set.

        Raises:
            DataSetNotFoundError: When a data set with the given name
                has not yet been registered.

        """
        data_set = self._data_sets.get(name, self._default(name))

        if self._remember and name not in self._data_sets:
            self._data_sets[name] = data_set

        data_set.save(data)

    # pylint: disable=too-many-arguments
    @classmethod
    def from_config(
        cls,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]] = None,
        load_versions: Dict[str, str] = None,
        save_version: str = None,
        journal: Journal = None,
    ):
        """To create a ``DataCatalogWithDefault`` from configuration, please
        use:
        ::

            >>>  DataCatalogWithDefault.from_data_catalog(
            >>>      DataCatalog.from_config(catalog, credentials))

        Args:
            catalog: See ``DataCatalog.from_config``
            credentials: See ``DataCatalog.from_config``
            load_versions: See ``DataCatalog.from_config``
            save_version: See ``DataCatalog.from_config``
            journal: See ``DataCatalog.from_config``

        Raises:
            ValueError: If you try to instantiate a ``DataCatalogWithDefault``
            directly with this method.

        """
        raise ValueError(
            "Cannot instantiate a `DataCatalogWithDefault` "
            "directly from configuration files. Please use"
            "``DataCatalogWithDefault.from_data_catalog("
            "DataCatalog.from_config(catalog, "
            "credentials, journal))"
        )

    @classmethod
    def from_data_catalog(
        cls, data_catalog: DataCatalog, default: Callable[[str], AbstractDataSet]
    ) -> "DataCatalogWithDefault":
        """Convenience factory method to create a ``DataCatalogWithDefault``
        from a ``DataCatalog``

        A ``DataCatalog`` with a default ``DataSet`` implementation for any
        data set which is not registered in the catalog.

        Args:
            data_catalog: The ``DataCatalog`` to convert to a
                ``DataCatalogWithDefault``.
            default: A callable which accepts a single argument of type string,
                the key of the data set, and returns an ``AbstractDataSet``.
                ``load`` and ``save`` calls on data sets which are not
                registered to the catalog will be delegated to this
                ``AbstractDataSet``.

        Returns:
            A new ``DataCatalogWithDefault`` which contains all the
            ``AbstractDataSets`` from the provided data-catalog.

        """
        # pylint: disable=protected-access
        return cls({**data_catalog._data_sets}, default)

    def shallow_copy(self) -> "DataCatalogWithDefault":  # pragma: no cover
        """Returns a shallow copy of the current object.
        Returns:
            Copy of the current object.
        """
        return DataCatalogWithDefault({**self._data_sets}, self._default)
