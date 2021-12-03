"""Provides I/O modules for Apache Spark."""

__all__ = ["SparkDataSet", "SparkHiveDataSet", "SparkJDBCDataSet", "DeltaTableDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .spark_dataset import SparkDataSet
with suppress(ImportError):
    from .spark_hive_dataset import SparkHiveDataSet
with suppress(ImportError):
    from .spark_jdbc_dataset import SparkJDBCDataSet
with suppress(ImportError):
    from .deltatable_dataset import DeltaTableDataSet
