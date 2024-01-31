# Migration guide

[See the release notes on GitHub](https://github.com/kedro-org/kedro/releases/) for comprehensive information about the content of each Kedro release.


## Migrate an existing project that uses Kedro 0.18.* to use 0.19.*

### Custom syntax for `--params` was removed
[Kedro 0.19.0](https://github.com/kedro-org/kedro/releases/tag/0.19.0) removed the custom Kedro syntax for `--params`. To update, you need to use the OmegaConf syntax instead by replacing `:` with `=`.

If you previously used this command to pass parameters to `kedro run`:

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

#### `requests`-specific arguments in `catalog.yml` have moved
From 0.19, if you use `APIDataset`, you need to move all `requests`-specific arguments, e.g. `params`, `headers`, in the hierarchy to sit under `load_args`. The `url` and `method` arguments are not affected.

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
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv
  metadata:
    kedro-viz:
      layer: raw
```

#### Dataset renaming
In 0.19.0 we renamed dataset and error classes to follow the [Kedro lexicon](https://github.com/kedro-org/kedro/wiki/Kedro-documentation-style-guide).

* Dataset classes ending with `DataSet` are replaced by classes that end with `Dataset`.
* Error classes starting with `DataSet` are replaced by classes that start with `Dataset`.

Note that all of the classes below are also importable from `kedro.io`; only the module where they are defined is listed as the location.

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

### Logging
`logging.yml` is now independent of Kedro's run environment and only used if `KEDRO_LOGGING_CONFIG` is set to point to it. The [documentation on logging](https://docs.kedro.org/en/stable/logging/index.html) describes in detail how logging works in Kedro and how it can be customised.
