# Kedro Data Catalog

Since `KedroDataCatalog` repeats `DataCatalog` functionality we will only highlight new API and provide usage examples at this page.
The rest examples provided for `DataCatalog` previously are relevant for `KedroDataCatalog`, thus we recommend first make yourself familiar with them and then start using new catalog.

## How to make `KedroDataCatalog` default catalog for Kedro `run`

To make `KedroDataCatalog` default catalog for Kedro `run` and other CLI commands modify your `settings.py` as follows:

```python
from kedro.io import KedroDataCatalog

DATA_CATALOG_CLASS = KedroDataCatalog
```

Then run your Kedro project as usual.

For more details about `settings.py` see [Project settings page](../kedro_project_setup/settings.md)

## How to access dataset in the catalog

```python
reviews_ds = catalog["reviews"]
reviews_ds = catalog.get("reviews", default=default_ds)
```

## How add dataset to the catalog

New API allows adding both datasets and raw data as follows:

```python
from kedro_datasets.pandas import CSVDataset


bikes_ds = CSVDataset(filepath="../data/01_raw/bikes.csv")
catalog["bikes"] = bikes_ds  # Set dataset
catalog["cars"] = ["Ferrari", "Audi"]  # Set raw data
```

Under the hood raw data is added as `MemoryDataset` to the catalog.

## How to iterate trough datasets in the catalog

`KedroDataCatalog` allows iterating through keys - dataset names, values - datasets and items - tuples `(dataset_name, dataset)`. The default iteration is happening through keys as ir is done for dictionary.

```python

for ds_name in catalog:  # __iter__
    pass

for ds_name in catalog.keys():  # keys()
    pass

for ds in catalog.values():  # values()
    pass

for ds_name, ds in catalog.items():  # items()
    pass
```

## How to get the number of datasets in the catalog

```python
ds_count = len(catalog)
```

## How to print catalog and dataset

To print catalog or dataset programmatically:

```python
print(catalog)

print(catalog["reviews"])
```

To print catalog or dataset in the interactive environment (IPython, JupyterLab and other Jupyter clients):

```bash
catalog

catalog["reviews"]
```

## How to access dataset patterns

Patterns resolution logic is now encapsulated to the `config_resolver` which is available as a catalog's property:

```python
config_resolver = catalog.config_resolver
ds_config = catalog.config_resolver.resolve_pattern(ds_name)  # resolve dataset patterns
patterns = catalog.config_resolver.list_patterns() # list al patterns available in the catalog
```

```{note}
`KedroDataCatalog` do not support all dict-specific functionality like pop(), popitem(), del by key.
```

For the full set of supported methods please refer to the [KedroDataCatalog source code](https://github.com/kedro-org/kedro/blob/main/kedro/io/kedro_data_catalog.py)
