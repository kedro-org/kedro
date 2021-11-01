"""Provides I/O modules using dask dataframe."""

__all__ = ["ParquetDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .parquet_dataset import ParquetDataSet
