# kedro.io

::: kedro.io
    options:
      docstring_style: google
      members: false
      show_source: false

| Name                                   | Type       | Description                                      |
|----------------------------------------|------------|--------------------------------------------------|
| [`AbstractDataset`](kedro.io.AbstractDataset.md) | Class      | Base class for all Kedro datasets.              |
| [`AbstractVersionedDataset`](kedro.io.AbstractVersionedDataset.md) | Class | Base class for versioned datasets.              |
| [`CachedDataset`](kedro.io.CachedDataset.md)    | Class      | Dataset wrapper for caching data in memory.     |
| [`DataCatalog`](kedro.io.DataCatalog.md)        | Class      | Manages datasets used in a Kedro pipeline.      |
| [`LambdaDataset`](kedro.io.LambdaDataset.md)    | Class      | Dataset wrapper for inline data transformations.|
| [`MemoryDataset`](kedro.io.MemoryDataset.md)    | Class      | Dataset for storing data in memory.             |
| [`Version`](kedro.io.Version.md)                | Class      | Represents dataset version information.         |
| [`DatasetAlreadyExistsError`](kedro.io.DatasetAlreadyExistsError.md) | Exception | Raised when a dataset already exists.           |
| [`DatasetError`](kedro.io.DatasetError.md)      | Exception  | General dataset-related error.                  |
| [`DatasetNotFoundError`](kedro.io.DatasetNotFoundError.md) | Exception | Raised when a dataset is not found.             |
