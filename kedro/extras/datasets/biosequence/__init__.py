"""``AbstractDataset`` implementation to read/write from/to a sequence file."""

__all__ = ["BioSequenceDataSet", "BioSequenceDataset"]

from contextlib import suppress

with suppress(ImportError):
    from .biosequence_dataset import BioSequenceDataSet, BioSequenceDataset
