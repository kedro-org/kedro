# Advanced: Access the Data Catalog in code

You can define a Data Catalog in two ways. Most use cases can be through a YAML configuration file as [illustrated previously](./data_catalog.md), but it is possible to access the Data Catalog programmatically through [`kedro.io.DataCatalog`](/kedro.io.DataCatalog) using an API that allows you to configure data sources in code and use the IO module within notebooks.

```{warning}
Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.
```

## How to configure the Data Catalog

To use the `DataCatalog` API, construct a `DataCatalog` object programmatically in a file like `catalog.py`.

In the following code, we use several pre-built data loaders documented in the [API reference documentation](/kedro_datasets).

```python
from kedro.io import DataCatalog
from kedro_datasets.pandas import (
    CSVDataset,
    SQLTableDataset,
    SQLQueryDataset,
    ParquetDataset,
)

io = DataCatalog(
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

## How to view the available data sources

To review the `DataCatalog`:

```python
io.list()
```

## How to load datasets programmatically

To access each dataset by its name:

```python
cars = io.load("cars")  # data is now loaded as a DataFrame in 'cars'
gear = cars["gear"].values
```

The following steps happened behind the scenes when `load` was called:

- The value `cars` was located in the Data Catalog
- The corresponding `AbstractDataset` object was retrieved
- The `load` method of this dataset was called
- This `load` method delegated the loading to the underlying pandas `read_csv` function

## How to save data programmatically

```{warning}
This pattern is not recommended unless you are using platform notebook environments (Sagemaker, Databricks etc) or writing unit/integration tests for your Kedro pipeline. Use the YAML approach in preference.
```

### How to save data to memory

To save data using an API similar to that used to load data:

```python
from kedro.io import MemoryDataset

memory = MemoryDataset(data=None)
io.add("cars_cache", memory)
io.save("cars_cache", "Memory can store anything.")
io.load("cars_cache")
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

io.save("cars_table", cars)

# rank scooters by their mpg
ranked = io.load("scooters_query")[["brand", "mpg"]]
```

### How to save data in Parquet

To save the processed data in Parquet format:

```python
io.save("ranked", ranked)
```

```{warning}
Saving `None` to a dataset is not allowed!
```

## How to access a dataset with credentials
Before instantiating the `DataCatalog`, Kedro will first attempt to read [the credentials from the project configuration](../configuration/credentials.md). The resulting dictionary is then passed into `DataCatalog.from_config()` as the `credentials` argument.

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
io = DataCatalog({"test_dataset": test_dataset})

# save the dataset to data/01_raw/test.csv/<version>/test.csv
io.save("test_dataset", data1)
# save the dataset into a new file data/01_raw/test.csv/<version>/test.csv
io.save("test_dataset", data2)

# load the latest version from data/test.csv/*/test.csv
reloaded = io.load("test_dataset")
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
io = DataCatalog({"test_dataset": test_dataset})

# save the dataset to data/01_raw/test.csv/my_exact_version/test.csv
io.save("test_dataset", data1)
# load from data/01_raw/test.csv/my_exact_version/test.csv
reloaded = io.load("test_dataset")
assert data1.equals(reloaded)

# raises DatasetError since the path
# data/01_raw/test.csv/my_exact_version/test.csv already exists
io.save("test_dataset", data2)
```

We do not recommend passing exact load and/or save versions, since it might lead to inconsistencies between operations. For example, if versions for load and save operations do not match, a save operation would result in a `UserWarning`.

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
io = DataCatalog({"test_dataset": test_dataset})

io.save("test_dataset", data1)  # emits a UserWarning due to version inconsistency

# raises DatasetError since the data/01_raw/test.csv/exact_load_version/test.csv
# file does not exist
reloaded = io.load("test_dataset")
```
