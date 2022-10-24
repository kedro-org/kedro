"""``AbstractDataSet`` implementation that produces arbitrary objects from HDF5 files."""

__all__ = ["H5pyDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .h5py_dataset import H5pyDataSet
