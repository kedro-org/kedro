"""Databricks' persistent table DataSet."""
from typing import Any, Dict, Union

import pandas as pd
from kedro.io.core import AbstractDataSet, DataSetError
from pyspark.sql import DataFrame, SparkSession
from pyspark.sql.functions import col, lit


class DatabricksDataSet(AbstractDataSet):
    def __init__(
        self,
        database: str,
        table: str,
        write_mode: str = "error",
        to_pandas: bool = False,
    ) -> None:
        valid_write_modes = ["append", "overwrite", "error", "errorifexists", "ignore"]
        if write_mode not in valid_write_modes:
            valid_modes = ", ".join(valid_write_modes)
            raise DataSetError(
                f"Invalid `write_mode` provided: {write_mode}. "
                f"`write_mode` must be one of: {valid_modes}"
            )
        self._write_mode = write_mode
        self._database = database
        self._table = table
        self._to_pandas = to_pandas

    def _describe(self) -> Dict[str, Any]:
        return dict(
            database=self._database,
            table=self._table,
            write_mode=self._write_mode,
            to_pandas=self._to_pandas,
        )

    @staticmethod
    def _get_spark() -> SparkSession:
        return SparkSession.builder.getOrCreate()

    def _exists(self) -> bool:
        if (
            self._get_spark()
            .sql("show databases")
            .filter(col("namespace") == lit(self._database))
            .take(1)
        ):
            if (
                self._get_spark()
                .sql(f"show tables in {self._database}")
                .filter(col("tableName") == lit(self._table))
                .take(1)
            ):
                return True
        return False

    def _load(self) -> Union[DataFrame, pd.DataFrame]:
        if not self._exists():
            raise DataSetError(
                f"Requested table not found: {self._database}.{self._table}"
            )
        res = self._get_spark().table(f"{self._database}.{self._table}")
        if not self._to_pandas:
            return res
        else:
            return res.toPandas()

    def _save(self, data: DataFrame) -> None:
        spark = self._get_spark()
        spark.sql(f"create database if not exists {self._database}")
        data.write.mode(self._write_mode).saveAsTable(
            f"{self._database}.{self._table}", format="parquet",
        )
