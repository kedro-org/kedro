# Kedro dataset factories
You can load multiple datasets with similar configuration using dataset factories, introduced in Kedro `0.18.12`.

!!! warning
    Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
    From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.


The dataset factories introduce a syntax that allows you to generalise your configuration and reduce the number of similar catalog entries by matching datasets used in your project's pipelines to dataset factory patterns.

For example:
```yaml
factory_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/factory_data.csv

process_data:
  type: pandas.CSVDataset
  filepath: data/01_raw/process_data.csv
```

With dataset factory, it can be re-written as:
```yaml
"{name}_data":
  type: pandas.CSVDataset
  filepath: data/01_raw/{name}_data.csv
```

In runtime, the pattern will be matched against the name of the datasets defined in `inputs` or `outputs`.
```python
Node(
    func=process_factory,
    inputs="factory_data",
    outputs="process_data",
),

...
```

!!! note
    The factory pattern must always be enclosed in quotes to avoid YAML parsing errors.

Dataset factories behave like a **regular expression** and you can think of the syntax as a reversed `f-string`. In this case, the name of the input dataset `factory_data` matches the pattern `{name}_data` with the `_data` suffix, so it resolves `name` to `factory`. Likewise, it resolves `name` to `process` for the output dataset `process_data`.

This allows you to use one dataset factory pattern to replace multiple dataset entries. It keeps your catalog concise and lets you generalise datasets by name, type, or namespace.

## Types of patterns

The catalog supports three types of factory patterns:

1. Dataset patterns
2. User catch-all pattern
3. Default runtime patterns

**Dataset patterns**

Dataset patterns are defined explicitly in the `catalog.yml` using placeholders such as `{name}_data`.
```yaml
"{name}_data":
  type: pandas.CSVDataset
  filepath: data/01_raw/{name}_data.csv
```
This allows any dataset named `something_data` to be dynamically resolved using the pattern.

**User catch-all pattern**

A user catch-all pattern acts as a fallback when no dataset patterns match. It also uses a placeholder like `{default_dataset}`.
```yaml
"{default_dataset}":
  type: pandas.CSVDataset
  filepath: data/{default_dataset}.csv
```

!!! note
    A single user catch-all pattern is allowed per catalog. If more are specified, Kedro raises a `DatasetError`.

**Default runtime patterns**

Default runtime patterns are built-in patterns used by Kedro when datasets are not defined in the catalog, often for intermediate datasets generated during a pipeline run.
They are defined per catalog type:
```python
# For DataCatalog
default_runtime_patterns: ClassVar = {
    "{default}": {"type": "kedro.io.MemoryDataset"}
}

# For SharedMemoryDataCatalog
default_runtime_patterns: ClassVar = {
    "{default}": {"type": "kedro.io.SharedMemoryDataset"}
}
```
These patterns enable automatic creation of in-memory or shared-memory datasets during execution.

## Patterns resolution order
When the `DataCatalog` is initialised, it scans the configuration to extract and validate any dataset patterns and the user catch-all pattern.

When resolving a dataset name, Kedro uses the following order of precedence:

1. **Dataset patterns:**
Specific patterns defined in the `catalog.yml`. These are the most explicit and are matched first.

2. **User catch-all pattern:**
A general fallback pattern (for example, `{default_dataset}`) that is matched if no dataset patterns apply. A single user catch-all pattern is allowed. Multiple patterns raise a `DatasetError`.

3. **Default runtime patterns:**
Internal fallback behaviour provided by Kedro. These patterns are built into the catalog and automatically used at runtime to create datasets (for example, `MemoryDataset` or `SharedMemoryDataset`) when none of the above match.

## How resolution works in practice

By default, runtime patterns are not used when calling `catalog.get()` unless explicitly enabled using the `fallback_to_runtime_pattern=True` flag.

**Case 1: Dataset pattern only**

```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv
```

