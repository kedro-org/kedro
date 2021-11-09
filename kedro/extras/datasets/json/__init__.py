"""``AbstractDataSet`` implementation to load/save data from/to a JSON file."""

__all__ = ["JSONDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .json_dataset import JSONDataSet
