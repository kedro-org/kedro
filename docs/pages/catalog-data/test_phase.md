# Goal

Before the release of `DataCatalog` version 1.0, we aim to validate its usability, functionality, and effectiveness through user testing. The primary objectives are to identify what works well, detect any pain points, and determine necessary adjustments before the final release.

This page provides the installation guide, highlights testing scenarios and new/updated/deprecated features with usage examples:
* [Installation](#installation)
* [Suggested testing scenarios](#suggested-testing-scenarios)
* [Catalog API and related components updates](#catalog-api-and-related-components-updates)
  * [Lazy loading](#lazy-loading)
  * [Dataset factories](#dataset-factories)
  * [Catalog and CLI commands](#catalog-and-cli-commands)
  * [Runners](#runners)
  * [DataCatalog API](#datacatalog-api)
  * [Deprecated API](#deprecated-api)

# Installation

1. Install `kedro` from `feature-1.0.0` branch
```console
git clone https://github.com/kedro-org/kedro.git
git fetch origin feature-1.0.0
git checkout feature-1.0.0
pip install .
```
2. Install kedro-viz (not require but maybe helpful for testing)
You will need a different `kedro-viz` build compatible with the new catalog:
```console
pip install git+https://github.com/kedro-org/kedro-viz.git@chore/compat-dc#subdirectory=package
```

# Suggested testing scenarios

Here we are suggesting a few testing scenarios but our main focus is let to users to interact with the catalog as they would in real-world projects and try their own scenarios.

Please test them via kedro run, Python API, ipython and jupyter notebook when possible.

1. Catalog API
Accessing datasets and data.
Loading/saving datasets.
Iterating over datasets.
Checking the dataset presence in the catalog.
Filter dataset names in the catalog based on name/type.
Access dataset type.

2. Pattern Resolution Testing
Resolving pattern configurations (dataset-specific, user catch-all, runtime).
Redefining runtime patterns.

3. Catalog serialization/deserialization
Convert KedroDataCatalog instance into a configuration format (to_config).
Loading catalog from saves config

4. Hooks
Utilize catalog-related hooks (e.g., after_catalog_created).

5. Pipeline Execution
Run pipelines with different execution runners (kedro run, Python API).
Validate runner.run() / session.run() outputs.

6. CLI Testing
Test new CLI commands (interactive environment + Python API usage).

7. Versioning
Test versioning functionality works as expected

8. User-Focused Testing
Interact with the catalog as you would in real-world for your projects.

# Catalog API and related components updates

## Lazy loading
Explain the logic and give a few examples

## Dataset factories
Explain resolution logic

## Catalog and CLI commands
list_datasets
list_patterns
resolve_patterns

## Runners
Run method output
SharedMemoryDataCatalog

## DataCatalog API
New `DataCatalog` retains most of the core functionality of old `DataCatalog`, with a few API enhancements.

Here are the new and updated features and with the usage examples:
* [How to access datasets in the catalog](#how-to-access-datasets-in-the-catalog)
* [How to add datasets to the catalog](#how-to-add-datasets-to-the-catalog)
* [How to iterate trough datasets in the catalog](#how-to-iterate-trough-datasets-in-the-catalog)
* [How to get the number of datasets in the catalog](#how-to-get-the-number-of-datasets-in-the-catalog)
* [How to print the full catalog and individual datasets](#how-to-print-the-full-catalog-and-individual-datasets)
* [How to access dataset patterns](#how-to-access-dataset-patterns)
* [How to save catalog to config](#how-to-save-catalog-to-config)
* [How to filter catalog datasets](#how-to-filter-catalog-datasets)
* [How to get dataset type](#how-to-get-dataset-type)

### How to access datasets in the catalog

You can check if dataset is in catalog using `__contains__` method. It returns True if a dataset is registered in the catalog
or matches a dataset/user catch all pattern.

```console
>>> catalog = DataCatalog(datasets={"example": MemoryDataset()})
>>> "example" in catalog
True
>>> "nonexistent" in catalog
False
```

You can retrieve a dataset from the catalog using either the dictionary-like syntax or the `get` method:

```python
reviews_ds = catalog["reviews"]
intermediate_ds = catalog.get("intermediate_ds", fallback_to_runtime_pattern=True)
```

Both methods allow you to get a dataset by name from an internal collection of datasets.

If a dataset is not materialized but matches dataset_pattern or user_catch_all_pattern it is instantiated and added to the catalog first, then returned. In

`get()` method also allows to enable `fallback_to_runtime_pattern` option and provide `version` argument.
If `fallback_to_runtime_pattern` is enabled catalog `runtime_pattern` will be used to resolve a dataset.
That means that in case the above conditions are not met `DataCatalog` will fall back to `MemoryDataset` and `SharedMemoryDataCatalog` to `SharedMemoryDataset`.

When the dataset in not in the internal collection, does not match dataset_pattern or user_catch_all_pattern and `fallback_to_runtime_pattern` is set to `False`
`DatasetNotFoundError` is raised.

### How to add datasets to the catalog

The new API allows you to add datasets as well as raw data directly to the catalog:

```python
from kedro_datasets.pandas import CSVDataset

bikes_ds = CSVDataset(filepath="../data/01_raw/bikes.csv")
catalog["bikes"] = bikes_ds  # Adding a dataset
catalog["cars"] = ["Ferrari", "Audi"]  # Adding raw data
```

When you add raw data, it is automatically wrapped in a `MemoryDataset` under the hood.

### How to iterate trough datasets in the catalog

`DataCatalog` supports iteration over dataset names (keys), datasets (values), and both (items). Iteration defaults to dataset names, similar to standard Python dictionaries:

```python
for ds_name in catalog:  # __iter__ defaults to keys
    pass

for ds_name in catalog.keys():  # Iterate over dataset names
    pass

for ds in catalog.values():  # Iterate over datasets
    pass

for ds_name, ds in catalog.items():  # Iterate over (name, dataset) tuples
    pass
```

### How to get the number of datasets in the catalog

You can get the number of datasets in the catalog using the `len()` function:

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
ds_config = catalog.config_resolver.resolve_pattern(ds_name)  # Resolving a dataset pattern
patterns = catalog.config_resolver.list_patterns() # Listing all available patterns
```

```{note}
`DataCatalog` does not support all dictionary-specific methods, such as `pop()`, `popitem()`, or deletion by key (`del`).
```

### How to save catalog to config

Converts the `DataCatalog` instance into a configuration format suitable for
        serialization. This includes datasets, credentials, and versioning information.

        This method is only applicable to catalogs that contain datasets initialized with static, primitive
        parameters. For example, it will work fine if one passes credentials as dictionary to
        `GBQQueryDataset` but not as `google.auth.credentials.Credentials` object.

        Returns:
            A tuple containing:
                catalog: A dictionary mapping dataset names to their unresolved configurations,
                    excluding in-memory datasets.

                credentials: A dictionary of unresolved credentials extracted from dataset configurations.

                load_versions: A dictionary mapping dataset names to specific versions to be loaded,
                    or `None` if no version is set.

                save_version: A global version identifier for saving datasets, or `None` if not specified.

```python
from kedro.io import DataCatalog
from kedro_datasets.pandas import CSVDataset

cars = CSVDataset(
     filepath="cars.csv",
     load_args=None,
     save_args={"index": False}
 )
catalog = DataCatalog(datasets={'cars': cars})

config, credentials, load_versions, save_version = catalog.to_config()

new_catalog = DataCatalog.from_config(config, credentials, load_versions, save_version)
```

### How to filter catalog datasets

`filter()` allows filtering dataset names registered in the catalog based on name and/or type.

        This method allows filtering datasets by their names and/or types. Regular expressions
        should be precompiled before passing them to `name_regex` or `type_regex`, but plain
        strings are also supported.

        Args:
            name_regex: Optional compiled regex pattern or string to filter dataset names.
            type_regex: Optional compiled regex pattern or string to filter dataset types.
                The provided regex is matched against the full dataset type path, for example:
                `kedro_datasets.pandas.parquet_dataset.ParquetDataset`.
            by_type: Optional dataset type(s) to filter by. This performs an instance type check
                rather than a regex match. It can be a single dataset type or a list of types.

        Returns:
            A list of dataset names that match the filtering criteria.

```python
 import re
catalog = DataCatalog()
# get datasets where the substring 'raw' is present
raw_data = catalog.filter(name_regex='raw')
# get datasets where names start with 'model_' (precompiled regex)
model_datasets = catalog.filter(name_regex=re.compile('^model_'))
# get datasets of a specific type using type_regex
csv_datasets = catalog.filter(type_regex='pandas.excel_dataset.ExcelDataset')
# get datasets where names contain 'train' and type matches 'CSV' in the path
catalog.filter(name_regex="train", type_regex="CSV")
# get datasets where names include 'data' and are of a specific type
from kedro_datasets.pandas import SQLQueryDataset
catalog.filter(name_regex="data", by_type=SQLQueryDataset)
# get datasets where names include 'data' and are of multiple specific types
from kedro.io import MemoryDataset
catalog.filter(name_regex="data", by_type=[MemoryDataset, SQLQueryDataset])
```

### How to get dataset type
Access dataset type without adding resolved dataset to the catalog.

        Args:
            ds_name: The name of the dataset whose type is to be retrieved.

        Returns:
            The fully qualified type of the dataset (e.g., `kedro.io.memory_dataset.MemoryDataset`).

        Raises:
            DatasetNotFoundError: When the dataset in not in the internal collection, does not match
                dataset_patterns or user_catch_all_pattern.

```python
from kedro.io import DataCatalog, MemoryDataset
catalog = DataCatalog(datasets={"example": MemoryDataset()})
dataset_type = catalog.get_type("example")
print(dataset_type)
            # kedro.io.memory_dataset.MemoryDataset

missing_type = catalog.get_type("nonexistent")
Raises DatasetNotFoundError: Dataset 'nonexistent' not found in the catalog.
```

# Deprecated API

catalog.list()
Create catalog CLI command