```bash
In [1]: catalog.get("reviews#csv")
Out[1]: kedro_datasets.pandas.csv_dataset.CSVDataset(filepath=.../data/01_raw/reviews.csv'), protocol='file', load_args={}, save_args={'index': False})

In [2]: catalog.get("nonexistent")
DatasetNotFoundError: Dataset 'nonexistent' not found in the catalog
```

Enable fallback to use runtime defaults:
```bash
In [3]: catalog.get("nonexistent", fallback_to_runtime_pattern=True)
Out[3]: kedro.io.memory_dataset.MemoryDataset()
```

**Case 2: Adding a user catch-all pattern**

```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv

"{default_dataset}":
  type: pandas.CSVDataset
  filepath: data/{default_dataset}.csv
```

```bash
In [1]: catalog.get("reviews#csv")
Out[1]: CSVDataset(filepath=.../data/01_raw/reviews.csv)

In [2]: catalog.get("nonexistent")
WARNING: Config from the dataset pattern '{default_dataset}' in the catalog will be used to override the default dataset creation for 'nonexistent'
Out[2]: CSVDataset(filepath=.../data/nonexistent.csv)
```

**Default vs runtime behaviour**

- Default behaviour: `DataCatalog` resolves dataset patterns and user catch-all patterns.
- Runtime behaviour (for example, during `kedro run`): Default runtime patterns are automatically enabled to resolve intermediate datasets not defined in `catalog.yml`.

!!! note
    Enabling `fallback_to_runtime_pattern=True` is recommended for advanced users with specific use cases. In most scenarios, Kedro handles it automatically during runtime.

## How to generalise datasets of the same type

You can also combine all the datasets with the same type and configuration details. For example, consider the following
catalog with three datasets named `boats`, `cars` and `planes` of the type `pandas.CSVDataset`:

```yaml
boats:
  type: pandas.CSVDataset
  filepath: data/01_raw/shuttles.csv

cars:
  type: pandas.CSVDataset
  filepath: data/01_raw/reviews.csv

planes:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv
```

These datasets can be combined into the following dataset factory:

```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv
```

You will then have to update the pipelines in your project located at `src/<project_name>/<pipeline_name>/pipeline.py` to reference these datasets as `boats#csv`,
`cars#csv` and `planes#csv`. Adding a suffix or a prefix to the dataset names and the dataset factory patterns, like `#csv` here, ensures that the dataset
names are matched with the intended pattern.

```python
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles


def create_pipeline(**kwargs) -> Pipeline:
    return Pipeline(
        [
            Node(
                func=preprocess_boats,
                inputs="boats#csv",
                outputs="preprocessed_boats",
                name="preprocess_boats_node",
            ),
            Node(
                func=preprocess_cars,
                inputs="cars#csv",
                outputs="preprocessed_cars",
                name="preprocess_cars_node",
            ),
            Node(
                func=preprocess_planes,
                inputs="planes#csv",
                outputs="preprocessed_planes",
                name="preprocess_planes_node",
            ),
            Node(
                func=create_model_input_table,
                inputs=[
                    "preprocessed_boats",
                    "preprocessed_planes",
                    "preprocessed_cars",
                ],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```
## How to generalise datasets using namespaces

You can also generalise the catalog entries for datasets belonging to namespaced modular pipelines. Consider the
following pipeline which takes in a `model_input_table` and outputs two regressors belonging to the
`active_modelling_pipeline` and the `candidate_modelling_pipeline` namespaces:

```python
from kedro.pipeline import Pipeline, Node

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    pipeline_instance = Pipeline(
        [
            Node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "y_train"],
                name="split_data_node",
            ),
            Node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
        ]
    )
    ds_pipeline_1 = Pipeline(
        nodes=pipeline_instance,
        inputs="model_input_table",
        namespace="active_modelling_pipeline",
    )
    ds_pipeline_2 = Pipeline(
        nodes=pipeline_instance,
        inputs="model_input_table",
        namespace="candidate_modelling_pipeline",
    )

    return ds_pipeline_1 + ds_pipeline_2
```
You can now have one dataset factory pattern in your catalog instead of two separate entries for `active_modelling_pipeline.regressor`
and `candidate_modelling_pipeline.regressor` as below:

