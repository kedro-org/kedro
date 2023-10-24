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

__all__ = [
    "AbstractDataset",
    "AbstractVersionedDataset",
    "CachedDataset",
    "DataCatalog",
    "DatasetAlreadyExistsError",
    "DatasetError",
    "DatasetNotFoundError",
    "LambdaDataset",
    "MemoryDataset",
    "Version",
]
