"""``AbstractDataSet`` implementation to read/write from/to a sequence file."""

__all__ = ["BioSequenceDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .biosequence_dataset import BioSequenceDataSet