```yaml
"{namespace}.regressor":
  type: pickle.PickleDataset
  filepath: data/06_models/regressor_{namespace}.pkl
  versioned: true
```

## How to generalise datasets of the same type in different layers

You can use multiple placeholders in the same pattern. For example, consider the following catalog where the dataset
entries share `type`, `file_format` and `save_args`:

```yaml
processing-factory_data:
  type: spark.SparkDataset
  filepath: data/processing/factory_data.parquet
  file_format: parquet
  save_args:
    mode: overwrite

processing-process_data:
  type: spark.SparkDataset
  filepath: data/processing/process_data.parquet
  file_format: parquet
  save_args:
    mode: overwrite

modelling-metrics:
  type: spark.SparkDataset
  filepath: data/modelling/factory_data.parquet
  file_format: parquet
  save_args:
    mode: overwrite
```

This could be generalised to the following pattern:

```yaml
"{layer}-{dataset_name}":
  type: spark.SparkDataset
  filepath: data/{layer}/{dataset_name}.parquet
  file_format: parquet
  save_args:
    mode: overwrite
```
All the placeholders used in the catalog entry body must exist in the factory pattern name.

## How to generalise datasets using multiple dataset factories
You can have multiple dataset factories in your catalog. For example:

```yaml
"{namespace}.{dataset_name}@spark":
  type: spark.SparkDataset
  filepath: data/{namespace}/{dataset_name}.parquet
  file_format: parquet

"{dataset_name}@csv":
  type: pandas.CSVDataset
  filepath: data/01_raw/{dataset_name}.csv
```

Having multiple dataset factories in your catalog can lead to a situation where a dataset name from your pipeline might
match multiple patterns. To overcome this, Kedro sorts all the potential matches for the dataset name in the pipeline and picks the best match.
The matches are ranked according to the following criteria:

1. Number of exact character matches between the dataset name and the factory pattern. For example, a dataset named `factory_data$csv` would match `{dataset}_data$csv` over `{dataset_name}$csv`.
2. Number of placeholders. For example, the dataset `preprocessing.shuttles+csv` would match `{namespace}.{dataset}+csv` over `{dataset}+csv`.
3. Alphabetical order

## How to override the default dataset creation with dataset factories

You can use dataset factories to define a catch-all pattern which will overwrite the default [kedro.io.MemoryDataset][] creation.

```yaml
"{default_dataset}":
  type: pandas.CSVDataset
  filepath: data/{default_dataset}.csv

```
Kedro will now treat all the datasets mentioned in your project's pipelines that do not appear as specific patterns or explicit entries in your catalog
as `pandas.CSVDataset`.

## User facing API

The logic behind pattern resolution is handled by the internal `CatalogConfigResolver`, available as a property on the catalog (`catalog.config_resolver`).

Here are several APIs that might be useful for custom use cases:

- `catalog_config_resolver.match_dataset_pattern()` - checks if the dataset name matches any dataset pattern
- `catalog_config_resolver.match_user_catch_all_pattern()` - checks if dataset name matches the user defined catch all pattern
- `catalog_config_resolver.match_runtime_pattern()` - checks if dataset name matches the default runtime pattern
- `catalog_config_resolver.resolve_pattern()` -  resolves a dataset name to its configuration based on patterns in the order explained above
- `catalog_config_resolver.list_patterns()` - lists all patterns available in the catalog
- `catalog_config_resolver.is_pattern()` - checks if a given string is a pattern

Refer to the method docstrings for more detailed examples and usage.

## Catalog and CLI commands

The DataCatalog provides three powerful pipeline-based commands, accessible through both the CLI and interactive environments. These tools help inspect how datasets are resolved and managed within your pipeline.

**Describe datasets**

Describes datasets used in the specified pipeline(s), grouped by how they are defined.

- datasets: Explicitly defined in catalog.yml
- factories: Resolved using dataset factory patterns
- defaults: Handled by user catch-all or default runtime patterns

