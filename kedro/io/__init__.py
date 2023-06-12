"""``kedro.io`` provides functionality to read and write to a
number of data sets. At the core of the library is the ``AbstractDataSet`` class.
"""

from .cached_dataset import CachedDataSet, CachedDataset
from .core import (
    AbstractDataSet,
    AbstractVersionedDataSet,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    Version,
)
from .data_catalog import DataCatalog
from .lambda_dataset import LambdaDataSet, LambdaDataset
from .memory_dataset import MemoryDataSet, MemoryDataset
from .partitioned_dataset import (
    IncrementalDataSet,
    IncrementalDataset,
    PartitionedDataSet,
    PartitionedDataset,
)

__all__ = [
    "AbstractDataSet",
    "AbstractVersionedDataSet",
    "CachedDataSet",
    "CachedDataset",
    "DataCatalog",
    "DataSetAlreadyExistsError",
    "DataSetError",
    "DataSetNotFoundError",
    "DatasetAlreadyExistsError",
    "DatasetError",
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
