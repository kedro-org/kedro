# Migration guide
## Migration guide from Kedro 0.18.* to 0.19.*
* Removed the custom Kedro syntax for `--params`, use the OmegaConf syntax instead by replacing `:` with `=`.
* Removed the `create_default_data_set()` method in the `Runner`. To overwrite the default dataset creation, use the new `Runner` class argument `extra_dataset_patterns` instead.
* Removed `project_version` in `pyproject.toml` please use `kedro_init_version` instead.

### Datasets
* If you use `APIDataSet`, move all `requests` specific arguments (e.g. `params`, `headers`), except for `url` and `method`, to under `load_args`.
* Using the `layer` attribute at the top level is removed. Please move `layer` inside the `metadata` -> `kedro-viz` attributes.
* Renamed dataset and error classes, in accordance with the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide#kedro-lexicon). Dataset classes ending with "DataSet" and error classes starting with "DataSet" are removed. Note that all of the below classes are also importable from `kedro.io`; only the module where they are defined is listed as the location.

| Type                        | Removed Alias               | Location                       |
| --------------------------- | --------------------------- | ------------------------------ |
| `AbstractDataset`           | `AbstractDataSet`           | `kedro.io.core`                |
| `AbstractVersionedDataset`  | `AbstractVersionedDataSet`  | `kedro.io.core`                |
| `CachedDataset`             | `CachedDataSet`             | `kedro.io.cached_dataset`      |
| `LambdaDataset`             | `LambdaDataSet`             | `kedro.io.lambda_dataset`      |
| `MemoryDataset`             | `MemoryDataSet`             | `kedro.io.memory_dataset`      |
| `DatasetError`              | `DataSetError`              | `kedro.io.core`                |
| `DatasetAlreadyExistsError` | `DataSetAlreadyExistsError` | `kedro.io.core`                |
| `DatasetNotFoundError`      | `DataSetNotFoundError`      | `kedro.io.core`                |
* All other dataset classes are removed from the core Kedro repository (`kedro.extras.datasets`). Install and import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.

### Logging
`logging.yml` is now independent of Kedro's run environment and only used if `KEDRO_LOGGING_CONFIG` is set to point to it.
