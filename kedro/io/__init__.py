"""``kedro.io`` provides functionality to read and write to a
number of data sets. At core of the library is the ``AbstractDataSet`` class.
"""

from .cached_dataset import CachedDataSet
from .core import (
    AbstractDataSet,
    AbstractDataset,
    AbstractVersionedDataSet,
    AbstractVersionedDataset,
    DataSetAlreadyExistsError,
    DatasetAlreadyExistsError,
    DataSetError,
    DatasetError,
    DataSetNotFoundError,
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
