# Data Catalog Test Phase

Before the release of `DataCatalog` version 1.0, we aim to validate its usability, functionality, and effectiveness through user testing. Our objectives are to:

- Identify what works well
- Uncover pain points
- Determine improvements needed before the final release

This document includes installation instructions, suggested testing scenarios, and an overview of new, updated, and deprecated features, with usage examples:

- [Installation](#installation)
- [Suggested Testing Scenarios](#suggested-testing-scenarios)
- [Catalog API and Related Components Updates](#catalog-api-and-related-components-updates)
    - [Dataset Factories](#dataset-factories)
    - [Catalog and CLI commands](#catalog-and-cli-commands)
    - [Runners](#runners)
    - [DataCatalog API](#datacatalog-api)
    - [Deprecated API](#deprecated-api)

# Installation

1. Install `kedro` from  the `feature-1.0.0` branch
```bash
git clone https://github.com/kedro-org/kedro.git
cd kedro
git fetch origin feature-1.0.0
git checkout feature-1.0.0
pip install .
```
2. (Optional) Install compatible kedro-viz for testing:
```console
pip install git+https://github.com/kedro-org/kedro-viz.git@chore/compat-dc#subdirectory=package
```

# Suggested Testing Scenarios

These suggested scenarios aim to guide your testing, but we encourage you to explore the catalog as you would in a real project.

Try using each via: `kedro run`, Python API, IPython, and Jupyter Notebook.

1. Catalog API
    - Access and manipulate datasets
    - Load and save data
    - Iterate through catalog entries
    - Check dataset presence
    - Filter datasets by name or type
    - Inspect dataset types

2. Pattern Resolution
    - Test pattern resolution (dataset-specific, user catch-all, runtime)

3. Catalog Serialization
    - Convert a KedroDataCatalog instance to config (`to_config`)
    - Load a catalog from a saved config

4. Hooks
    - Trigger and validate catalog-related hooks (e.g., `after_catalog_created`)

5. Pipeline Execution
    - Run pipelines using different runners (sequential, thread and parallel):
        - `kedro run`
        - Python API (runner.run() / session.run())
    - Validate runner outputs

6. CLI Features
    - Test new catalog CLI commands
    - Try both interactive and scripted usage

7. Versioning
    - Validate dataset versioning functionality

8. Real-World Scenarios
    - Use the catalog as you would in a production project

# Catalog API and related components updates

## Lazy loading

The new `DataCatalog` introduces a helper class called `_LazyDataset` to improve performance and optimize dataset loading.

### What is `_LazyDataset`?
`_LazyDataset` is a lightweight internal class that stores the configuration and versioning information of a dataset without immediately instantiating it. This allows the catalog to defer actual dataset creation (also called materialization) until it is explicitly accessed.
This approach reduces startup overhead, especially when working with large catalogs, since only the datasets you actually use are initialized.

### When is `_LazyDataset` used?
When you instantiate a `DataCatalog` from a config file (such as `catalog.yml`), Kedro doesn't immediately create all the underlying dataset objects. Instead, it wraps each dataset in a `_LazyDataset` and registers it in the catalog.
These placeholders are automatically materialized when a dataset is accessed for the first time-either directly or during pipeline execution.

```bash
In [1]: catalog
Out[1]: {
  'shuttles': kedro_datasets.pandas.excel_dataset.ExcelDataset
}

# At this point, 'shuttles' has not been fully instantiated—only its config is registered.

In [2]: catalog["shuttles"]
Out[2]: kedro_datasets.pandas.excel_dataset.ExcelDataset(
    filepath=PurePosixPath('/Projects/default/data/01_raw/shuttles.xlsx'),
    protocol='file',
    load_args={'engine': 'openpyxl'},
    save_args={'index': False},
    writer_args={'engine': 'openpyxl'}
)

# Accessing the dataset triggers materialization.

In [3]: catalog
Out[3]: {
    'shuttles': kedro_datasets.pandas.excel_dataset.ExcelDataset(
        filepath=PurePosixPath('/Projects/default/data/01_raw/shuttles.xlsx'),
        protocol='file',
        load_args={'engine': 'openpyxl'},
        save_args={'index': False},
        writer_args={'engine': 'openpyxl'}
    )
}
```

### When is this useful?
This lazy loading mechanism is especially beneficial before runtime, during the warm-up phase of a pipeline. You can force materialization of all datasets early on to:

- Catch configuration or import errors
- Validate external dependencies
- Ensure all datasets can be created before execution begins

Although `_LazyDataset` is not exposed to end users and doesn't affect your usual catalog usage, it's a useful concept to understand when debugging catalog behavior or troubleshooting dataset instantiation issues.

## Dataset factories
The concept of dataset factories remains the same in the updated `DataCatalog`, but the implementation has been significantly simplified. Dataset factories allow you to generalize configuration patterns and reduce boilerplate by dynamically resolving datasets based on matching names used in your pipeline.

The catalog now supports only three types of factory patterns:

1. Dataset patterns
2. User catch-all pattern
3. Default runtime patterns

### Types of patterns

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
```{note}
Only one user catch-all pattern is allowed per catalog. If more are specified, a `DatasetError` will be raised.
```

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

### Patterns resolution order
When the `DataCatalog` is initialized, it scans the configuration to extract and validate any dataset patterns and user catch-all pattern.

When resolving a dataset name, Kedro uses the following order of precedence:

1. **Dataset patterns:**
Specific patterns defined in the `catalog.yml`. These are the most explicit and are matched first.

2. **User catch-all pattern:**
A general fallback pattern (e.g., `{default_dataset}`) that is matched if no dataset patterns apply. Only one user catch-all pattern is allowed. Multiple will raise a `DatasetError`.

3. **Default runtime patterns:**
Internal fallback behavior provided by Kedro. These patterns are built-in to catalog and automatically used at runtime to create datasets (e.g., `MemoryDatase`t or `SharedMemoryDataset`) when none of the above match.

### How resolution works in practice

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

**Default vs runtime behavior**

- Default behavior: `DataCatalog` resolves dataset patterns and user catch-all patterns only.
- Runtime behavior (e.g. during `kedro run`): Default runtime patterns are automatically enabled to resolve intermediate datasets not defined in `catalog.yml`.

```{note}
Enabling `fallback_to_runtime_pattern=True` is recommended only for advanced users with specific use cases. In most scenarios, Kedro handles it automatically during runtime.
```

### User facing API

The logic behind pattern resolution is handled by the internal `CatalogConfigResolver`, available as a property on the catalog (`catalog.config_resolver`).

Here are a few APIs might be useful for custom use-cases:

- `catalog_config_resolver.match_dataset_pattern()` - checks if the dataset name matches any dataset pattern
- `catalog_config_resolver.match_user_catch_all_pattern()` - checks if dataset name matches the user defined catch all pattern
- `catalog_config_resolver.match_runtime_pattern()` - checks if dataset name matches the default runtime pattern
- `catalog_config_resolver.resolve_pattern()` -  resolves a dataset name to its configuration based on patterns in the order explained above
- `catalog_config_resolver.list_patterns()` - lists all patterns available in the catalog
- `catalog_config_resolver.is_pattern()` - checks if a given string is a pattern

Refer to the method docstrings for more detailed examples and usage.

## Catalog and CLI commands

The new DataCatalog provides three powerful pipeline-based commands, accessible via both the CLI and interactive environment. These tools help inspect how datasets are resolved and managed within your pipeline.

**List datasets**

Lists all datasets used in the specified pipeline(s), grouped by how they are defined.

- datasets: Explicitly defined in catalog.yml
- factories: Resolved using dataset factory patterns
- defaults: Handled by user catch-all or default runtime patterns

CLI:
```bash
kedro catalog list-datasets -p data_processing
```

Interactive environment:
```bash
In [1]: catalog.list_datasets(pipelines=["data_processing", "data_science"])
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

```{note}
If no pipelines are specified, the `__default__` pipeline is used.
```

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

```{note}
If no pipelines are specified, the `__default__` pipeline is used.
```

### Implementation details and Python API usage

To ensure a consistent experience across the CLI, interactive environments (like IPython or Jupyter), and the Python API, we introduced pipeline-aware catalog commands using a mixin-based design.

At the core of this implementation is the `CatalogCommandsMixin` - a mixin class that extends the DataCatalog with additional methods for working with dataset factory patterns and pipeline-specific datasets.

**Why use a mixin?**
The goal was to keep pipeline logic decoupled from the core `DataCatalog`, while still providing seamless access to helpful methods utilizing pipelines.

This mixin approach allows these commands to be injected only when needed - avoiding unnecessary overhead in simpler catalog use cases.

**What This Means in Practice**
You don't need to do anything if:

- You're using Kedro via CLI, or
- Working inside an interactive environment (e.g. IPython, Jupyter Notebook).

Kedro automatically composes the catalog with `CatalogCommandsMixin` behind the scenes when initializing the session.

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

assert hasattr(catalog, "list_datasets")
print("list_datasets method is available!")
```

**Option 2: Subclass the catalog with the mixin**

```python
from kedro.io import DataCatalog, MemoryDataset
from kedro.framework.context import CatalogCommandsMixin

class DataCatalogWithMixins(DataCatalog, CatalogCommandsMixin):
    pass

catalog = DataCatalogWithMixins(datasets={"example": MemoryDataset()})

assert hasattr(catalog, "list_datasets")
print("list_datasets method is available!")
```

This design keeps your project flexible and modular, while offering a powerful set of pipeline-aware catalog inspection tools when you need them.

## Runners

The runners in Kedro have been simplified and made more consistent, especially around how pipeline outputs are handled and how parallel execution works.

1. Consistent `runner.run()` behavior
The `run()` method now always returns all pipeline outputs, regardless of how the catalog is set up. It returns only the dataset names, not the data itself. You still need to load the data from the catalog manually.
2. Support for `SharedMemoryDataCatalog` in `ParallelRunner`
`ParallelRunner` is now only compatible with `SharedMemoryDataCatalog`, a special catalog designed for multiprocessing.
This catalog:
     - Extends the standard `DataCatalog`
     - Ensures datasets are multiprocessing-safe
     - Supports inter-process communication by using shared memory
     - Manages synchronization and serialization of datasets across multiple processes

### What does it mean in practice

1. The output of `runner.run()` is now a list of dataset names that were produced by the pipeline.
To access the actual data, you must load it from the catalog:
```python
from kedro.framework.project import pipelines
from kedro.io import DataCatalog
from kedro.runner import SequentialRunner

# Assume this is loaded from your catalog.yml or similar
catalog_config = """
...
"""

catalog = DataCatalog.from_config(catalog_config)
default = pipelines.get("__default__")

runner = SequentialRunner()
result = runner.run(pipeline=default, catalog=catalog)

# Load actual data for outputs
for output_ds in result:
    data = catalog[output_ds].load()
```
This approach keeps the runner logic lightweight and consistent across execution modes.

2. Parallel execution requires `SharedMemoryDataCatalog`.
When using Kedro from the CLI (e.g., `kedro run`), the framework will automatically select the correct catalog type based on the runner.
```bash
# These just work out of the box
kedro run
kedro run -r ThreadRunner
kedro run -r ParallelRunner
```
However, if you're using the Python API, you need to explicitly use `SharedMemoryDataCatalog` when working with `ParallelRunner`:
```python
from kedro.framework.project import pipelines
from kedro.io import SharedMemoryDataCatalog
from kedro.runner import ParallelRunner

# Assume this is loaded from your catalog.yml or similar
catalog_config = """
...
"""

catalog = SharedMemoryDataCatalog.from_config(catalog_config)
default = pipelines.get("__default__")

runner = ParallelRunner()
result = runner.run(pipeline=default, catalog=catalog)

# Load actual data
for output_ds in result:
    data = catalog[output_ds].load()
```

**Summary**

- `runner.run()` always returns a list of dataset names - all pipeline outputs
- The actual dataset contents must be loaded manually from the catalog
- `ParallelRunner` requires the use of `SharedMemoryDataCatalog` for multiprocessing support
- When using `kedro run`, Kedro automatically selects the appropriate catalog
- When using the Python API, you must manually specify the correct catalog (`DataCatalog` or `SharedMemoryDataCatalog`) depending on the runner

## DataCatalog API
The new DataCatalog retains the core functionality of the previous version, with several enhancements to the API.

Below are the new and updated features, along with usage examples:

- [Accessing datasets](#how-to-access-datasets-in-the-catalog)
- [Adding datasets](#how-to-add-datasets-to-the-catalog)
- [Iterating through datasets](#how-to-iterate-trough-datasets-in-the-catalog)
- [Counting datasets](#how-to-get-the-number-of-datasets-in-the-catalog)
- [Printing the catalog](#how-to-print-the-full-catalog-and-individual-datasets)
- [Accessing dataset patterns](#how-to-access-dataset-patterns)
- [Saving catalog to config](#how-to-save-catalog-to-config)
- [Filtering datasets](#how-to-filter-catalog-datasets)
- [Getting dataset type](#how-to-get-dataset-type)

### How to access datasets in the catalog

You can check whether a dataset exists using the `in` operator (`__contains__` method):

```python
catalog = DataCatalog(datasets={"example": MemoryDataset()})
"example" in catalog  # True
"nonexistent" in catalog  # False
```

This checks if:

- The dataset is explicitly defined,
- It matches a dataset_pattern or user_catch_all_pattern.

To retrieve datasets, use standard dictionary-style access or the `.get()` method:

```python
reviews_ds = catalog["reviews"]
intermediate_ds = catalog.get("intermediate_ds", fallback_to_runtime_pattern=True)
```

- Both methods retrieve a dataset by name from the catalog’s internal collection.
- If the dataset isn’t materialized but matches a configured pattern, it's instantiated and returned.
- The `.get()` method accepts:
  - `fallback_to_runtime_pattern` (bool): If True, unresolved names fallback to `MemoryDataset` or `SharedMemoryDataset` (in `SharedMemoryDataCatalog`).
  - `version`: Specify dataset version if versioning is enabled.
- If no match is found and fallback is disabled, a `DatasetNotFoundError` is raised.

### How to add datasets to the catalog

The new API allows you to add datasets as well as raw data directly to the catalog:

```python
from kedro_datasets.pandas import CSVDataset

bikes_ds = CSVDataset(filepath="../data/01_raw/bikes.csv")
catalog["bikes"] = bikes_ds  # Add dataset instance

catalog["cars"] = ["Ferrari", "Audi"]  # Add raw data
```
When raw data is added, it's automatically wrapped in a `MemoryDataset`.

### How to iterate trough datasets in the catalog

`DataCatalog` supports iteration over dataset names (keys), datasets (values), and both (items). Iteration defaults to dataset names, similar to standard Python dictionaries:

```python
for ds_name in catalog:  # Default iteration over keys
    pass

for ds_name in catalog.keys():  # Iterate over dataset names
    pass

for ds in catalog.values():  # Iterate over dataset instances
    pass

for ds_name, ds in catalog.items():  # Iterate over (name, dataset) tuples
    pass
```

### How to get the number of datasets in the catalog

Use Python’s built-in `len()` function:

```python
ds_count = len(catalog)
```

### How to print the full catalog and individual datasets

To print the catalog or an individual dataset programmatically, use the `print()` function or in an interactive environment like IPython or JupyterLab, simply enter the variable:

```bash
In [1]: catalog
Out[1]: {'shuttles': kedro_datasets.pandas.excel_dataset.ExcelDataset(filepath=PurePosixPath('/data/01_raw/shuttles.xlsx'), protocol='file', load_args={'engine': 'openpyxl'}, save_args={'index': False}, writer_args={'engine': 'openpyxl'}), 'preprocessed_companies': kedro_datasets.pandas.parquet_dataset.ParquetDataset(filepath=PurePosixPath('/data/02_intermediate/preprocessed_companies.pq'), protocol='file', load_args={}, save_args={}), 'params:model_options.test_size': kedro.io.memory_dataset.MemoryDataset(data='<float>'), 'params:model_options.features': kedro.io.memory_dataset.MemoryDataset(data='<list>'))}

In [2]: catalog["shuttles"]
Out[2]: kedro_datasets.pandas.excel_dataset.ExcelDataset(filepath=PurePosixPath('/data/01_raw/shuttles.xlsx'), protocol='file', load_args={'engine': 'openpyxl'}, save_args={'index': False}, writer_args={'engine': 'openpyxl'})
```

### How to access dataset patterns

The pattern resolution logic in `DataCatalog` is handled by the `config_resolver`, which can be accessed as a property of the catalog:

```python
config_resolver = catalog.config_resolver
ds_config = catalog.config_resolver.resolve_pattern(ds_name)  # Resolve specific pattern
patterns = catalog.config_resolver.list_patterns() # List all patterns
```

```{note}
`DataCatalog` does not support all dictionary methods, such as `pop()`, `popitem()`, or `del`.
```

### How to save catalog to config

You can serialize a `DataCatalog` into configuration format (e.g., for saving to a YAML file) using `.to_config()`:

```python
from kedro.io import DataCatalog
from kedro_datasets.pandas import CSVDataset

cars = CSVDataset(
     filepath="cars.csv",
     save_args={"index": False}
 )
catalog = DataCatalog(datasets={'cars': cars})

config, credentials, load_versions, save_version = catalog.to_config()
```

To reconstruct the catalog later:
```python
new_catalog = DataCatalog.from_config(config, credentials, load_versions, save_version)
```

```{note}
This method only works for datasets with static, serializable parameters. For example, you can serialize credentials passed as dictionaries, but not as actual credential objects (like `google.auth.credentials.Credentials)`.
In-memory datasets are excluded.
```

### How to filter catalog datasets

Use the `.filter()` method to retrieve dataset names that match specific criteria:

```python
import re
from kedro.io import MemoryDataset
from kedro_datasets.pandas import SQLQueryDataset

catalog.filter(name_regex="raw")  # Names containing 'raw'
catalog.filter(name_regex=re.compile("^model_"))  # Regex match (precompiled)
catalog.filter(type_regex="pandas.excel_dataset.ExcelDataset")  # Match by type string
catalog.filter(name_regex="train", type_regex="CSV")  # Name + type
catalog.filter(name_regex="data", by_type=SQLQueryDataset)  # Exact type match
catalog.filter(name_regex="data", by_type=[MemoryDataset, SQLQueryDataset])  # Multiple types
```

**Args:**

- name_regex: Dataset names to match (string or re.Pattern).
- type_regex: Match full class path of dataset types.
- by_type: Dataset class(es) to match using isinstance.

**Returns:**

- A list of matching dataset names.

### How to get dataset type
You can check the dataset type without materializing or adding it to the catalog:

```python
from kedro.io import DataCatalog, MemoryDataset

catalog = DataCatalog(datasets={"example": MemoryDataset()})
dataset_type = catalog.get_type("example")
print(dataset_type)  # kedro.io.memory_dataset.MemoryDataset
```

If the dataset is not present and no patterns match, the method raises:
```python
DatasetNotFoundError: Dataset 'nonexistent' not found in the catalog.
```

# Deprecated API

The following DataCatalog methods and CLI commands are deprecated and should no longer be used.
Where applicable, alternatives are suggested:

- `catalog._get_dataset()` – Internal method; no longer needed. Use catalog.get() instead.
- `catalog.add_all()` – Prefer explicit catalog construction or use catalog.add() if necessary.
- `catalog.add_feed_dict()` – Deprecated. Use dict-style assignment with `__setitem__()` instead (e.g., `catalog["my_dataset"] = ...`).
- `catalog.list()` – Replaced by `catalog.filter()`
- `catalog.shallow_copy()` – Removed due to internal catalog refactoring; no replacement needed.
- `kedro catalog create` – The CLI command for creating catalog entries has been removed.
