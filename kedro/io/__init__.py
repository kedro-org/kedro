"""``kedro.io`` provides functionality to read and write to a
number of data sets. At the core of the library is the ``AbstractDataset`` class.
"""
from __future__ import annotations

import warnings

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

with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    from .cached_dataset import CachedDataSet
    from .lambda_dataset import LambdaDataSet
    from .memory_dataset import MemoryDataSet
    from .partitioned_dataset import IncrementalDataSet, PartitionedDataSet

# https://github.com/pylint-dev/pylint/issues/4300#issuecomment-1043601901
DataSetError: type[DatasetError]
DataSetNotFoundError: type[DatasetNotFoundError]
DataSetAlreadyExistsError: type[DatasetAlreadyExistsError]
AbstractDataSet: type[AbstractDataset]
AbstractVersionedDataSet: type[AbstractVersionedDataset]


def __getattr__(name):
    import kedro.io.core  # noqa: import-outside-toplevel

    if name in (kedro.io.core._DEPRECATED_CLASSES):  # noqa: protected-access
        return getattr(kedro.io.core, name)
    raise AttributeError(f"module {repr(__name__)} has no attribute {repr(name)}")


__all__ = [
    "AbstractDataSet",
    "AbstractDataset",
    "AbstractVersionedDataSet",
    "AbstractVersionedDataset",
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
