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
"""``SQLDataSet`` to load and save data to a SQL backend."""

import copy
import re
from typing import Any, Dict, Optional

import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.exc import NoSuchModuleError

from kedro.io.core import AbstractDataSet, DataSetError

__all__ = ["SQLTableDataSet", "SQLQueryDataSet"]

KNOWN_PIP_INSTALL = {
    "psycopg2": "psycopg2",
    "mysqldb": "mysqlclient",
    "cx_Oracle": "cx_Oracle",
}

DRIVER_ERROR_MESSAGE = """
A module/driver is missing when connecting to your SQL server. SQLDataSet
 supports SQLAlchemy drivers. Please refer to
 https://docs.sqlalchemy.org/en/13/core/engines.html#supported-databases
 for more information.
\n\n
"""


def _find_known_drivers(module_import_error: ImportError) -> Optional[str]:
    """Looks up known keywords in a ``ModuleNotFoundError`` so that it can
    provide better guideline for the user.

    Args:
        module_import_error: Error raised while connecting to a SQL server.

    Returns:
        Instructions for installing missing driver. An empty string is
        returned in case error is related to an unknown driver.

    """

    # module errors contain string "No module name 'module_name'"
    # we are trying to extract module_name surrounded by quotes here
    res = re.findall(r"'(.*?)'", str(module_import_error.args[0]).lower())

    # in case module import error does not match our expected pattern
    # we have no recommendation
    if not res:
        return None

    missing_module = res[0]

    if KNOWN_PIP_INSTALL.get(missing_module):
        return (
            "You can also try installing missing driver with\n"
            "\npip install {}".format(KNOWN_PIP_INSTALL.get(missing_module))
        )

    return None


def _get_missing_module_error(import_error: ImportError) -> DataSetError:
    missing_module_instruction = _find_known_drivers(import_error)

    if missing_module_instruction is None:
        return DataSetError(
            "{}Loading failed with error:\n\n{}".format(
                DRIVER_ERROR_MESSAGE, str(import_error)
            )
        )

    return DataSetError("{}{}".format(DRIVER_ERROR_MESSAGE, missing_module_instruction))


def _get_sql_alchemy_missing_error() -> DataSetError:
    return DataSetError(
        "The SQL dialect in your connection is not supported by "
        "SQLAlchemy. Please refer to "
        "https://docs.sqlalchemy.org/en/13/core/engines.html#supported-databases "
        "for more information."
    )


class SQLTableDataSet(AbstractDataSet):
    """``SQLTableDataSet`` loads data from a SQL table and saves a pandas
    dataframe to a table. It uses ``pandas.DataFrame`` internally,
    so it supports all allowed pandas options on ``read_sql_table`` and
    ``to_sql`` methods. Since Pandas uses SQLAlchemy behind the scenes, when
    instantiating ``SQLTableDataSet`` one needs to pass a compatible connection
    string either in ``credentials`` (see the example code snippet below) or in
    ``load_args`` and ``save_args``. Connection string formats supported by
    SQLAlchemy can be found here:
    https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls

    ``SQLTableDataSet`` modifies the save parameters and stores
    the data with no index. This is designed to make load and save methods
    symmetric.


    Example:
    ::

        >>> from kedro.io import SQLTableDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({"col1": [1, 2], "col2": [4, 5],
        >>>                      "col3": [5, 6]})
        >>> table_name = "table_a"
        >>> credentials = {
        >>>     "con": "postgresql://scott:tiger@localhost/test"
        >>> }
        >>> data_set = SQLTableDataSet(table_name=table_name,
        >>>                            credentials=credentials)
        >>>
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.equals(reloaded)

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {"index": False}  # type: Dict[str, Any]

    def _describe(self) -> Dict[str, Any]:
        load_args = self._load_args.copy()
        save_args = self._save_args.copy()
        del load_args["table_name"]
        del load_args["con"]
        del save_args["name"]
        del save_args["con"]
        return dict(
            table_name=self._load_args["table_name"],
            load_args=load_args,
            save_args=save_args,
        )

    def __init__(
        self,
        table_name: str,
        credentials: Dict[str, Any],
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new ``SQLTableDataSet``.

        Args:
            table_name: The table name to load or save data to. It
                overwrites name in ``save_args`` and ``table_name``
                parameters in ``load_args``.
            credentials: A dictionary with a ``SQLAlchemy`` connection string.
                Users are supposed to provide the connection string 'con'
                through credentials. It overwrites `con` parameter in
                ``load_args`` and ``save_args`` in case it is provided. To find
                all supported connection string formats, see here:
                https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
            load_args: Provided to underlying pandas ``read_sql_table``
                function along with the connection string.
                To find all supported arguments, see here:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_sql_table.html
                To find all supported connection string formats, see here:
                https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
            save_args: Provided to underlying pandas ``to_sql`` function along
                with the connection string.
                To find all supported arguments, see here:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.DataFrame.to_sql.html
                To find all supported connection string formats, see here:
                https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
                It has ``index=False`` in the default parameters.

        Raises:
            DataSetError: When either ``table_name`` or ``con`` is empty.

        """

        if not table_name:
            raise DataSetError("`table_name` argument cannot be empty.")

        if not (credentials and "con" in credentials and credentials["con"]):
            raise DataSetError(
                "`con` argument cannot be empty. Please "
                "provide a SQLAlchemy connection string."
            )

        # Handle default load and save arguments
        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = copy.deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        self._load_args["table_name"] = table_name
        self._save_args["name"] = table_name

        self._load_args["con"] = self._save_args["con"] = credentials["con"]

    def _load(self) -> pd.DataFrame:
        try:
            return pd.read_sql_table(**self._load_args)
        except ImportError as import_error:
            raise _get_missing_module_error(import_error)
        except NoSuchModuleError:
            raise _get_sql_alchemy_missing_error()

    def _save(self, data: pd.DataFrame) -> None:
        try:
            data.to_sql(**self._save_args)
        except ImportError as import_error:
            raise _get_missing_module_error(import_error)
        except NoSuchModuleError:
            raise _get_sql_alchemy_missing_error()

    def _exists(self) -> bool:
        eng = create_engine(self._load_args["con"])
        schema = self._load_args.get("schema", None)
        exists = self._load_args["table_name"] in eng.table_names(schema)
        eng.dispose()
        return exists


