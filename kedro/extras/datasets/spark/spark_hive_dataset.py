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

"""``AbstractDataSet`` implementation to access Spark dataframes using
``pyspark`` on Apache Hive.
"""

import pickle
import uuid
from typing import Any, Dict, List

from pyspark.sql import DataFrame, SparkSession  # pylint: disable=import-error
from pyspark.sql.functions import (  # pylint: disable=import-error,no-name-in-module
    coalesce,
    col,
    lit,
)

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

    Example:
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
        self, database: str, table: str, write_mode: str, table_pk: List[str] = None
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

        self._write_mode = write_mode
        self._table_pk = table_pk or []
        self._database = database
        self._table = table
        self._stage_table = "_temp_" + table

        # self._table_columns is set up in _save() to speed up initialization
        self._table_columns = []  # type: List[str]

    def _describe(self) -> Dict[str, Any]:
        return dict(
            database=self._database,
            table=self._table,
            write_mode=self._write_mode,
            table_pk=self._table_pk,
        )

    @staticmethod
    def _get_spark() -> SparkSession:
        return SparkSession.builder.getOrCreate()

    def _create_empty_hive_table(self, data):
        data.createOrReplaceTempView("tmp")
        self._get_spark().sql(
            f"create table {self._database}.{self._table} select * from tmp limit 1"  # nosec
        )
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
