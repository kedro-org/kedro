"""``AbstractDataSet`` implementation to load/save data from/to a svmlight/
libsvm sparse data file."""
__all__ = ["SVMLightDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .svmlight_dataset import SVMLightDataSet
