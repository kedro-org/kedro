"""``AbstractDataSet`` implementations that produce pandas DataFrames."""

__all__ = [
    "CSVDataSet",
    "ExcelDataSet",
    "FeatherDataSet",
    "GBQTableDataSet",
    "GBQQueryDataSet",
    "ExcelDataSet",
    "AppendableExcelDataSet",
    "HDFDataSet",
    "JSONDataSet",
    "ParquetDataSet",
    "SQLQueryDataSet",
    "SQLTableDataSet",
    "GenericDataSet",
]

from contextlib import suppress

with suppress(ImportError):
    from .csv_dataset import CSVDataSet
with suppress(ImportError):
    from .excel_dataset import ExcelDataSet
with suppress(ImportError):
    from .appendable_excel_dataset import AppendableExcelDataSet
with suppress(ImportError):
    from .feather_dataset import FeatherDataSet
with suppress(ImportError):
    from .gbq_dataset import GBQQueryDataSet, GBQTableDataSet
with suppress(ImportError):
    from .hdf_dataset import HDFDataSet
with suppress(ImportError):
    from .json_dataset import JSONDataSet
with suppress(ImportError):
    from .parquet_dataset import ParquetDataSet
with suppress(ImportError):
    from .sql_dataset import SQLQueryDataSet, SQLTableDataSet
with suppress(ImportError):
    from .generic_dataset import GenericDataSet
