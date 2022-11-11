"""``kedro.io`` provides functionality to read and write to a
number of data sets. At core of the library is ``AbstractDataSet``
which allows implementation of various ``AbstractDataSet``s.
"""

from .cached_dataset import CachedDataSet
from .core import (
    AbstractDataSet,
    AbstractVersionedDataSet,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    Version,
)
from .data_catalog import DataCatalog
from .lambda_dataset import LambdaDataSet
from .memory_dataset import MemoryDataSet
from .partitioned_dataset import IncrementalDataSet, PartitionedDataSet

__all__ = [
    "AbstractDataSet",
    "AbstractVersionedDataSet",
    "CachedDataSet",
    "DataCatalog",
    "DataSetAlreadyExistsError",
    "DataSetError",
    "DataSetNotFoundError",
    "IncrementalDataSet",
    "LambdaDataSet",
    "MemoryDataSet",
    "PartitionedDataSet",
    "Version",
]
