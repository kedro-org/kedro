# Advanced Data Catalog usage

## How to read the same file using two different dataset implementations

When you want to load and save the same file, via its specified `filepath`, using different `DataSet` implementations, you'll need to use transcoding.

### A typical example of transcoding

For instance, parquet files can not only be loaded via the `ParquetDataSet` using `pandas`, but also directly by `SparkDataSet`. This conversion is typical when coordinating a `Spark` to `pandas` workflow.

To enable transcoding, define two `DataCatalog` entries for the same dataset in a common format (Parquet, JSON, CSV, etc.) in your `conf/base/catalog.yml`:

```yaml
my_dataframe@spark:
  type: spark.SparkDataSet
  filepath: data/02_intermediate/data.parquet
  file_format: parquet

my_dataframe@pandas:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/data.parquet
```

These entries are used in the pipeline like this:

```python
pipeline(
    [
        node(func=my_func1, inputs="spark_input", outputs="my_dataframe@spark"),
        node(func=my_func2, inputs="my_dataframe@pandas", outputs="pipeline_output"),
    ]
)
```

### How does transcoding work?

In this example, Kedro understands that `my_dataframe` is the same dataset in its `spark.SparkDataSet` and `pandas.ParquetDataSet` formats and helps resolve the node execution order.

In the pipeline, Kedro uses the `spark.SparkDataSet` implementation for saving and `pandas.ParquetDataSet`
for loading, so the first node should output a `pyspark.sql.DataFrame`, while the second node would receive a `pandas.Dataframe`.


## Access the Data Catalog in code

TO REMOVE -- Diataxis: How to

You can define a Data Catalog in two ways - through YAML configuration, or programmatically using an API.

The code API allows you to:

* configure data sources in code
* operate the IO module within notebooks

### Configure a Data Catalog

In a file like `catalog.py`, you can construct a `DataCatalog` object programmatically. In the following, we are using several pre-built data loaders documented in the [API reference documentation](/kedro_datasets).

```python
from kedro.io import DataCatalog
from kedro_datasets.pandas import (
    CSVDataSet,
    SQLTableDataSet,
    SQLQueryDataSet,
    ParquetDataSet,
)

io = DataCatalog(
    {
        "bikes": CSVDataSet(filepath="../data/01_raw/bikes.csv"),
        "cars": CSVDataSet(filepath="../data/01_raw/cars.csv", load_args=dict(sep=",")),
        "cars_table": SQLTableDataSet(
            table_name="cars", credentials=dict(con="sqlite:///kedro.db")
        ),
        "scooters_query": SQLQueryDataSet(
            sql="select * from cars where gear=4",
            credentials=dict(con="sqlite:///kedro.db"),
        ),
        "ranked": ParquetDataSet(filepath="ranked.parquet"),
    }
)
```

When using `SQLTableDataSet` or `SQLQueryDataSet` you must provide a `con` key containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) database connection string. In the example above we pass it as part of `credentials` argument. Alternative to `credentials` is to put `con` into `load_args` and `save_args` (`SQLTableDataSet` only).

### Load datasets

You can access each dataset by its name.

```python
cars = io.load("cars")  # data is now loaded as a DataFrame in 'cars'
gear = cars["gear"].values
```

#### Behind the scenes

The following steps happened behind the scenes when `load` was called:

- The value `cars` was located in the Data Catalog
- The corresponding `AbstractDataSet` object was retrieved
- The `load` method of this dataset was called
- This `load` method delegated the loading to the underlying pandas `read_csv` function

### View the available data sources

If you forget what data was assigned, you can always review the `DataCatalog`.

```python
io.list()
```

### Save data

You can save data using an API similar to that used to load data.

```{warning}
This use is not recommended unless you are prototyping in notebooks.
```

#### Save data to memory

```python
from kedro.io import MemoryDataSet

memory = MemoryDataSet(data=None)
io.add("cars_cache", memory)
io.save("cars_cache", "Memory can store anything.")
io.load("cars_cache")
```

#### Save data to a SQL database for querying

We might now want to put the data in a SQLite database to run queries on it. Let's use that to rank scooters by their mpg.

