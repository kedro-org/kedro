# Use Templating and Variables

This page covers:

- [Template values within configuration files](#template-values-within-configuration-files)
- [Share variables across configurations with globals](#share-variables-across-configurations-with-globals)
- [Load catalog with templating in code](#load-catalog-with-templating-in-code)
- [Create custom resolvers for dynamic values](#create-custom-resolvers-for-dynamic-values)
- [Use built-in OmegaConf resolvers](#use-built-in-omegaconf-resolvers)
- [Override configuration with runtime parameters](#override-configuration-with-runtime-parameters)
- [Combine globals and runtime parameters](#combine-globals-and-runtime-parameters)

## Template values within configuration files

Use `${...}` syntax to reference values and avoid duplication.

### In parameters

```yaml
# conf/base/parameters.yml
data:
  size: 0.2

model_options:
  test_size: ${data.size}
```

Template files must match the `parameters*` pattern to be resolved.

### In catalog

```yaml
# conf/base/catalog_variables.yml
_file_format: "parquet"
_base_path: "s3://my-bucket/data"

# conf/base/catalog.yml
raw_data:
  type: spark.SparkDataset
  filepath: "${_base_path}/raw/data.${_file_format}"
  file_format: ${_file_format}
```

!!! note
    Catalog template variables must start with `_` to distinguish them from dataset definitions.

Template files must match the `catalog*` pattern to be resolved.

## Share variables across configurations with globals

Use `globals.yml` to share variables across different configuration types (parameters, catalog, etc.).

### Define global variables

```yaml
# conf/base/globals.yml
bucket_name: "my-s3-bucket"
file_format: "parquet"
dataset_type:
  csv: "pandas.CSVDataset"
```

### Use in parameters

```yaml
# conf/base/parameters.yml
data_settings:
  storage: "${globals:bucket_name}"
  format: "${globals:file_format}"
```

### Use in catalog

```yaml
# conf/base/catalog.yml
raw_data:
  type: "${globals:dataset_type.csv}"
  filepath: "s3://${globals:bucket_name}/raw/data.csv"
```

### Provide default values

```yaml
storage: "${globals:bucket_name, my-default-bucket}"
```

If `bucket_name` doesn't exist in `globals.yml`, it uses `my-default-bucket`.

## Load catalog with templating in code

`OmegaConfigLoader` automatically resolves templates:

```python
from kedro.config import OmegaConfigLoader
from kedro.framework.project import settings

conf_path = str(project_path / settings.CONF_SOURCE)
conf_loader = OmegaConfigLoader(conf_source=conf_path)

conf_catalog = conf_loader["catalog"]
# Templates are already resolved
```

---

## Create custom resolvers for dynamic values

Register custom resolvers to compute values dynamically:

```python
# src/my_project/settings.py
from datetime import date

CONFIG_LOADER_ARGS = {
    "custom_resolvers": {
        "today": lambda: date.today().isoformat(),
        "add": lambda *values: sum(values),
    }
}
```

Use in configuration:

```yaml
# conf/base/parameters.yml
run_date: "${today:}"
total_budget: "${add:100,200,300}"  # Returns 600
```

## Use built-in OmegaConf resolvers

### oc.env (credentials only)

Load from environment variables:

```yaml
# conf/local/credentials.yml
api_key: ${oc.env:API_KEY}
database_password: ${oc.env:DB_PASSWORD}
```

!!! note
    `oc.env` only works in `credentials.yml` by default to discourage using environment variables for non-credential configuration.

### oc.select

Provide default values:

```yaml
environment: ${oc.select:DEPLOY_ENV, development}
```

See the [OmegaConf documentation](https://omegaconf.readthedocs.io/en/latest/custom_resolvers.html#built-in-resolvers) for all built-in resolvers.

## Override configuration with runtime parameters

Specify that configuration values should be provided at runtime:

```yaml
# conf/base/parameters.yml
model_options:
  random_state: "${runtime_params:seed}"
  learning_rate: "${runtime_params:lr, 0.01}"  # With default
```

Provide values via CLI:

```bash
kedro run --params="seed=42,lr=0.05"
```

If `seed` is not provided, Kedro raises an error. If `lr` is not provided, it uses `0.01`.

### Works across configuration types

Use `runtime_params` in catalog, parameters, and other configuration (but not `globals`):

```yaml
# conf/base/catalog.yml
my_data:
  type: pandas.CSVDataset
  filepath: "${runtime_params:data_path, 'data/01_raw'}/companies.csv"
```

```bash
kedro run --params="data_path=data/staging"
```

## Combine globals and runtime parameters

Use globals as defaults for runtime parameters:

```yaml
# conf/base/globals.yml
default_learning_rate: 0.01

# conf/base/parameters.yml
model_options:
  learning_rate: "${runtime_params:lr, ${globals:default_learning_rate}}"
```

If `lr` is not provided at runtime, it uses the global default.

!!! note
    `runtime_params` cannot override `globals` directly. Globals have a single entry point (the YAML file) to keep configuration predictable.
