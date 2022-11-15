"""Provides I/O modules for Snowflake."""

__all__ = ["SnowflakeTableDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .snowflake_dataset import SnowflakeTableDataSet
