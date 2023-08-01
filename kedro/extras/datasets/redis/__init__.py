"""``AbstractDataSet`` implementation to load/save data from/to a redis db."""

__all__ = ["PickleDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .redis_dataset import PickleDataSet
