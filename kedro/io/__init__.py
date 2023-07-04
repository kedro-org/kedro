"""``kedro.io`` provides functionality to read and write to a
number of data sets. At the core of the library is the ``AbstractDataSet`` class.
"""
from __future__ import annotations

from .cached_dataset import CachedDataset, CachedDataSet
from .core import (
    AbstractDataSet,
    AbstractVersionedDataSet,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
)
from .data_catalog import DataCatalog
from .lambda_dataset import LambdaDataset, LambdaDataSet
from .memory_dataset import MemoryDataset, MemoryDataSet
from .partitioned_dataset import (
    IncrementalDataset,
    IncrementalDataSet,
    PartitionedDataset,
    PartitionedDataSet,
)

# https://github.com/pylint-dev/pylint/issues/4300#issuecomment-1043601901
DataSetError: type[Exception]
DataSetNotFoundError: type[DatasetError]
DataSetAlreadyExistsError: type[DatasetError]


def __getattr__(name):
    import kedro.io.core  # pylint: disable=import-outside-toplevel

    if name in (
        kedro.io.core._DEPRECATED_ERROR_CLASSES  # pylint: disable=protected-access
    ):
        return getattr(kedro.io.core, name)
    raise AttributeError(f"module {repr(__name__)} has no attribute {repr(name)}")


__all__ = [
    "AbstractDataSet",
    "AbstractVersionedDataSet",
    "CachedDataSet",
    "CachedDataset",
    "DataCatalog",
    "DataSetAlreadyExistsError",
    "DatasetAlreadyExistsError",
    "DataSetError",
    "DatasetError",
    "DataSetNotFoundError",
    "DatasetNotFoundError",
    "IncrementalDataSet",
    "IncrementalDataset",
    "LambdaDataSet",
    "LambdaDataset",
    "MemoryDataSet",
    "MemoryDataset",
    "PartitionedDataSet",
    "PartitionedDataset",
    "Version",
]
