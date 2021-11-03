"""``AbstractDataSet`` implementation to load/save data from/to a text file."""

__all__ = ["TextDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .text_dataset import TextDataSet
