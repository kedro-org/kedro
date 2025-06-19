# Advanced: Access the Data Catalog in code

You can define a Data Catalog in two ways. Most use cases can be through a YAML configuration file as [illustrated previously](./data_catalog.md), but it is possible to access the Data Catalog programmatically through [kedro.io.DataCatalog][] using an API that allows you to configure data sources in code and use the IO module within notebooks.

!!! Warning
    Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
    From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.

This page contains a set of guides for advanced usage of the `DataCatalog` API in Kedro, including how to configure, access, manipulate, and persist datasets programmatically:

- [How to configure the Data Catalog](#how-to-configure-the-data-catalog)
- [How to access datasets in the catalog](#how-to-access-datasets-in-the-catalog)
- [How to add datasets to the catalog](#how-to-add-datasets-to-the-catalog)
- [How to iterate through datasets in the catalog](#how-to-iterate-trough-datasets-in-the-catalog)
- [How to get the number of datasets in the catalog](#how-to-get-the-number-of-datasets-in-the-catalog)
- [How to print the full catalog and individual datasets](#how-to-print-the-full-catalog-and-individual-datasets)
- [How to load datasets programmatically](#how-to-load-datasets-programmatically)
- [How to save data programmatically](#how-to-save-data-programmatically)
  - [How to save data to memory](#how-to-save-data-to-memory)
  - [How to save data to a SQL database for querying](#how-to-save-data-to-a-sql-database-for-querying)
  - [How to save data in Parquet](#how-to-save-data-in-parquet)
- [How to access a dataset with credentials](#how-to-access-a-dataset-with-credentials)
- [How to version a dataset using the Code API](#how-to-version-a-dataset-using-the-code-api)
- [How to save catalog to config](#how-to-save-catalog-to-config)
- [How to filter catalog datasets](#how-to-filter-catalog-datasets)
- [How to get dataset type](#how-to-get-dataset-type)

## How to configure the Data Catalog

To use the `DataCatalog` API, construct a `DataCatalog` object programmatically in a file like `catalog.py`.

In the following code, we use several pre-built data loaders documented in the [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/latest/).

```python
from kedro.io import DataCatalog
from kedro_datasets.pandas import (
    CSVDataset,
    SQLTableDataset,
    SQLQueryDataset,
    ParquetDataset,
)

catalog = DataCatalog(
    {
        "bikes": CSVDataset(filepath="../data/01_raw/bikes.csv"),
        "cars": CSVDataset(filepath="../data/01_raw/cars.csv", load_args=dict(sep=",")),
        "cars_table": SQLTableDataset(
            table_name="cars", credentials=dict(con="sqlite:///kedro.db")
        ),
        "scooters_query": SQLQueryDataset(
            sql="select * from cars where gear=4",
            credentials=dict(con="sqlite:///kedro.db"),
        ),
        "ranked": ParquetDataset(filepath="ranked.parquet"),
    }
)
```

When using `SQLTableDataset` or `SQLQueryDataset` you must provide a `con` key containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) database connection string. In the example above we pass it as part of `credentials` argument. Alternative to `credentials` is to put `con` into `load_args` and `save_args` (`SQLTableDataset` only).

## How to access datasets in the catalog

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

## How to add datasets to the catalog

`DataCatalog` API allows you to add datasets as well as raw data directly to the catalog:

```python
from kedro_datasets.pandas import CSVDataset

bikes_ds = CSVDataset(filepath="../data/01_raw/bikes.csv")
catalog["bikes"] = bikes_ds  # Add dataset instance

catalog["cars"] = ["Ferrari", "Audi"]  # Add raw data
```
When raw data is added, it's automatically wrapped in a `MemoryDataset`.

## How to iterate trough datasets in the catalog

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

## How to get the number of datasets in the catalog

Use Python’s built-in `len()` function:

```python
ds_count = len(catalog)
```

## How to print the full catalog and individual datasets

To print the catalog or an individual dataset programmatically, use the `print()` function or in an interactive environment like IPython or JupyterLab, simply enter the variable:

```bash
In [1]: catalog
Out[1]: {'shuttles': kedro_datasets.pandas.excel_dataset.ExcelDataset(filepath=PurePosixPath('/data/01_raw/shuttles.xlsx'), protocol='file', load_args={'engine': 'openpyxl'}, save_args={'index': False}, writer_args={'engine': 'openpyxl'}), 'preprocessed_companies': kedro_datasets.pandas.parquet_dataset.ParquetDataset(filepath=PurePosixPath('/data/02_intermediate/preprocessed_companies.pq'), protocol='file', load_args={}, save_args={}), 'params:model_options.test_size': kedro.io.memory_dataset.MemoryDataset(data='<float>'), 'params:model_options.features': kedro.io.memory_dataset.MemoryDataset(data='<list>'))}

In [2]: catalog["shuttles"]
Out[2]: kedro_datasets.pandas.excel_dataset.ExcelDataset(filepath=PurePosixPath('/data/01_raw/shuttles.xlsx'), protocol='file', load_args={'engine': 'openpyxl'}, save_args={'index': False}, writer_args={'engine': 'openpyxl'})
```

## How to load datasets programmatically

To access each dataset by its name:

```python
cars = catalog.load("cars")  # data is now loaded as a DataFrame in 'cars'
gear = cars["gear"].values
```

The following steps happened behind the scenes when `load` was called:

- The value `cars` was located in the Data Catalog
- The corresponding `AbstractDataset` object was retrieved
- The `load` method of this dataset was called
- This `load` method delegated the loading to the underlying pandas `read_csv` function

## How to save data programmatically

!!! warning "Memory Dataset Warning"
    This pattern is not recommended unless you are using platform notebook environments (Sagemaker, Databricks etc) or writing unit/integration tests for your Kedro pipeline. Use the YAML approach in preference.

### How to save data to memory

To save data using an API similar to that used to load data:

```python
from kedro.io import MemoryDataset

memory_ds = MemoryDataset(data=None)
catalog["cars_cache"] = memory_ds
catalog.save("cars_cache", "Memory can store anything.")
catalog.load("cars_cache")
```

### How to save data to a SQL database for querying

To put the data in a SQLite database:

```python
import os

# This cleans up the database in case it exists at this point
try:
    os.remove("kedro.db")
except FileNotFoundError:
    pass

catalog.save("cars_table", cars)

# rank scooters by their mpg
ranked = catalog.load("scooters_query")[["brand", "mpg"]]
```

### How to save data in Parquet

To save the processed data in Parquet format:

```python
catalog.save("ranked", ranked)
```

!!! warning "Null Value Warning"
    Saving `None` to a dataset is not allowed!

## How to access a dataset with credentials

Before instantiating the `DataCatalog`, Kedro will first attempt to read [the credentials from the project configuration](../configure/credentials.md). The resulting dictionary is then passed into `DataCatalog.from_config()` as the `credentials` argument.

Let's assume that the project contains the file `conf/local/credentials.yml` with the following contents:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: key
    aws_secret_access_key: secret

scooters_credentials:
  con: sqlite:///kedro.db

my_gcp_credentials:
  id_token: key
```

Your code will look as follows:

```python
CSVDataset(
    filepath="s3://test_bucket/data/02_intermediate/company/motorbikes.csv",
    load_args=dict(sep=",", skiprows=5, skipfooter=1, na_values=["#NA", "NA"]),
    credentials=dict(key="token", secret="key"),
)
```

## How to version a dataset using the Code API

In an earlier section of the documentation we described how [Kedro enables dataset and ML model versioning](./data_catalog.md/#dataset-versioning).

If you require programmatic control over load and save versions of a specific dataset, you can instantiate `Version` and pass it as a parameter to the dataset initialisation:

```python
from kedro.io import DataCatalog, Version
from kedro_datasets.pandas import CSVDataset
import pandas as pd

data1 = pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})
data2 = pd.DataFrame({"col1": [7], "col2": [8], "col3": [9]})
version = Version(
    load=None,  # load the latest available version
    save=None,  # generate save version automatically on each save operation
)

test_dataset = CSVDataset(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
catalog =  DataCatalog({"test_dataset": test_dataset})

# save the dataset to data/01_raw/test.csv/<version>/test.csv
catalog.save("test_dataset", data1)
# save the dataset into a new file data/01_raw/test.csv/<version>/test.csv
catalog.save("test_dataset", data2)

# load the latest version from data/test.csv/*/test.csv
reloaded = catalog.load("test_dataset")
assert data2.equals(reloaded)
```

In the example above, we do not fix any versions. The behaviour of load and save operations becomes slightly different when we set a version:


```python
version = Version(
    load="my_exact_version",  # load exact version
    save="my_exact_version",  # save to exact version
)

test_dataset = CSVDataset(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
catalog =  DataCatalog({"test_dataset": test_dataset})

# save the dataset to data/01_raw/test.csv/my_exact_version/test.csv
catalog.save("test_dataset", data1)
# load from data/01_raw/test.csv/my_exact_version/test.csv
reloaded = catalog.load("test_dataset")
assert data1.equals(reloaded)

# raises DatasetError since the path
# data/01_raw/test.csv/my_exact_version/test.csv already exists
catalog.save("test_dataset", data2)
```

We do not recommend passing exact load or save versions, since it might lead to inconsistencies between operations. For example, if versions for load and save operations do not match, a save operation would result in a `UserWarning`.

Imagine a simple pipeline with two nodes, where B takes the output from A. If you specify the load-version of the data for B to be `my_data_2023_08_16.csv`, the data that A produces (`my_data_20230818.csv`) is not used.

```text
Node_A -> my_data_20230818.csv
my_data_2023_08_16.csv -> Node B
```

In code:

```python
version = Version(
    load="my_data_2023_08_16.csv",  # load exact version
    save="my_data_20230818.csv",  # save to exact version
)

test_dataset = CSVDataset(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
catalog =  DataCatalog({"test_dataset": test_dataset})

catalog.save("test_dataset", data1)  # emits a UserWarning due to version inconsistency

# raises DatasetError since the data/01_raw/test.csv/exact_load_version/test.csv
# file does not exist
reloaded = catalog.load("test_dataset")

### How to access dataset patterns

The pattern resolution logic in `DataCatalog` is handled by the `config_resolver`, which can be accessed as a property of the catalog:

```python
config_resolver = catalog.config_resolver
ds_config = catalog.config_resolver.resolve_pattern(ds_name)  # Resolve specific pattern
patterns = catalog.config_resolver.list_patterns() # List all patterns
```

!!! note
    `DataCatalog` does not support all dictionary methods, such as `pop()`, `popitem()`, or `del`.

## How to save catalog to config

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

!!! note
    This method only works for datasets with static, serializable parameters. For example, you can serialize credentials passed as dictionaries, but not as actual credential objects (like `google.auth.credentials.Credentials)`. In-memory datasets are excluded.

## How to filter catalog datasets

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

## How to get dataset type
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
