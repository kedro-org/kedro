"""SparkJDBCDataSet to load and save a PySpark DataFrame via JDBC."""

from copy import deepcopy
from typing import Any, Dict

from pyspark.sql import DataFrame, SparkSession

from kedro.io.core import AbstractDataSet, DataSetError

__all__ = ["SparkJDBCDataSet"]


class SparkJDBCDataSet(AbstractDataSet):
    """``SparkJDBCDataSet`` loads data from a database table accessible
    via JDBC URL url and connection properties and saves the content of
    a PySpark DataFrame to an external database table via JDBC.  It uses
    ``pyspark.sql.DataFrameReader`` and ``pyspark.sql.DataFrameWriter``
    internally, so it supports all allowed PySpark options on ``jdbc``.


    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        >>> weather:
        >>>   type: spark.SparkJDBCDataSet
        >>>   table: weather_table
        >>>   url: jdbc:postgresql://localhost/test
        >>>   credentials: db_credentials
        >>>   load_args:
        >>>     properties:
        >>>       driver: org.postgresql.Driver
        >>>   save_args:
        >>>     properties:
        >>>       driver: org.postgresql.Driver

    Example using Python API:
    ::

        >>> import pandas as pd
        >>>
        >>> from pyspark.sql import SparkSession
        >>>
        >>> spark = SparkSession.builder.getOrCreate()
        >>> data = spark.createDataFrame(pd.DataFrame({'col1': [1, 2],
        >>>                                            'col2': [4, 5],
        >>>                                            'col3': [5, 6]}))
        >>> url = 'jdbc:postgresql://localhost/test'
        >>> table = 'table_a'
        >>> connection_properties = {'driver': 'org.postgresql.Driver'}
        >>> data_set = SparkJDBCDataSet(
        >>>     url=url, table=table, credentials={'user': 'scott',
        >>>                                        'password': 'tiger'},
        >>>     load_args={'properties': connection_properties},
        >>>     save_args={'properties': connection_properties})
        >>>
        >>> data_set.save(data)
        >>> reloaded = data_set.load()
        >>>
        >>> assert data.toPandas().equals(reloaded.toPandas())

    """

    DEFAULT_LOAD_ARGS = {}  # type: Dict[str, Any]
    DEFAULT_SAVE_ARGS = {}  # type: Dict[str, Any]

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        url: str,
        table: str,
        credentials: Dict[str, Any] = None,
        load_args: Dict[str, Any] = None,
        save_args: Dict[str, Any] = None,
    ) -> None:
        """Creates a new ``SparkJDBCDataSet``.

        Args:
            url: A JDBC URL of the form ``jdbc:subprotocol:subname``.
            table: The name of the table to load or save data to.
            credentials: A dictionary of JDBC database connection arguments.
                Normally at least properties ``user`` and ``password`` with
                their corresponding values.  It updates ``properties``
                parameter in ``load_args`` and ``save_args`` in case it is
                provided.
            load_args: Provided to underlying PySpark ``jdbc`` function along
                with the JDBC URL and the name of the table. To find all
                supported arguments, see here:
                https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.DataFrameWriter.jdbc.html
            save_args: Provided to underlying PySpark ``jdbc`` function along
                with the JDBC URL and the name of the table. To find all
                supported arguments, see here:
                https://spark.apache.org/docs/latest/api/python/reference/api/pyspark.sql.DataFrameWriter.jdbc.html

        Raises:
            DataSetError: When either ``url`` or ``table`` is empty or
                when a property is provided with a None value.
        """

        if not url:
            raise DataSetError(
                "`url` argument cannot be empty. Please "
                "provide a JDBC URL of the form "
                "``jdbc:subprotocol:subname``."
            )

        if not table:
            raise DataSetError(
                "`table` argument cannot be empty. Please "
                "provide the name of the table to load or save "
                "data to."
            )

        self._url = url
        self._table = table

        # Handle default load and save arguments
        self._load_args = deepcopy(self.DEFAULT_LOAD_ARGS)
        if load_args is not None:
            self._load_args.update(load_args)
        self._save_args = deepcopy(self.DEFAULT_SAVE_ARGS)
        if save_args is not None:
            self._save_args.update(save_args)

        # Update properties in load_args and save_args with credentials.
        if credentials is not None:

            # Check credentials for bad inputs.
            for cred_key, cred_value in credentials.items():
                if cred_value is None:
                    raise DataSetError(
                        f"Credential property `{cred_key}` cannot be None. "
                        f"Please provide a value."
                    )

            load_properties = self._load_args.get("properties", {})
            save_properties = self._save_args.get("properties", {})
            self._load_args["properties"] = {**load_properties, **credentials}
            self._save_args["properties"] = {**save_properties, **credentials}

    def _describe(self) -> Dict[str, Any]:
        load_args = self._load_args
        save_args = self._save_args

        # Remove user and password values from load and save properties.
        if "properties" in load_args:
            load_properties = load_args["properties"].copy()
            load_properties.pop("user", None)
            load_properties.pop("password", None)
            load_args = {**load_args, "properties": load_properties}
        if "properties" in save_args:
            save_properties = save_args["properties"].copy()
            save_properties.pop("user", None)
            save_properties.pop("password", None)
            save_args = {**save_args, "properties": save_properties}

        return dict(
            url=self._url, table=self._table, load_args=load_args, save_args=save_args
        )

    @staticmethod
    def _get_spark():
        return SparkSession.builder.getOrCreate()

    def _load(self) -> DataFrame:
        return self._get_spark().read.jdbc(self._url, self._table, **self._load_args)

    def _save(self, data: DataFrame) -> None:
        return data.write.jdbc(self._url, self._table, **self._save_args)
