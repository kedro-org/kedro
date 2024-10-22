# Kedro Data Catalog
`KedroDataCatalog` retains the core functionality of `DataCatalog`, with a few API enhancements. This page highlights the new features and provides usage examples. For a comprehensive understanding, we recommend reviewing the existing `DataCatalog` documentation before exploring the additional functionality of `KedroDataCatalog`.

## How to make `KedroDataCatalog` default catalog for Kedro `run`

To set `KedroDataCatalog` as the default catalog for the `kedro run` command and other CLI commands, update your `settings.py` as follows:

```python
from kedro.io import KedroDataCatalog

DATA_CATALOG_CLASS = KedroDataCatalog
```

Once this change is made, you can run your Kedro project as usual.

For more information on `settings.py`, refer to the [Project settings documentation](../kedro_project_setup/settings.md).

## How to access dataset in the catalog

You can retrieve a dataset from the catalog using either the dictionary-like syntax or the `get` method:

```python
reviews_ds = catalog["reviews"]
reviews_ds = catalog.get("reviews", default=default_ds)
```

## How add dataset to the catalog

The new API allows you to add datasets as well as raw data directly to the catalog:

```python
from kedro_datasets.pandas import CSVDataset


bikes_ds = CSVDataset(filepath="../data/01_raw/bikes.csv")
catalog["bikes"] = bikes_ds  # Adding a dataset
catalog["cars"] = ["Ferrari", "Audi"]  # Adding raw data
```

When you add raw data, it is automatically wrapped in a `MemoryDataset` under the hood.

## How to iterate trough datasets in the catalog

`KedroDataCatalog` supports iteration over dataset names (keys), datasets (values), and both (items). Iteration defaults to dataset names, similar to standard Python dictionaries:

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

## How to get the number of datasets in the catalog

You can get the number of datasets in the catalog using the `len()` function:

```python
ds_count = len(catalog)
```

## How to print catalog and dataset

To print the catalog or an individual dataset programmatically, use the `print()` function:

```python
print(catalog)

print(catalog["reviews"])
```

In an interactive environment like IPython or JupyterLab, simply entering the variable will display it:

```bash
catalog

catalog["reviews"]
```

## How to access dataset patterns

The pattern resolution logic in `KedroDataCatalog` is handled by the `config_resolver`, which can be accessed as a property of the catalog:

```python
config_resolver = catalog.config_resolver
ds_config = catalog.config_resolver.resolve_pattern(ds_name)  # Resolving a dataset pattern
patterns = catalog.config_resolver.list_patterns() # Listing all available patterns
```

```{note}
`KedroDataCatalog` does not support all dictionary-specific methods, such as `pop()`, `popitem()`, or deletion by key (`del`).
```

For a full list of supported methods, refer to the [KedroDataCatalog source code](https://github.com/kedro-org/kedro/blob/main/kedro/io/kedro_data_catalog.py).