```python
import os

# This cleans up the database in case it exists at this point
try:
    os.remove("kedro.db")
except FileNotFoundError:
    pass

io.save("cars_table", cars)
ranked = io.load("scooters_query")[["brand", "mpg"]]
```

#### Save data in Parquet

Finally, we can save the processed data in Parquet format.

```python
io.save("ranked", ranked)
```

```{warning}
Saving `None` to a dataset is not allowed!
```

### Accessing a dataset that needs credentials
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
CSVDataSet(
    filepath="s3://test_bucket/data/02_intermediate/company/motorbikes.csv",
    load_args=dict(sep=",", skiprows=5, skipfooter=1, na_values=["#NA", "NA"]),
    credentials=dict(key="token", secret="key"),
)
```

### Versioning using the Code API

In order to do that, pass a dictionary with exact load versions to `DataCatalog.from_config`:

```python
load_versions = {"cars": "2019-02-13T14.35.36.518Z"}
io = DataCatalog.from_config(catalog_config, credentials, load_versions=load_versions)
cars = io.load("cars")
```

The last row in the example above would attempt to load a CSV file from `data/01_raw/company/car_data.csv/2019-02-13T14.35.36.518Z/car_data.csv`:

* `load_versions` configuration has an effect only if a dataset versioning has been enabled in the catalog config file - see the example above.

* We recommend that you do not override `save_version` argument in `DataCatalog.from_config` unless strongly required to do so, since it may lead to inconsistencies between loaded and saved versions of the versioned datasets.

```{warning}
The `DataCatalog` does not re-generate save versions between instantiations. Therefore, if you call `catalog.save('cars', some_data)` twice, then the second call will fail, since it tries to overwrite a versioned dataset using the same save version. To mitigate this, reload your data catalog by calling `%reload_kedro` line magic. This limitation does not apply to `load` operation.
```

**** HOW DOES THE BELOW FIT WITH THE ABOVE??

Should you require more control over load and save versions of a specific dataset, you can instantiate `Version` and pass it as a parameter to the dataset initialisation:

```python
from kedro.io import DataCatalog, Version
from kedro_datasets.pandas import CSVDataSet
import pandas as pd

data1 = pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})
data2 = pd.DataFrame({"col1": [7], "col2": [8], "col3": [9]})
version = Version(
    load=None,  # load the latest available version
    save=None,  # generate save version automatically on each save operation
)

test_data_set = CSVDataSet(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
io = DataCatalog({"test_data_set": test_data_set})

# save the dataset to data/01_raw/test.csv/<version>/test.csv
io.save("test_data_set", data1)
# save the dataset into a new file data/01_raw/test.csv/<version>/test.csv
io.save("test_data_set", data2)

# load the latest version from data/test.csv/*/test.csv
reloaded = io.load("test_data_set")
assert data2.equals(reloaded)
```

```{note}
In the example above, we did not fix any versions. If we do, then the behaviour of load and save operations becomes slightly different:
```

```python
version = Version(
    load="my_exact_version",  # load exact version
    save="my_exact_version",  # save to exact version
)

test_data_set = CSVDataSet(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
io = DataCatalog({"test_data_set": test_data_set})

# save the dataset to data/01_raw/test.csv/my_exact_version/test.csv
io.save("test_data_set", data1)
# load from data/01_raw/test.csv/my_exact_version/test.csv
reloaded = io.load("test_data_set")
assert data1.equals(reloaded)

# raises DataSetError since the path
# data/01_raw/test.csv/my_exact_version/test.csv already exists
io.save("test_data_set", data2)
```

```{warning}
We do not recommend passing exact load and/or save versions, since it might lead to inconsistencies between operations. For example, if versions for load and save operations do not match, a save operation would result in a `UserWarning` indicating that save and load versions do not match. Load after save might also return an error if the corresponding load version is not found:
```

```python
version = Version(
    load="exact_load_version",  # load exact version
    save="exact_save_version",  # save to exact version
)

test_data_set = CSVDataSet(
    filepath="data/01_raw/test.csv", save_args={"index": False}, version=version
)
io = DataCatalog({"test_data_set": test_data_set})

io.save("test_data_set", data1)  # emits a UserWarning due to version inconsistency

# raises DataSetError since the data/01_raw/test.csv/exact_load_version/test.csv
# file does not exist
reloaded = io.load("test_data_set")
```
