# The Data Catalog

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

This section introduces `catalog.yml`, the project-shareable Data Catalog. The file is located in `conf/base` and is a registry of all data sources available for use by a project; it manages loading and saving of data.

All supported data connectors are available in [`kedro.extras.datasets`](/kedro.extras.datasets).

## Using the Data Catalog within Kedro configuration

Kedro uses configuration to make your code reproducible when it has to reference datasets in different locations and/or in different environments.

You can copy this file and reference additional locations for the same datasets. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production while copying and updating a second version of `catalog.yml` that can be placed in `conf/local/` to register the locations of sample datasets on the local computer that you are using for prototyping your data pipeline.

There is built-in functionality for `conf/local/` to overwrite `conf/base/` detailed [here](./03_configuration.md). This means that a dataset called `cars` could exist in the `catalog.yml` files in `conf/base/` and `code/local/`. In code, in `src`, you would only call a dataset named `cars` and Kedro would detect which definition of `cars` dataset to use to run your pipeline - `cars` definition from `code/local/catalog.yml` would take precedence in this case.

The Data Catalog also works with the `credentials.yml` in `conf/local/`, allowing you to specify usernames and passwords that are required to load certain datasets.

The are two ways of defining a Data Catalog through the use of YAML configuration, or programmatically using an API. Both methods allow you to specify:

 - Dataset name
 - Dataset type
 - Location of the dataset using `fsspec`, detailed in the next section
 - Credentials needed in order to access the dataset
 - Load and saving arguments
 - Whether or not you want a [dataset or ML model to be versioned](./08_advanced_io.md#versioning) when you run your data pipeline

## Specifying the location of the dataset

Kedro relies on [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) for reading and saving data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. When specifying a storage location in `filepath:`, a URL should be provided using the general form `protocol://path/to/data`.  If no protocol is provided, the local file system is assumed (same as ``file://``).

The following prepends are available:
- **Local or Network File System**: `file://` - the local file system is default in the absence of any protocol, it also permits relative paths.
- **Hadoop File System (HDFS)**: `hdfs://user@server:port/path/to/data` - Hadoop Distributed File System, for resilient, replicated files within a cluster.
- **Amazon S3**: `s3://my-bucket-name/path/to/data` - Amazon S3 remote binary store, often used with Amazon EC2,
  using the library s3fs.
- **Google Cloud Storage**: `gcs://` - Google Cloud Storage, typically used with Google Compute
  resource using gcsfs (in development).
- **HTTP(s)**: ``http://`` or ``https://`` for reading data directly from HTTP web servers.

`fsspec` also provides other file systems that may be of interest to Kedro users, such as SSH, FTP and WebHDFS. See the [documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#implementations) for more information.

## Using the Data Catalog with the YAML API

The YAML API allows you to configure your datasets in a YAML configuration file, `conf/base/catalog.yml` or `conf/local/catalog.yml`.

Here is an example data config `catalog.yml`:

```yaml
# Example 1: Loads / saves a CSV file from / to a local file system

bikes:
  type: pandas.CSVDataSet
  filepath: "data/01_raw/bikes.csv"

# Example 2: Loads and saves a CSV on a local file system, using specified load and save arguments

cars:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/cars.csv
  load_args:
    sep: ','
  save_args:
    index: False
    date_format: '%Y-%m-%d %H:%M'
    decimal: '.'

# Example 3: Loads a CSV file from a specific S3 bucket, using credentials and load arguments

motorbikes:
  type: pandas.CSVDataSet
  filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  load_args:
    sep: ','
    skiprows: 5
    skipfooter: 1
    na_values: ['#NA', 'NA']

# Example 4: Loads / saves a pickle file from / to a local file system

airplanes:
  type: pickle.PickleDataSet
  filepath: data/06_models/airplanes.pkl
  backend: pickle

# Example 5: Loads an excel file from Google Cloud Storage

rockets:
  type: pandas.ExcelDataSet
  filepath: gcs://your_bucket/data/02_intermediate/company/motorbikes.xlsx
  fs_args:
    project: my-project
  credentials: my_gcp_credentials
  save_args:
    sheet_name: Sheet1

# Example 6: Save an image created with Matplotlib on Google Cloud Storage

results_plot:
  type: matplotlib.MatplotLibWriter
  filepath: gcs://your_bucket/data/08_results/plots/output_1.jpeg
  fs_args:
    project: my-project
  credentials: my_gcp_credentials

# Example 7: Loads / saves an HDF file on local file system storage, using specified load and save arguments

skateboards:
  type: pandas.HDFDataSet
  filepath: data/02_intermediate/skateboards.hdf
  key: name
  load_args:
    columns: ['brand', 'length']
  save_args:
    mode: 'w'  # Overwrite even when the file already exists
    dropna: True

# Example 8: Loads / saves a parquet file on local file system storage, using specified load and save arguments

trucks:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/trucks.parquet
  load_args:
    columns: ['name', 'gear','disp', 'wt']
    categories: list
    index: 'name'
  save_args:
     compression: 'GZIP'
     file_scheme: 'hive'
     has_nulls: false
     partition_on: ['name']

# Example 9: Load / saves a Spark table on S3, using specified load and save arguments

weather:
  type: spark.SparkDataSet
  filepath: s3a://your_bucket/data/01_raw/weather*
  credentials: dev_s3
  file_format: csv
  load_args:
    header: True
    inferSchema: True
  save_args:
    sep: '|'
    header: True

# Example 10: Loads / saves a SQL table using credentials, a database connection, using specified load and save arguments

scooters:
  type: pandas.SQLTableDataSet
  credentials: scooters_credentials
  table_name: scooters
  load_args:
    index_col: ['name']
    columns: ['name', 'gear']
  save_args:
    if_exists: 'replace'

# Example 11: Load a SQL table with credentials, a database connection, and applies a SQL query to the table

scooters_query:
  type: pandas.SQLQueryDataSet
  credentials: scooters_credentials
  sql: 'select * from cars where gear=4'
  load_args:
    index_col: ['name']
```

> *Note:* When using [`pandas.SQLTableDataSet`](/kedro.extras.datasets.pandas.SQLTableDataSet) or [`pandas.SQLQueryDataSet`](/kedro.extras.datasets.pandas.SQLQueryDataSet) you must provide a database connection string. In the example above we pass it using `scooters_credentials` key from the credentials (see the details in [Feeding in credentials](#feeding-in-credentials) section below). `scooters_credentials` must have a top-level key `con` containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) connection string. Alternative to credentials would be to explicitly put `con` into `load_args` and `save_args` (`pandas.SQLTableDataSet` only).


## Adding parameters

You can [configure parameters](./03_configuration.md#loading-parameters) for your project and [reference them](./03_configuration.md#using-parameters) in your nodes. The way to do this is via `add_feed_dict()` method (Relevant API documentation: [DataCatalog](/kedro.io.DataCatalog)). You should be able to use this method to add any other entry / metadata you wish on the `DataCatalog`.


## Feeding in credentials

Before instantiating the `DataCatalog` Kedro will first attempt to read the credentials from project configuration (see [this section](./03_configuration.md#aws-credentials) for more details). Resulting dictionary will then be passed into `DataCatalog.from_config()` as `credentials` argument.

Let's assume that the project contains the file `conf/local/credentials.yml` with the following contents:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: token
    aws_secret_access_key: key

scooters_credentials:
  con: sqlite:///kedro.db

my_gcp_credentials:
  id_token: key
```

In the example above `catalog.yml` contains references to credentials keys `dev_s3` and `scooters_credentials`. It means that when instantiating `motorbikes` dataset, for example, the `DataCatalog` will attempt to read top-level key `dev_s3` from the received `credentials` dictionary, and then will pass its values into the dataset `__init__` as `credentials` argument. This is essentially equivalent to calling this:

```python
CSVDataSet(
    filepath="s3://test_bucket/data/02_intermediate/company/motorbikes.csv",
    load_args=dict(sep=",", skiprows=5, skipfooter=1, na_values=["#NA", "NA"],),
    credentials=dict(client_kwargs=dict(aws_access_key_id="token", aws_secret_access_key="key")),
)
```


## Loading multiple datasets that have similar configuration

You may encounter situations where your datasets use the same file format, load and save arguments, and are stored in the same folder. YAML has a [built-in syntax](https://yaml.org/spec/1.2/spec.html#id2765878) for factorising parts of a YAML file, which means that you can decide what is generalisable across your datasets so that you do not have to spend time copying and pasting dataset configurations in `catalog.yml`.

You can see this in the following example:

```yaml
_csv: &csv
  type: spark.SparkDataSet
  file_format: csv
  load_args:
    sep: ','
    na_values: ['#NA', 'NA']
    header: True
    inferSchema: False

cars:
  <<: *csv
  filepath: 's3a://data/01_raw/cars.csv'

trucks:
  <<: *csv
  filepath: 's3a://data/01_raw/trucks.csv'

bikes:
  <<: *csv
  filepath: 's3a://data/01_raw/bikes.csv'
  load_args:
    header: False
```

The syntax `&csv` names the following block `csv` and the syntax `<<: *csv` inserts the contents of the block named `csv`. Locally declared keys entirely override inserted ones as seen in `bikes`.

> *Note*: It's important that the name of the template entry starts with a `_` so Kedro knows not to try and instantiate it as a dataset.

You can also nest reuseable YAML syntax:

```yaml
_csv: &csv
  type: spark.SparkDataSet
  file_format: csv
  load_args: &csv_load_args
    header: True
    inferSchema: False

airplanes:
  <<: *csv
  filepath: 's3a://data/01_raw/airplanes.csv'
  load_args:
    <<: *csv_load_args
    sep: ';'
```

In this example the default `csv` configuration is inserted into `airplanes` and then the `load_args` block is overridden. Normally that would replace the whole dictionary. In order to extend `load_args` the defaults for that block are then re-inserted.


## Transcoding datasets

You may come across a situation where you would like to read the same file using two different dataset implementations. Use transcoding when you want to load and save the same file, via its specified `filepath`, using different `DataSet` implementations.

### A typical example of transcoding

For instance, parquet files can not only be loaded via the `ParquetDataSet` using `pandas`, but also directly by `SparkDataSet`. This conversion is typical when coordinating a `Spark` to `pandas` workflow.

To enable transcoding, you will need to define two `DataCatalog` entries for the same dataset in a common format (Parquet, JSON, CSV, etc.) in your `conf/base/catalog.yml`:

```yaml
my_dataframe@spark:
  type: spark.SparkDataSet
  filepath: data/02_intermediate/data.parquet
  file_format: 'parquet'

my_dataframe@pandas:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/data.parquet
```

These entries will be used in the pipeline like this:

```python
Pipeline(
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


## Transforming datasets

Transformers intercept the load and save operations on Kedro `DataSet`s. Use cases that transformers enable include:
 - Performing data validation,
 - Tracking operation performance,
 - And, converting a data format (although we would recommend [Transcoding](https://kedro.readthedocs.io/en/stable/04_user_guide/04_data_catalog.html#transcoding-datasets) for this).

### Applying built-in transformers

The use case of _tracking operation performance_ by applying built-in transformers for monitoring load and save operation latency will be covered.

Transformers are applied at the `DataCatalog` level. To apply the built-in `ProfileTimeTransformer`, you need to:
1. Navigate to `src/<package_name>/run.py`
2. Override `_create_catalog` method for your `ProjectContext` class using the following:

```python
from typing import Dict, Any

from kedro.context import KedroContext
from kedro.extras.transformers import ProfileTimeTransformer  # new import
from kedro.io import DataCatalog
from kedro.versioning import Journal


class ProjectContext(KedroContext):

    ...

    def _create_catalog(self, *args, **kwargs):
        catalog = super()._create_catalog(*args, **kwargs)
        profile_time = ProfileTimeTransformer()  # instantiate a built-in transformer
        catalog.add_transformer(profile_time)  # apply it to the catalog
        return catalog
```

Once complete, rerun the pipeline from the terminal and you should see the following logging output:

```console
$ kedro run

...
2019-11-13 15:09:01,784 - kedro.io.data_catalog - INFO - Loading data from `companies` (CSVDataSet)...
2019-11-13 15:09:01,827 - ProfileTimeTransformer - INFO - Loading companies took 0.043 seconds
2019-11-13 15:09:01,828 - kedro.pipeline.node - INFO - Running node: preprocessing_companies: preprocess_companies([companies]) -> [preprocessed_companies]
2019-11-13 15:09:01,880 - kedro_tutorial.nodes.data_engineering - INFO - Running 'preprocess_companies' took 0.05 seconds
2019-11-13 15:09:01,880 - kedro_tutorial.nodes.data_engineering - INFO - Running 'preprocess_companies' took 0.05 seconds
2019-11-13 15:09:01,880 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_companies` (CSVDataSet)...
2019-11-13 15:09:02,112 - ProfileTimeTransformer - INFO - Saving preprocessed_companies took 0.232 seconds
2019-11-13 15:09:02,113 - kedro.runner.sequential_runner - INFO - Completed 1 out of 6 tasks
...
```

You can notice 2 new `INFO` level log messages from `ProfileTimeTransformer`, which report the corresponding dataset load and save operation latency.

> Pro Tip: You can narrow down the application of the transformer by specifying an optional list of the datasets in `add_transformer`. For example, the command `catalog.add_transformer(profile_time, ["dataset1", "dataset2"])` will apply `profile_time` transformer _only_ to the datasets named `dataset1` and `dataset2`. This may be useful when you need to apply a transformer only to a subset of datasets, rather than all of them.

### Developing your own transformer

The use case of _tracking operation performance_ by developing our own transformer for tracking memory consumption will be covered. A built-in memory profiler is supported, however, in this example you will learn how to create your own one.

You can profile memory using [memory-profiler](https://github.com/pythonprofilers/memory_profiler). The custom transformer should:
1. Inherit the `kedro.io.AbstractTransformer` base class
2. Implement the `load` and `save` method (as show in the example below)

Create `src/<package_name>/memory_profile.py` and then paste the following code into it:

```python
import logging
from typing import Callable, Any

from kedro.io import AbstractTransformer
from memory_profiler import memory_usage


def _normalise_mem_usage(mem_usage):
    # memory_profiler < 0.56.0 returns list instead of float
    return mem_usage[0] if isinstance(mem_usage, (list, tuple)) else mem_usage


class ProfileMemoryTransformer(AbstractTransformer):
    """ A transformer that logs the maximum memory consumption during load and save calls """

    @property
    def _logger(self):
        return logging.getLogger(self.__class__.__name__)

    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        mem_usage, data = memory_usage(
            (load, [], {}),
            interval=0.1,
            max_usage=True,
            retval=True,
            include_children=True,
        )
        # memory_profiler < 0.56.0 returns list instead of float
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Loading %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        mem_usage = memory_usage(
            (save, [data], {}),
            interval=0.1,
            max_usage=True,
            retval=False,
            include_children=True,
        )
        mem_usage = _normalise_mem_usage(mem_usage)

        self._logger.info(
            "Saving %s consumed %2.2fMiB memory at peak time", data_set_name, mem_usage
        )
```

Finally, you need to update `ProjectContext._create_catalog` method definition to apply your custom transformer:

```python
...
from .memory_profile import ProfileMemoryTransformer  # new import


class ProjectContext(KedroContext):

    ...

    def _create_catalog(self, *args, **kwargs):
        catalog = super()._create_catalog(*args, **kwargs)

        profile_time = ProfileTimeTransformer()
        catalog.add_transformer(profile_time)

        # instantiate our custom transformer
        profile_memory = ProfileMemoryTransformer()

        # as memory tracking is quite time-consuming, for demonstration purposes
        # let's apply profile_memory only to the master_table
        catalog.add_transformer(profile_memory, "master_table")
        return catalog
```

And rerun the pipeline:

```console
$ kedro run

...
2019-11-13 15:55:01,674 - kedro.io.data_catalog - INFO - Saving data to `master_table` (CSVDataSet)...
2019-11-13 15:55:12,322 - ProfileMemoryTransformer - INFO - Saving master_table consumed 606.98MiB memory at peak time
2019-11-13 15:55:12,322 - ProfileTimeTransformer - INFO - Saving master_table took 10.648 seconds
2019-11-13 15:55:12,357 - kedro.runner.sequential_runner - INFO - Completed 3 out of 6 tasks
2019-11-13 15:55:12,358 - kedro.io.data_catalog - INFO - Loading data from `master_table` (CSVDataSet)...
2019-11-13 15:55:13,933 - ProfileMemoryTransformer - INFO - Loading master_table consumed 533.05MiB memory at peak time
2019-11-13 15:55:13,933 - ProfileTimeTransformer - INFO - Loading master_table took 1.576 seconds
...
```

## Versioning datasets and ML models

Making a simple addition to your Data Catalog allows you to perform versioning of datasets and machine learning models.

Consider the following versioned dataset defined in the `catalog.yml`:

```yaml
cars.csv:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/cars.csv
  versioned: true
```

The `DataCatalog` will create a versioned `CSVDataSet` called `cars.csv`. The actual csv file location will look like `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` corresponds to a global save version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

You can run the pipeline with a particular versioned data set with `--load-version` flag as follows:

```bash
kedro run --load-version="cars.csv:YYYY-MM-DDThh.mm.ss.sssZ"
```
where `--load-version` is dataset name and version timestamp separated by `:`.

This section shows just the very basics of versioning. You can learn more about how this feature can be used in [Advanced IO](./08_advanced_io.md#versioning).

## Using the Data Catalog with the Code API

The code API allows you to configure data sources in code. This can also be used to operate the IO module within notebooks.

## Configuring a Data Catalog

In a file like `catalog.py`, you can generate the Data Catalog. This will allow everyone in the project to review all the available data sources. In the following, we are using the pre-built CSV loader, which is documented in the [API reference documentation](/kedro.extras.datasets)

```python
from kedro.io import (
    DataCatalog,
    CSVDataSet,
    SQLTableDataSet,
    SQLQueryDataSet,
    ParquetDataSet,
)

io = DataCatalog(
    {
        "bikes": CSVDataSet(filepath="../data/01_raw/bikes.csv"),
        "cars": CSVDataSet(
            filepath="../data/01_raw/cars.csv", load_args=dict(sep=",")
        ),
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

> *Note:* When using `SQLTableDataSet` or `SQLQueryDataSet` you must provide a `con` key containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) database connection string. In the example above we pass it as part of `credentials` argument. Alternative to `credentials` would be to put `con` into `load_args` and `save_args` (`SQLTableDataSet` only).

## Loading datasets

Each dataset can be accessed by its name.

```python
cars = io.load("cars")  # data is now loaded as a DataFrame in 'cars'
gear = cars["gear"].values
```

### Behind the scenes

The following steps happened behind the scenes when `load` was called:

- The value `cars` was located in the Data Catalog
- The corresponding `AbstractDataSet` object was retrieved
- The `load` method of this dataset was called
- This `load` method delegated the loading to the underlying pandas `read_csv` function

### Viewing the available data sources

If you forget what data was assigned, you can always review the `DataCatalog`.

```python
io.list()
```

## Saving data

Saving data can be completed with a similar API.

> *Note:* This use is not recommended unless you are prototyping in notebooks.

### Saving data to memory

```python
from kedro.io import MemoryDataSet

memory = MemoryDataSet(data=None)
io.add("cars_cache", memory)
io.save("cars_cache", "Memory can store anything.")
io.load("car_cache")
```

### Saving data to a SQL database for querying

At this point we may want to put the data in a SQLite database to run queries on it. Let's use that to rank scooters by their mpg.

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

### Saving data in parquet

Finally we can save the processed data in Parquet format.

```python
io.save("ranked", ranked)
```

> *Note:* Saving `None` to a dataset is not allowed!

### Creating your own dataset
More specialised datasets can be found in `contrib/io`. [Creating new datasets](../03_tutorial/03_set_up_data.md#creating-custom-datasets) is the easiest way to contribute to the Kedro project.
