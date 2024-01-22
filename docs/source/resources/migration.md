# Migration guide

[See the release notes on GitHub](https://github.com/kedro-org/kedro/releases/) for comprehensive information about the content of each Kedro release.


## Migrate an existing project that uses Kedro 0.18.* to use 0.19.*

 
* [Kedro 0.19.0](https://github.com/kedro-org/kedro/releases/tag/0.19.0) removed the custom Kedro syntax for `--params`. To update, you need to use the OmegaConf syntax instead by replacing `:` with `=`.

<!-- TO DO - add example code and say what file it is in -- config.yml?? and link to the OmegaConf syntax -->

* Kedro 0.19 removed the `create_default_data_set()` method in the `Runner`. To overwrite the default dataset creation, you now need use the new `Runner` class argument `extra_dataset_patterns` instead.

<!-- TO DO - add example code and state where you'd be making this change -->

* Kedro 0.19 removed `project_version` in `pyproject.toml`. Use `kedro_init_version` instead.

<!-- TO DO - add example  -->

### Datasets changes in 0.19

* From 0.19, if you use `APIDataSet`, you need to move all `requests`-specific arguments (e.g. `params`, `headers`), except for `url` and `method`, in the hierarchy to sit under `load_args`.

<!-- TO DO - add example code and state where the change happens `catalog.yml` ??  -->


* From 0.19, the `layer` attribute at the top level has been  moved inside the `metadata` -> `kedro-viz` attributes. You need to update `catalog.yml` accordingly.

<!-- TO DO - add example code -->

* In 0.19.0 we renamed dataset and error classes in accordance with the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide#kedro-lexicon). 

    * Dataset classes ending with `DataSet` are replaced by classes that end with `Dataset`.
    
    * Error classes starting with `DataSet` are replaced by classes that start with `Dataset`. 

Note that all of the below classes are also importable from `kedro.io`; only the module where they are defined is listed as the location.

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

<!-- TO DO - add example code that illustrates where the changes have occured (which files are affected) -->
