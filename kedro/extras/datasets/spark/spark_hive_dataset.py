"""``AbstractDataSet`` implementation to access Spark dataframes using
``pyspark`` on Apache Hive.
"""

import pickle
import uuid
from typing import Any, Dict, List

from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import coalesce, col, lit

from kedro.io.core import AbstractDataSet, DataSetError


class StagedHiveDataSet:
    """
    Provides a context manager for temporarily writing data to a staging hive table, for example
    where you want to replace the contents of a hive table with data which relies on the data
    currently present in that table.

    Once initialised, the ``staged_data`` ``DataFrame`` can be queried and underlying tables used to
    define the initial dataframe can be modified without affecting ``staged_data``.

    Upon exiting this object it will drop the redundant staged table.
    """

    def __init__(
        self, data: DataFrame, stage_table_name: str, stage_database_name: str
    ):
        """
        Creates a new instance eof `StagedHiveDataSet`.

        Args:
            data: The spark dataframe to be staged
            stage_table_name: the database destination for the staged data
            stage_database_name: the table destination for the staged data
        """
        self.staged_data = None
        self._data = data
        self._stage_table_name = stage_table_name
        self._stage_database_name = stage_database_name
        self._spark_session = SparkSession.builder.getOrCreate()

    def __enter__(self):
        self._data.createOrReplaceTempView("tmp")

        _table = f"{self._stage_database_name}.{self._stage_table_name}"
        self._spark_session.sql(
            f"create table {_table} as select * from tmp"  # nosec
        ).take(1)
        self.staged_data = self._spark_session.sql(f"select * from {_table}")  # nosec
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._spark_session.sql(
            f"drop table {self._stage_database_name}.{self._stage_table_name}"  # nosec
        )