CLI:
```bash
kedro catalog describe-datasets -p data_processing
```

Interactive environment:
```bash
In [1]: catalog.describe_datasets(pipelines=["data_processing", "data_science"])
```

Example output:
```yaml
data_processing:
  datasets:
    kedro_datasets.pandas.excel_dataset.ExcelDataset:
    - shuttles
    kedro_datasets.pandas.parquet_dataset.ParquetDataset:
    - preprocessed_shuttles
    - model_input_table
  defaults:
    kedro.io.MemoryDataset:
    - preprocessed_companies
  factories:
    kedro_datasets.pandas.csv_dataset.CSVDataset:
    - companies#csv
    - reviews-01_raw#csv
```

!!! note
    If no pipelines are specified, the `__default__` pipeline is used.

**List patterns**

Lists all dataset factory patterns defined in the catalog, ordered by priority.

CLI:
```bash
kedro catalog list-patterns
```

Interactive environment:
```bash
In [1]: catalog.list_patterns()
```

Example output:
```yaml
- '{name}-{folder}#csv'
- '{name}_data'
- out-{dataset_name}
- '{dataset_name}#csv'
- in-{dataset_name}
- '{default}'
```

**Resolve patterns**

Resolves datasets used in the pipeline against all dataset patterns, returning their full catalog configuration. It includes datasets explicitly defined in the catalog as well as those resolved from dataset factory patterns.

CLI command:
```bash
kedro catalog resolve-patterns -p data_processing
```

Interactive environment:
```bash
In [1]: catalog.resolve_patterns(pipelines=["data_processing"])
```

Example output:
```yaml
companies#csv:
  type: pandas.CSVDataset
  filepath: ...data/01_raw/companies.csv
  credentials: companies#csv_credentials
  metadata:
    kedro-viz:
      layer: training
```

!!! note
    If no pipelines are specified, the `__default__` pipeline is used.

### Implementation details and Python API usage

To ensure a consistent experience across the CLI, interactive environments (like IPython or Jupyter), and the Python API, we introduced pipeline-aware catalog commands using a mixin-based design.

At the core of this implementation is the `CatalogCommandsMixin` - a mixin class that extends the DataCatalog with additional methods for working with dataset factory patterns and pipeline-specific datasets.

**Why use a mixin?**

The goal was to keep pipeline logic decoupled from the core `DataCatalog`, while still providing seamless access to helpful methods utilising pipelines.

This `mixin` approach injects these commands when they are needed, which avoids unnecessary overhead in simpler catalog use cases.

**What this means in practice?**

You don't need to do anything if:

- You're using Kedro through the CLI, or
- Working inside an interactive environment (for example, IPython, Jupyter Notebook).

Kedro automatically composes the catalog with `CatalogCommandsMixin` behind the scenes when initialising the session.

If you're working outside a Kedro session and want to access the extra catalog commands, you have two options:

**Option 1: Compose the catalog class dynamically**

```python
from kedro.io import DataCatalog
from kedro.framework.context import CatalogCommandsMixin, compose_classes

# Compose a new catalog class with the mixin
CatalogWithCommands = compose_classes(DataCatalog, CatalogCommandsMixin)

# Create a catalog instance from config or dictionary
catalog = CatalogWithCommands.from_config({
    "cars": {
        "type": "pandas.CSVDataset",
        "filepath": "cars.csv",
        "save_args": {"index": False}
    }
})

assert hasattr(catalog, "describe_datasets")
print("describe_datasets method is available!")
```

**Option 2: Subclass the catalog with the mixin**

```python
from kedro.io import DataCatalog, MemoryDataset
from kedro.framework.context import CatalogCommandsMixin

class DataCatalogWithMixins(DataCatalog, CatalogCommandsMixin):
    pass

catalog = DataCatalogWithMixins(datasets={"example": MemoryDataset()})

assert hasattr(catalog, "describe_datasets")
print("describe_datasets method is available!")
```

This design keeps your project flexible and modular, while offering a powerful set of pipeline-aware catalog inspection tools when you need them.
