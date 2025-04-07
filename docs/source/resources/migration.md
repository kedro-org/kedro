# Migration guide

[See the release notes on GitHub](https://github.com/kedro-org/kedro/releases/) for comprehensive information about the content of each Kedro release.

## Migrate an existing project that uses Kedro 0.19.* to use 1.*

### Polishing API Surface
- Kedro 1.0.0 made the following private methods `_is_project` and `_find_kedro_project` public. To update, you need to use `is_kedro_project` and `find_kedro_project` respectively.
- Renamed instances of `extra_params` and `_extra_params` to `runtime_params` in `KedroSession`, `KedroContext` and `PipelineSpecs`. To update, start using `runtime_params` while creating a `KedroSession`, `KedroContext` or while using pipeline hooks like `before_pipeline_run`, `after_pipeline_run` and `on_pipeline_error`.

## Migrate an existing project that uses Kedro 0.18.* to use 0.19.*

### Custom syntax for `--params` was removed
[Kedro 0.19.0](https://github.com/kedro-org/kedro/releases/tag/0.19.0) removed the custom Kedro syntax for `--params`. To update, you need to use the OmegaConf syntax instead by replacing `:` with `=`.

If you used this command to pass parameters to `kedro run`:

```bash
kedro run --params=param_key1:value1,param_key2:2.0
```
You should now use the following:

```bash
kedro run --params=param_key1=value1,param_key2=2.0
```

For more information see ["How to specify parameters at runtime"](https://docs.kedro.org/en/stable/configuration/parameters.html#how-to-specify-parameters-at-runtime).

### `create_default_data_set()` was removed from `Runner`
Kedro 0.19 removed the `create_default_data_set()` method in the `Runner`. To overwrite the default dataset creation, you need to use the new `Runner` class argument `extra_dataset_patterns` instead.

On class instantiation, pass the `extra_dataset_patterns` argument, and overwrite the default `MemoryDataset` creation as follows:

```python
from kedro.runner import ThreadRunner

runner = ThreadRunner(extra_dataset_patterns={"{default}": {"type": "MyCustomDataset"}})
```

### `project_version` was removed
Kedro 0.19 removed `project_version` in `pyproject.toml`. Use `kedro_init_version` instead:

```diff
[tool.kedro]
package_name = "my_project"
project_name = "my project"
- project_version = "0.19.1"
+ kedro_init_version = "0.19.1"
```

### Datasets changes in 0.19

#### The `layer` attribute in `catalog.yml` has moved
From 0.19, the `layer` attribute at the top level has been  moved inside the `metadata` -> `kedro-viz` attribute. You need to update `catalog.yml` accordingly.

The following `catalog.yml` entry changes from the following in 0.18.x code:

```yaml
companies:
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv
  layer: raw
```

to this in 0.19.x:

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
  metadata:
    kedro-viz:
      layer: raw
```

See {doc}`See the Kedro-Viz documentation for more information<kedro-viz:kedro-viz_visualisation>`.


#### For `APIDataset`, the `requests`-specific arguments in `catalog.yml` have moved
From 0.19, if you use `APIDataset`, you need to move all `requests`-specific arguments, such as `params`, `headers`, in the hierarchy to sit under `load_args`. The `url` and `method` arguments are not affected.

For example the following `APIDataset` in `catalog.yml` changes from the following in 0.18.x code:

```yaml
us_corn_yield_data:
  type: api.APIDataSet
  url: https://quickstats.nass.usda.gov
  credentials: usda_credentials
  params:
    key: SOME_TOKEN
    format: JSON
```

to this in 0.19.x:

```yaml
us_corn_yield_data:
  type: api.APIDataSet
  url: https://quickstats.nass.usda.gov
  credentials: usda_credentials
  load_args:
    params:
      key: SOME_TOKEN
      format: JSON
```

#### Dataset renaming
In 0.19.0 we renamed dataset and error classes to follow the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide).

* Dataset classes ending with `DataSet` are replaced by classes that end with `Dataset`.
* Error classes starting with `DataSet` are replaced by classes that start with `Dataset`.

All the classes below are also importable from `kedro.io`; only the module where they are defined is listed as the location.

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


#### All other dataset classes are removed from the core Kedro repository (`kedro.extras.datasets`)
You now need to install and import datasets from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.

### Configuration changes in 0.19

The `ConfigLoader` and `TemplatedConfigLoader` classes were deprecated in Kedro 0.18.12 and were removed in Kedro 0.19.0. To use that release or later, you must now adopt the `OmegaConfigLoader`. The [configuration migration guide](../configuration/config_loader_migration.md) outlines the primary distinctions between the old loaders and the OmegaConfigLoader, and provides step-by-step instructions on updating your code base to use the new class effectively.


#### Changes to the default environments
The default configuration environment has changed in 0.19 and needs to be declared in `settings.py` explicitly if you have custom arguments. For example, if you use `CONFIG_LOADER_ARGS`  in `settings.py` to read Spark configuration, you need to add `base_env` and `default_run_env` explicitly.

Before 0.19.x:

```
CONFIG_LOADER_ARGS = {
#       "base_env": "base",
#       "default_run_env": "local",
    "config_patterns": {
        "spark": ["spark*", "spark*/**"],
    }
}
```

In 0.19.x:

```
CONFIG_LOADER_ARGS = {
      "base_env": "base",
      "default_run_env": "local",
          "config_patterns": {
              "spark": ["spark*", "spark*/**"],
          }
}
```

If you didn't use `CONFIG_LOADER_ARGS` in your code, this change is not needed because Kedro sets it by default.


### Logging
`logging.yml` is now independent of Kedro's run environment and used only if `KEDRO_LOGGING_CONFIG` is set to point to it. The [documentation on logging](https://docs.kedro.org/en/stable/logging/index.html) describes in detail how logging works in Kedro and how it can be customised.
