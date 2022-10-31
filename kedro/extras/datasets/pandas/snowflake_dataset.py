"""``SnowflakeTableDataSet`` to load and save data to a SQL backend."""

import copy
import re
from typing import Any, Dict, Optional

import pandas as pd
from snowflake.snowpark import Session

from kedro.io.core import AbstractDataSet, DataSetError

KNOWN_PIP_INSTALL = {
    "snowflake.snowpark": "snowflake.snowpark",
}

DRIVER_ERROR_MESSAGE = """
A module/driver is missing when connecting to Snowflake
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
            f"You can also try installing missing driver with\n"
            f"\npip install {KNOWN_PIP_INSTALL.get(missing_module)}"
        )

    return None


def _get_missing_module_error(import_error: ImportError) -> DataSetError:
    missing_module_instruction = _find_known_drivers(import_error)

    if missing_module_instruction is None:
        return DataSetError(
            f"{DRIVER_ERROR_MESSAGE}Loading failed with error:\n\n{str(import_error)}"
        )

    return DataSetError(f"{DRIVER_ERROR_MESSAGE}{missing_module_instruction}")


class SnowflakeTableDataSet(AbstractDataSet[pd.DataFrame, pd.DataFrame]):
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

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
        data_catalog.html#use-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> shuttles_table_dataset:
        >>>   type: pandas.SQLTableDataSet
        >>>   credentials: db_credentials
        >>>   table_name: shuttles
        >>>   load_args:
        >>>     schema: dwschema
        >>>   save_args:
        >>>     schema: dwschema
        >>>     if_exists: replace

    Sample database credentials entry in ``credentials.yml``:

    .. code-block:: yaml

            >>> db_creds:
            >>>     con: postgresql://scott:tiger@localhost/test

    Example using Python API:
    ::

        >>> from kedro.extras.datasets.pandas import SQLTableDataSet
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

    DEFAULT_LOAD_ARGS: Dict[str, Any] = {}
    DEFAULT_SAVE_ARGS: Dict[str, Any] = {"index": False}
    # using Any because of Sphinx but it should be
    # sqlalchemy.engine.Engine or sqlalchemy.engine.base.Engine
    sessions: Dict[str, Any] = {}

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
            raise DataSetError("'table_name' argument cannot be empty.")

        if not credentials:
            raise DataSetError("Please configure expected credentials")

        # print(self._load_args)

        # Handle default load and save arguments
        self._load_args = copy.deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = copy.deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        self._load_args["table_name"] = table_name
        self._save_args["name"] = table_name

        self._credentials = credentials["credentials"]

        # self._connection_str = credentials["con"]
        self.create_connection(self._credentials)

    @classmethod
    def create_connection(cls, credentials: dict) -> None:
        """Given a connection string, create singleton connection
        to be used across all instances of `SQLQueryDataSet` that
        need to connect to the same source.
            connection_params = {
                "account": "",∂
                "user": "",
                "password": "",
                "role": "",
                "warehouse": "",
                "database": "",
                "schema": ""
                }
        """
        if credentials["account"] in cls.sessions:
            return
        try:
            session = Session.builder.configs(credentials).create()
        except ImportError as import_error:
            raise _get_missing_module_error(import_error) from import_error
        except Exception as exception:
            raise exception

        cls.sessions[credentials["account"]] = session
        print("session")
        print(session)
        print("connection successful")

    def _describe(self) -> Dict[str, Any]:
        load_args = copy.deepcopy(self._load_args)
        save_args = copy.deepcopy(self._save_args)
        del load_args["table_name"]
        del save_args["name"]
        return dict(
            table_name=self._load_args["table_name"],
            load_args=load_args,
            save_args=save_args,
        )

    def _load(self) -> pd.DataFrame:
        pass

    def _save(self, data: pd.DataFrame) -> None:
        # pd df to snowpark df
        session = self.sessions[self._credentials["account"]]  # type: ignore
        sp_df = session.create_dataframe(data)
        table_name = [
            self._credentials.get("database"),
            self._credentials.get("schema"),
            self._load_args["table_name"],
        ]
        sp_df.write.mode("overwrite").save_as_table(table_name, table_type="")

    def _exists(self) -> bool:
        session = self.sessions[self._credentials["account"]]  # type: ignore
        schema = self._load_args.get("schema", None)
        exists = self._load_args["table_name"] in session.table_names(schema)
        return exists