class SparkHiveDataSet(AbstractDataSet):
    """``SparkHiveDataSet`` loads and saves Spark dataframes stored on Hive.
    This data set also handles some incompatible file types such as using partitioned parquet on
    hive which will not normally allow upserts to existing data without a complete replacement
    of the existing file/partition.
    This DataSet has some key assumptions:
    - Schemas do not change during the pipeline run (defined PKs must be present for the
    duration of the pipeline)
    - Tables are not being externally modified during upserts. The upsert method is NOT ATOMIC
    to external changes to the target table while executing.
    Example adding a catalog entry with
    `YAML API <https://kedro.readthedocs.io/en/stable/05_data/\
        01_data_catalog.html#using-the-data-catalog-with-the-yaml-api>`_:
    .. code-block:: yaml
        >>> hive_dataset:
        >>>   type: spark.SparkHiveDataSet
        >>>   database: hive_database
        >>>   table: table_name
        >>>   write_mode: overwrite
        >>>   table_type: internal
        >>>   table_path: None
        >>>   table_format: None
    Example using Python API:
    ::
        >>> from pyspark.sql import SparkSession
        >>> from pyspark.sql.types import (StructField, StringType,
        >>>                                IntegerType, StructType)
        >>>
        >>> from kedro.extras.datasets.spark import SparkHiveDataSet
        >>>
        >>> schema = StructType([StructField("name", StringType(), True),
        >>>                      StructField("age", IntegerType(), True)])
        >>>
        >>> data = [('Alex', 31), ('Bob', 12), ('Clarke', 65), ('Dave', 29)]
        >>>
        >>> spark_df = SparkSession.builder.getOrCreate().createDataFrame(data, schema)
        >>>
        >>> data_set = SparkHiveDataSet(database="test_database", table="test_table",
        >>>                             write_mode="overwrite")
        >>> data_set.save(spark_df)
        >>> reloaded = data_set.load()
        >>>
        >>> reloaded.take(4)
    """

    def __init__(
        self, database: str, table: str, write_mode: str, table_format: str = "Parquet", table_type: str = "INTERNAL", table_path: str = None, table_pk: List[str] = None ,
    ) -> None:
        """Creates a new instance of ``SparkHiveDataSet``.
        Args:
            database: The name of the hive database.
            table: The name of the table within the database.
            write_mode: ``insert``, ``upsert`` or ``overwrite`` are supported.
            table_pk: If performing an upsert, this identifies the primary key columns used to
                resolve preexisting data. Is required for ``write_mode="upsert"``.
        Raises:
            DataSetError: Invalid configuration supplied
        """
        valid_write_modes = ["insert", "upsert", "overwrite"]
        if write_mode not in valid_write_modes:
            valid_modes = ", ".join(valid_write_modes)
            raise DataSetError(
                f"Invalid `write_mode` provided: {write_mode}. "
                f"`write_mode` must be one of: {valid_modes}"
            )
        if write_mode == "upsert" and not table_pk:
            raise DataSetError("`table_pk` must be set to utilise `upsert` read mode")

        valid_table_type = ["internal","external",None,"INTERNAL","EXTERNAL"]
        if table_type not in valid_table_type:
            valid_table_modes = ", ".join(valid_table_type)
            raise DataSetError(
                f"Invalid `table_type` provided: {table_type}. "
                f"`table_type` must be one of: {valid_table_modes}"
            )

        #nested if for external ONLY
        elif table_type in ["internal","INTERNAL",None]:
            print("Hive table created will be of Internal type")

        elif table_type in ["external","EXTERNAL"] and table_path == None:
            raise DataSetError(
                f"No path specified for External table type, please specify a path to save the external table on"
            )
        else:
            print( f"Hive table created will be of external type on path `{table_path}`")

        valid_table_formats = ["TextFile","SequenceFile","ORC","Parquet"]
        if table_format not in valid_table_formats:
            valid_table_format_modes = ", ".join(valid_table_formats)
            raise DataSetError(
                f"`table_format` : {table_format} is not supported as of now, contact Kedro support for enhancements"
                f"`table_format` must be one of: {valid_table_format_modes} types"
            )

        self._write_mode = write_mode
        self._table_pk = table_pk or []
        self._database = database
        self._table = table
        self._stage_table = "_temp_" + table
        self._table_type = table_type
        self._table_path = table_path
        self._table_format = table_format


        # self._table_columns is set up in _save() to speed up initialization
        self._table_columns = []  # type: List[str]

    def _describe(self) -> Dict[str, Any]:
        return dict(
            database=self._database,
            table=self._table,
            write_mode=self._write_mode,
            table_pk=self._table_pk,
            table_type=self._table_type,
            table_path=self._table_path,
            table_format=self._table_format
        )

    @staticmethod
    def _get_spark() -> SparkSession:
        return SparkSession.builder.getOrCreate()

    def _create_empty_hive_table(self, data):
        # if self._table_type and self._table_type.lower() == 'internal'
            #do external
            #fx createinternaltable
        if self._table_type in ["INTERNAL","internal",None]:
            data.createOrReplaceTempView("tmp")
            self._get_spark().sql(
                f"create table {self._database}.{self._table} STORED AS {self._table_format} as select * from tmp limit 1;"  # nosec
            )


        elif self._table_type in ["EXTERNAL","external"]:
            #other table options {}
            data.write.format(self._table_format).options(map("path", self._table_path)).saveAsTable(f"`{self._database}.{self._table}`")

        self._get_spark().sql(f"truncate table {self._database}.{self._table}")  # nosec

    def _load(self) -> DataFrame:
        if not self._exists():
            raise DataSetError(
                f"Requested table not found: {self._database}.{self._table}"
            )
        return self._get_spark().sql(
            f"select * from {self._database}.{self._table}"  # nosec
        )

    def _save(self, data: DataFrame) -> None:
        if not self._exists():
            self._create_empty_hive_table(data)
            self._table_columns = data.columns
        else:
            self._table_columns = self._load().columns
            if self._write_mode == "upsert":
                non_existent_columns = set(self._table_pk) - set(self._table_columns)
                if non_existent_columns:
                    colnames = ", ".join(sorted(non_existent_columns))
                    raise DataSetError(
                        f"Columns [{colnames}] selected as primary key(s) not found in "
                        f"table {self._database}.{self._table}"
                    )

        self._validate_save(data)
        write_methods = {
            "insert": self._insert_save,
            "upsert": self._upsert_save,
            "overwrite": self._overwrite_save,
        }
        write_methods[self._write_mode](data)

    def _insert_save(self, data: DataFrame) -> None:
        data.createOrReplaceTempView("tmp")
        columns = ", ".join(self._table_columns)
        self._get_spark().sql(
            f"insert into {self._database}.{self._table} select {columns} from tmp"  # nosec
        )

    def _upsert_save(self, data: DataFrame) -> None:
        if self._load().rdd.isEmpty():
            self._insert_save(data)
        else:
            joined_data = data.alias("new").join(
                self._load().alias("old"), self._table_pk, "outer"
            )
            upsert_dataset = joined_data.select(
                [  # type: ignore
                    coalesce(f"new.{col_name}", f"old.{col_name}").alias(col_name)
                    for col_name in set(data.columns)
                    - set(self._table_pk)  # type: ignore
                ]
                + self._table_pk
            )
            temporary_persisted_tbl_name = f"temp_{uuid.uuid4().int}"
            with StagedHiveDataSet(
                upsert_dataset,
                stage_database_name=self._database,
                stage_table_name=temporary_persisted_tbl_name,
            ) as temp_table:
                self._overwrite_save(temp_table.staged_data)

    def _overwrite_save(self, data: DataFrame) -> None:
        self._get_spark().sql(f"truncate table {self._database}.{self._table}")  # nosec
        self._insert_save(data)

    def _validate_save(self, data: DataFrame):
        hive_dtypes = set(self._load().dtypes)
        data_dtypes = set(data.dtypes)
        if data_dtypes != hive_dtypes:
            new_cols = data_dtypes - hive_dtypes
            missing_cols = hive_dtypes - data_dtypes
            raise DataSetError(
                f"Dataset does not match hive table schema.\n"
                f"Present on insert only: {sorted(new_cols)}\n"
                f"Present on schema only: {sorted(missing_cols)}"
            )

    def _exists(self) -> bool:
        if (
            self._get_spark()
            .sql("show databases")
            .filter(col("namespace") == lit(self._database))
            .take(1)
        ):
            self._get_spark().sql(f"use {self._database}")
            if (
                self._get_spark()
                .sql("show tables")
                .filter(col("tableName") == lit(self._table))
                .take(1)
            ):
                return True
        return False

    def __getstate__(self) -> None:
        raise pickle.PicklingError("PySpark datasets can't be serialized")
