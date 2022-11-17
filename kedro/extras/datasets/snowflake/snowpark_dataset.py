"""``AbstractDataSet`` implementation to access Snowflake using Snowpark dataframes
"""
from copy import deepcopy
from re import findall
from typing import Any, Dict, Optional, Union

import pandas as pd
import snowflake.snowpark as sp

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
    res = findall(r"'(.*?)'", str(module_import_error.args[0]).lower())

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


# TODO: Update docstring after interface finalised
# TODO: Add to docs example of using API to add dataset
class SnowParkDataSet(
    AbstractDataSet[pd.DataFrame, pd.DataFrame]
):  # pylint: disable=too-many-instance-attributes
    """``SnowParkDataSet`` loads and saves Snowpark dataframes.

    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
        data_catalog.html#use-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> weather:
        >>>   type: snowflake.SnowParkDataSet
        >>>   table_name: weather_data
        >>>   warehouse: warehouse_warehouse
        >>>   database: meteorology
        >>>   schema: observations
        >>>   credentials: db_credentials
        >>>   load_args (WIP):
        >>>     Do we need any?
        >>>   save_args:
        >>>     mode: overwrite
    """

    # this dataset cannot be used with ``ParallelRunner``,
    # therefore it has the attribute ``_SINGLE_PROCESS = True``
    # for parallelism within a Spark pipeline please consider
    # ``ThreadRunner`` instead
    _SINGLE_PROCESS = True
    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # TODO: Update docstring
    def __init__(  # pylint: disable=too-many-arguments
        self,
        table_name: str,
        warehouse: str,
        database: str,
        schema: str,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
        credentials: Dict[str, Any] = None,
    ) -> None:
        """Creates a new instance of ``SnowParkDataSet``.

        Args:
            table_name:
            warehouse:
            database:
            schema:
            load_args:
            save_args: whatever supported by snowpark writer
            https://docs.snowflake.com/en/developer-guide/snowpark/reference/python/api/snowflake.snowpark.DataFrameWriter.saveAsTable.html
            credentials:
        """

        if not table_name:
            raise DataSetError("'table_name' argument cannot be empty.")

        # TODO: Check if we can use default warehouse when user is not providing one explicitly
        if not warehouse:
            raise DataSetError("'warehouse' argument cannot be empty.")

        if not database:
            raise DataSetError("'database' argument cannot be empty.")

        if not schema:
            raise DataSetError("'schema' argument cannot be empty.")

        if not credentials:
            raise DataSetError("Please configure expected credentials")

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        self._credentials = credentials["credentials"]

        self._session = self._get_session(self._credentials)
        self._table_name = table_name
        self._warehouse = warehouse
        self._database = database
        self._schema = schema

    def _describe(self) -> Dict[str, Any]:
        return dict(
            table_name=self._table_name,
            warehouse=self._warehouse,
            database=self._database,
            schema=self._schema,
        )

    # TODO: Do we want to make it static method?
    @classmethod
    def _get_session(cls, credentials: dict) -> sp.Session:
        """Given a connection string, create singleton connection
        to be used across all instances of `SnowParkDataSet` that
        need to connect to the same source.
            connection_params = {
                "account": "",
                "user": "",
                "password": "",
                "role": "", (optional)
                "warehouse": "", (optional)
                "database": "", (optional)
                "schema": "" (optional)
                }
        """
        try:
            session = sp.Session.builder.configs(credentials).create()
        except ImportError as import_error:
            raise _get_missing_module_error(import_error) from import_error
        except Exception as exception:
            raise exception
        return session

    def _load(self) -> sp.DataFrame:
        table_name = [
            self._database,
            self._schema,
            self._table_name,
        ]

        sp_df = self._session.table(".".join(table_name))
        return sp_df

    def _save(self, data: Union[pd.DataFrame, sp.DataFrame]) -> None:
        if not isinstance(data, sp.DataFrame):
            sp_df = self._session.create_dataframe(data)
        else:
            sp_df = data

        table_name = [
            self._database,
            self._schema,
            self._table_name,
        ]

        sp_df.write.mode(self._save_args["mode"]).save_as_table(
            table_name,
            column_order=self._save_args["column_order"],
            table_type=self._save_args["table_type"],
            statement_params=self._save_args["statement_params"],
        )

    def _exists(self) -> bool:
        session = self._session
        schema = self._schema
        exists = self._table_name in session.table_names(schema)
        return exists
