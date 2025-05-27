# Goal

Before the release of `DataCatalog` version 1.0, we aim to validate its usability, functionality, and effectiveness through user testing. Our objectives are to:

- Identify what works well
- Uncover pain points
- Determine improvements needed before the final release

This document includes installation instructions, suggested testing scenarios, and an overview of new, updated, and deprecated features, with usage examples:
* [Installation](#installation)
* [Suggested Testing Scenarios](#suggested-testing-scenarios)
* [Catalog API and related Updates](#catalog-api-and-related-updates)
  * [Lazy Loading](#lazy-loading)
  * [Dataset Factories](#dataset-factories)
  * [Catalog and CLI commands](#catalog-and-cli-commands)
  * [Runners](#runners)
  * [DataCatalog API](#datacatalog-api)
  * [Deprecated API](#deprecated-api)

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
- Test pattern resolution (dataset-specific, user catch-all, runtime-defined)
- Override patterns at runtime

3. Catalog Serialization
- Convert a KedroDataCatalog instance to config (`to_config`)
- Load a catalog from a saved config

4. Hooks
- Trigger and validate catalog-related hooks (e.g., `after_catalog_created`)

5. Pipeline Execution
- Run pipelines using different runners:
  - `kedro run`
  - Python API (runner.run() / session.run())
- Validate runner outputs

6. CLI Features
- Test new catalo CLI commands
- Try both interactive and scripted usage

7. Versioning
- Validate dataset versioning functionality

8. Real-World Scenarios
Use the catalog as you would in a production project

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
The new DataCatalog retains the core functionality of the previous version, with several enhancements to the API.

Below are the new and updated features, along with usage examples:
* [Accessing datasets](#how-to-access-datasets-in-the-catalog)
* [Adding datasets](#how-to-add-datasets-to-the-catalog)
* [Iterating through datasets](#how-to-iterate-trough-datasets-in-the-catalog)
* [Counting datasets](#how-to-get-the-number-of-datasets-in-the-catalog)
* [Printing the catalog](#how-to-print-the-full-catalog-and-individual-datasets)
* [Accessing dataset patterns](#how-to-access-dataset-patterns)
* [Saving catalog to config](#how-to-save-catalog-to-config)
* [Filtering datasets](#how-to-filter-catalog-datasets)
* [Getting dataset type](#how-to-get-dataset-type)

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
`DataCatalog` does **not** support all dictionary methods, such as `pop()`, `popitem()`, or `del`.
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

**Note:** This method only works for datasets with static, serializable parameters.
For example, you can serialize credentials passed as dictionaries, but not as actual credential objects (like `google.auth.credentials.Credentials)`.
In-memory datasets are excluded.


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

catalog.list()
Create catalog CLI command
