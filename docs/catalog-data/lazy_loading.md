# Lazy loading

From Kedro version **`0.19.10`** `DataCatalog` introduces a helper class called `_LazyDataset` to improve performance and optimise dataset loading.

## What is `_LazyDataset`?
`_LazyDataset` is a lightweight internal class that stores the configuration and versioning information of a dataset without instantiating it straight away. This allows the catalog to defer actual dataset creation (also called materialisation) until it is explicitly accessed.
This approach reduces startup overhead for large catalogs because it instantiates datasets when they are required.

## When is `_LazyDataset` used?
When you instantiate a `DataCatalog` from a config file (such as `catalog.yml`), Kedro doesn't instantly create all the underlying dataset objects. Instead, it wraps each dataset in a `_LazyDataset` and registers it in the catalog.
These placeholders are automatically materialised when a dataset is accessed for the first time-either directly or during pipeline execution.

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

# Accessing the dataset triggers materialisation.

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

## When is this useful?
This lazy loading mechanism is useful before runtime, during the warm-up phase of a pipeline. You can force materialisation of all datasets early on to:

- Catch configuration or import errors
- Validate external dependencies
- Ensure all datasets can be created before execution begins

Although `_LazyDataset` is not exposed to end users and doesn't affect your usual catalog usage, it is a useful concept to understand when debugging catalog behaviour or troubleshooting dataset instantiation issues.