class SQLQueryDataSet(AbstractDataSet):
    """``SQLQueryDataSet`` loads data from a provided SQL query. It
    uses ``pandas.DataFrame`` internally, so it supports all allowed
    pandas options on ``read_sql_query``. Since Pandas uses SQLAlchemy behind
    the scenes, when instantiating ``SQLQueryDataSet`` one needs to pass
    a compatible connection string either in ``credentials`` (see the example
    code snippet below) or in ``load_args``. Connection string formats supported
    by SQLAlchemy can be found here:
    https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls

    It does not support save method so it is a read only data set.
    To save data to a SQL server use ``SQLTableDataSet``.


    Example:
    ::

        >>> from kedro.io import SQLQueryDataSet
        >>> import pandas as pd
        >>>
        >>> data = pd.DataFrame({"col1": [1, 2], "col2": [4, 5],
        >>>                      "col3": [5, 6]})
        >>> sql = "SELECT * FROM table_a"
        >>> credentials = {
        >>>     "con": "postgresql://scott:tiger@localhost/test"
        >>> }
        >>> data_set = SQLQueryDataSet(sql=sql,
        >>>                            credentials=credentials)
        >>>
        >>> sql_data = data_set.load()
        >>>

    """

    def _describe(self) -> Dict[str, Any]:
        load_args = self._load_args.copy()
        del load_args["sql"]
        del load_args["con"]
        return dict(sql=self._load_args["sql"], load_args=load_args)

    def __init__(
        self, sql: str, credentials: Dict[str, Any], load_args: Dict[str, Any] = None
    ) -> None:
        """Creates a new ``SQLQueryDataSet``.

        Args:
            sql: The sql query statement.
            credentials: A dictionary with a ``SQLAlchemy`` connection string.
                Users are supposed to provide the connection string 'con'
                through credentials. It overwrites `con` parameter in
                ``load_args`` and ``save_args`` in case it is provided. To find
                all supported connection string formats, see here:
                https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls
            load_args: Provided to underlying pandas ``read_sql_query``
                function along with the connection string.
                To find all supported arguments, see here:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_sql_query.html
                To find all supported connection string formats, see here:
                https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls

        Raises:
            DataSetError: When either ``sql`` or ``con`` parameters is emtpy.

        """

        if not sql:
            raise DataSetError(
                "`sql` argument cannot be empty. Please provide a sql query"
            )

        if not (credentials and "con" in credentials and credentials["con"]):
            raise DataSetError(
                "`con` argument cannot be empty. Please "
                "provide a SQLAlchemy connection string."
            )

        default_load_args = {}  # type: Dict[str, Any]

        self._load_args = (
            {**default_load_args, **load_args}
            if load_args is not None
            else default_load_args
        )

        self._load_args["sql"] = sql

        self._load_args["con"] = credentials["con"]

    def _load(self) -> pd.DataFrame:
        try:
            return pd.read_sql_query(**self._load_args)
        except ImportError as import_error:
            raise _get_missing_module_error(import_error)
        except NoSuchModuleError:
            raise _get_sql_alchemy_missing_error()

    def _save(self, data: pd.DataFrame) -> None:
        raise DataSetError("`save` is not supported on SQLQueryDataSet")
