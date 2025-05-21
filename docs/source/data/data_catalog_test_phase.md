# Goal

Before the release of `DataCatalog` version 1.0, we aim to validate its usability, functionality, and effectiveness through user testing. The primary objectives are to identify what works well, detect any pain points, and determine necessary adjustments before the final release.

This page provides the installation guide, highlights testing scenarios and new/updated/deprecated features with usage examples:
* [Installation](#installation)
* [Suggested testing scenarios](#suggested-testing-scenarios)
* [Catalog API and related components updates](#catalog-api-and-related-components-updates)
  * [DataCatalog API](#datacatalog-api)
  * [Lazy loading](#lazy-loading)
  * [Dataset factories](#dataset-factories)
  * [Catalog and CLI commands](#catalog-and-cli-commands)
  * [Runners](#runners)
  * [Deprecated API](#deprecated-api)

# Installation

Install from feature-1.0.0 branch
Uninstall telemetry and install from the main branch
Install kedro-viz if needed
```console
pip install git+https://github.com/kedro-org/kedro-viz.git@chore/compat-dc#subdirectory=package
```

# Suggested testing scenarios

Test via kedro run, Python API, ipython and jupyter notebook.

Dict-like Interface

Accessing datasets and data.
Iterating over datasets.
Pattern Resolution Testing

Loading datasets from the catalog, checking the dataset presence in the catalog.
Resolving pattern configurations (dataset-specific, default, runtime).
Redefining runtime patterns.
Filtering

Filter dataset names in the catalog based on name/type.
Configuration

Convert KedroDataCatalog instance into a configuration format (to_config).
Loading catalog from saves config
Hooks

Utilize catalog-related hooks (e.g., after_catalog_created).
Pipeline Execution

Run pipelines with different execution runners (kedro run, Python API).
Validate runner.run() / session.run() outputs.
CLI & API Testing

Test new CLI commands (interactive environment + Python API usage).
Attempt creating a new catalog and running it (kedro run, Python API).
Versioning

Test versioning functionality works as expected
User-Focused Testing

Allow users to interact with the catalog as they would in real-world projects.

# Catalog API and related components updates

## DataCatalog API
New `DataCatalog` retains the core functionality of `DataCatalog`, with a few API enhancements.

This page highlights the new features and provides usage examples:
* [How to access datasets in the catalog](#how-to-access-datasets-in-the-catalog)
* [How to add datasets to the catalog](#how-to-add-datasets-to-the-catalog)
* [How to iterate trough datasets in the catalog](#how-to-iterate-trough-datasets-in-the-catalog)
* [How to get the number of datasets in the catalog](#how-to-get-the-number-of-datasets-in-the-catalog)
* [How to print the full catalog and individual datasets](#how-to-print-the-full-catalog-and-individual-datasets)
* [How to access dataset patterns](#how-to-access-dataset-patterns)

### How to access datasets in the catalog

You can retrieve a dataset from the catalog using either the dictionary-like syntax or the `get` method:

```python
reviews_ds = catalog["reviews"]
reviews_ds = catalog.get("reviews", default=default_ds)
```

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

# Lazy loading
Explain the logic and give a few examples

# Dataset factories
Explain resolution logic

# Catalog and CLI commands
list_datasets
list_patterns
resolve_patterns

# Runners
Run method output
SharedMemoryDataCatalog

# Deprecated API

Create catalog CLI command
