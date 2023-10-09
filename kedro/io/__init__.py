"""``kedro.io`` provides functionality to read and write to a
number of data sets. At the core of the library is the ``AbstractDataset`` class.
"""
from __future__ import annotations

from .cached_dataset import CachedDataset
from .core import (
    AbstractDataset,
    AbstractVersionedDataset,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
)
from .data_catalog import DataCatalog
from .lambda_dataset import LambdaDataset
from .memory_dataset import MemoryDataset
from .partitioned_dataset import (
    IncrementalDataset,
    PartitionedDataset,
)


def __getattr__(name):
    import kedro.io.core  # noqa: import-outside-toplevel

    if name in (kedro.io.core._DEPRECATED_CLASSES):  # noqa: protected-access
        return getattr(kedro.io.core, name)
    raise AttributeError(f"module {repr(__name__)} has no attribute {repr(name)}")


__all__ = [
    "AbstractDataset",
    "AbstractVersionedDataset",
    "CachedDataset",
    "DataCatalog",
    "DatasetAlreadyExistsError",
    "DatasetError",
    "DatasetNotFoundError",
    "IncrementalDataset",
    "LambdaDataset",
    "MemoryDataset",
    "PartitionedDataset",
    "Version",
]
