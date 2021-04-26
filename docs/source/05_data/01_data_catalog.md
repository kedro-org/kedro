# The Data Catalog

> *Note:* This documentation is based on `Kedro 0.17.1`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

This section introduces `catalog.yml`, the project-shareable Data Catalog. The file is located in `conf/base` and is a registry of all data sources available for use by a project; it manages loading and saving of data.

All supported data connectors are available in [`kedro.extras.datasets`](/kedro.extras.datasets).

## Using the Data Catalog within Kedro configuration

Kedro uses configuration to make your code reproducible when it has to reference datasets in different locations and/or in different environments.

You can copy this file and reference additional locations for the same datasets. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production while copying and updating a second version of `catalog.yml` in `conf/local/` to register the locations of sample datasets that you are using for prototyping your data pipeline(s).

There is built-in functionality for `conf/local/` to overwrite `conf/base/` detailed [here](../04_kedro_project_setup/02_configuration.md). This means that a dataset called `cars` could exist in the `catalog.yml` files in `conf/base/` and `conf/local/`. In code, in `src`, you would only call a dataset named `cars` and Kedro would detect which definition of `cars` dataset to use to run your pipeline - `cars` definition from `conf/local/catalog.yml` would take precedence in this case.

The Data Catalog also works with the `credentials.yml` in `conf/local/`, allowing you to specify usernames and passwords that are required to load certain datasets.

The are two ways of defining a Data Catalog through the use of YAML configuration, or programmatically using an API. Both methods allow you to specify:

 - Dataset name
 - Dataset type
 - Location of the dataset using `fsspec`, detailed in the next section
 - Credentials needed in order to access the dataset
 - Load and saving arguments
 - Whether or not you want a [dataset or ML model to be versioned](02_kedro_io.md#versioning) when you run your data pipeline

## Specifying the location of the dataset

Kedro relies on [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) for reading and saving data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. When specifying a storage location in `filepath:`, you should provide a URL using the general form `protocol://path/to/data`.  If no protocol is provided, the local file system is assumed (same as ``file://``).

The following prepends are available:

- **Local or Network File System**: `file://` - the local file system is default in the absence of any protocol, it also permits relative paths.
- **Hadoop File System (HDFS)**: `hdfs://user@server:port/path/to/data` - Hadoop Distributed File System, for resilient, replicated files within a cluster.
- **Amazon S3**: `s3://my-bucket-name/path/to/data` - Amazon S3 remote binary store, often used with Amazon EC2,
  using the library s3fs.
- **S3 Compatible Storage**: `s3://my-bucket-name/path/_to/data` - e.g. Minio, using the s3fs library.
- **Google Cloud Storage**: `gcs://` - Google Cloud Storage, typically used with Google Compute
  resource using gcsfs (in development).
- **Azure Blob Storage / Azure Data Lake Storage Gen2**: `abfs://` - Azure Blob Storage, typically used when working on an Azure environment.
- **HTTP(s)**: ``http://`` or ``https://`` for reading data directly from HTTP web servers.

`fsspec` also provides other file systems, such as SSH, FTP and WebHDFS. See the [documentation](https://filesystem-spec.readthedocs.io/en/latest/api.html#implementations) for more information.

## Data Catalog `*_args` parameters

Data Catalog accepts two different groups of `*_args` parameters that serve different purposes:
- `fs_args`
- `load_args` and `save_args`

The `fs_args` is used to configure the interaction with a filesystem.
All the top-level parameters of `fs_args` (except `open_args_load` and `open_args_save`) will be passed in an underlying filesystem class.

Example 1: Provide the `project` value to the underlying filesystem class (`GCSFileSystem`) to interact with Google Cloud Storage (GCS).
```yaml
test_dataset:
  type: ...
  fs_args:
    project: test_project
```

The `open_args_load` and `open_args_save` parameters are passed to the filesystem's `open` method to configure how a dataset file (on a specific filesystem) is opened during a load or save operation, respectively.

Example 2: Load data from a local binary file using `utf-8` encoding.
```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_load:
      mode: "rb"
      encoding: "utf-8"
```

`load_args` and `save_args` configure how a third-party library (e.g. `pandas` for `CSVDataSet`) loads/saves data from/to a file.

Example 3: Save data to a CSV file without row names (index) using `utf-8` encoding.
```yaml
test_dataset:
  type: pandas.CSVDataSet
  ...
  save_args:
    index: False
    encoding: "utf-8"
```

## Using the Data Catalog with the YAML API

The YAML API allows you to configure your datasets in a YAML configuration file, `conf/base/catalog.yml` or `conf/local/catalog.yml`.

Here are some examples of data configuration in a `catalog.yml`:

Example 1: Loads / saves a CSV file from / to a local file system
```yaml
bikes:
  type: pandas.CSVDataSet
  filepath: data/01_raw/bikes.csv
```

Example 2: Loads and saves a CSV on a local file system, using specified load and save arguments

```yaml
cars:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/cars.csv
  load_args:
    sep: ','
  save_args:
    index: False
    date_format: '%Y-%m-%d %H:%M'
    decimal: .

```

Example 3: Loads and saves a compressed CSV on a local file system

```yaml
boats:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/boats.csv.gz
  load_args:
    sep: ','
    compression: 'gzip'
  fs_args:
    open_args_load:
      mode: 'rb'
```

Example 4: Loads a CSV file from a specific S3 bucket, using credentials and load arguments

```yaml
motorbikes:
  type: pandas.CSVDataSet
  filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  load_args:
    sep: ','
    skiprows: 5
    skipfooter: 1
    na_values: ['#NA', NA]
```

Example 5: Loads / saves a pickle file from / to a local file system

```yaml
airplanes:
  type: pickle.PickleDataSet
  filepath: data/06_models/airplanes.pkl
  backend: pickle
```

Example 6: Loads an excel file from Google Cloud Storage

```yaml
rockets:
  type: pandas.ExcelDataSet
  filepath: gcs://your_bucket/data/02_intermediate/company/motorbikes.xlsx
  fs_args:
    project: my-project
  credentials: my_gcp_credentials
  save_args:
    sheet_name: Sheet1
```

Example 7: Save an image created with Matplotlib on Google Cloud Storage

```yaml
results_plot:
  type: matplotlib.MatplotlibWriter
  filepath: gcs://your_bucket/data/08_results/plots/output_1.jpeg
  fs_args:
    project: my-project
  credentials: my_gcp_credentials
```

Example 8: Loads / saves an HDF file on local file system storage, using specified load and save arguments

```yaml
skateboards:
  type: pandas.HDFDataSet
  filepath: data/02_intermediate/skateboards.hdf
  key: name
  load_args:
    columns: [brand, length]
  save_args:
    mode: w  # Overwrite even when the file already exists
    dropna: True
```

Example 9: Loads / saves a parquet file on local file system storage, using specified load and save arguments

```yaml
trucks:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/trucks.parquet
  load_args:
    columns: [name, gear, disp, wt]
    categories: list
    index: name
  save_args:
    compression: GZIP
    file_scheme: hive
    has_nulls: False
    partition_on: [name]
```

Example 10: Load / saves a Spark table on S3, using specified load and save arguments

```yaml
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
```

Example 11: Loads / saves a SQL table using credentials, a database connection, using specified load and save arguments

```yaml
scooters:
  type: pandas.SQLTableDataSet
  credentials: scooters_credentials
  table_name: scooters
  load_args:
    index_col: [name]
    columns: [name, gear]
  save_args:
    if_exists: replace
```

Example 12: Load a SQL table with credentials, a database connection, and applies a SQL query to the table

```yaml
scooters_query:
  type: pandas.SQLQueryDataSet
  credentials: scooters_credentials
  sql: select * from cars where gear=4
  load_args:
    index_col: [name]
```

Example 13: Load data from an API endpoint, example US corn yield data from USDA

```yaml
us_corn_yield_data:
  type: api.APIDataSet
  url: https://quickstats.nass.usda.gov
  params:
    key: SOME_TOKEN
    format: JSON
    commodity_desc: CORN
    statisticcat_des: YIELD
    agg_level_desc: STATE
    year: 2000
```

> *Note:* When using [`pandas.SQLTableDataSet`](/kedro.extras.datasets.pandas.SQLTableDataSet) or [`pandas.SQLQueryDataSet`](/kedro.extras.datasets.pandas.SQLQueryDataSet) you must provide a database connection string. In the example above we pass it using `scooters_credentials` key from the credentials (see the details in [Feeding in credentials](#feeding-in-credentials) section below). `scooters_credentials` must have a top-level key `con` containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) connection string. As an alternative to credentials, you could explicitly put `con` into `load_args` and `save_args` (`pandas.SQLTableDataSet` only).

Example 14: Loading data from Minio (S3 API Compatible Storage)
```yaml
test:
  type: pandas.CSVDataSet
  filepath: s3://your_bucket/test.csv # assume `test.csv` is uploaded to the Minio server.
  credentials: dev_minio
```
In `credentials.yml`, define the `key`, `secret` and the `endpoint_url` as follows:

```yaml
dev_minio:
  key: token
  secret: key
  cleitn_kwargs:
    endpoint_url : 'http://localhost:9000'
```
> Note: The easiest way to setup MinIO is to run a Docker image. After the following command, you can access to Minio server with http://localhost:9000 and create a bucket and add files as if it is on S3.

`docker run -p 9000:9000 -e "MINIO_ACCESS_KEY=token" -e "MINIO_SECRET_KEY=key" minio/minio server /data`

Example 15: Loading a model saved as a pickle from Azure Blob Storage

```yaml
ml_model:
  type: pickle.PickleDataSet
  filepath: "abfs://models/ml_models.pickle"
  versioned: True
  credentials: dev_abs
```
In `credentials.yml`, define the `account_name` and `account_key` as follows:

```yaml
dev_abs:
  account_name: accountname
  account_key: key
```

## Creating a Data Catalog YAML configuration file via CLI

You can use [`kedro catalog create` command](../09_development/03_commands_reference.md#create-a-data-catalog-yaml-configuration-file) to create a Data Catalog YAML configuration.

It creates a `<conf_root>/<env>/catalog/<pipeline_name>.yml` configuration file with `MemoryDataSet` datasets for each dataset in a registered pipeline if it is missing from the `DataCatalog`.

```yaml
# <conf_root>/<env>/catalog/<pipeline_name>.yml
rockets:
  type: MemoryDataSet
scooters:
  type: MemoryDataSet
```

## Adding parameters

You can [configure parameters](../04_kedro_project_setup/02_configuration.md#loading-parameters) for your project and [reference them](../04_kedro_project_setup/02_configuration.md#using-parameters) in your nodes. Do this using the `add_feed_dict()` method ([API documentation](/kedro.io.DataCatalog)). You can use this method to add any other entry / metadata you wish on the `DataCatalog`.


## Feeding in credentials

Before instantiating the `DataCatalog` Kedro will first attempt to read the credentials from [the project configuration](../04_kedro_project_setup/02_configuration.md#aws-credentials). The resulting dictionary is then passed into `DataCatalog.from_config()` as the `credentials` argument.

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

In the example above `catalog.yml` contains references to credentials keys `dev_s3` and `scooters_credentials`. It means that when instantiating `motorbikes` dataset, for example, the `DataCatalog` will attempt to read top-level key `dev_s3` from the received `credentials` dictionary, and then will pass its values into the dataset `__init__` as `credentials` argument. This is essentially equivalent to calling this:

```python
CSVDataSet(
    filepath="s3://test_bucket/data/02_intermediate/company/motorbikes.csv",
    load_args=dict(sep=",", skiprows=5, skipfooter=1, na_values=["#NA", "NA"],),
    credentials=dict(key="token", secret="key"),
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
    na_values: ['#NA', NA]
    header: True
    inferSchema: False

cars:
  <<: *csv
  filepath: s3a://data/01_raw/cars.csv

trucks:
  <<: *csv
  filepath: s3a://data/01_raw/trucks.csv

bikes:
  <<: *csv
  filepath: s3a://data/01_raw/bikes.csv
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
  filepath: s3a://data/01_raw/airplanes.csv
  load_args:
    <<: *csv_load_args
    sep: ;
```

In this example the default `csv` configuration is inserted into `airplanes` and then the `load_args` block is overridden. Normally that would replace the whole dictionary. In order to extend `load_args` the defaults for that block are then re-inserted.


## Transcoding datasets

You may come across a situation where you would like to read the same file using two different dataset implementations. Use transcoding when you want to load and save the same file, via its specified `filepath`, using different `DataSet` implementations.

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

Transformers are used to intercept the load and save operations on Kedro `DataSet`s. Use cases for transformers include:

 - Data validation
 - Tracking operation performance
 - Data format conversion (although we would recommend [Transcoding](#transcoding-datasets) for this)

### Applying built-in transformers

Here we cover the use case of _tracking operation performance_ by applying built-in transformers to monitor the latency of load and save operations.

Transformers are applied at the `DataCatalog` level. To apply the built-in `ProfileTimeTransformer`, you need to:

1. Navigate to `src/<package_name>/hooks.py`
2. Apply `ProfileTimeTransformer` in the hook implementation `TransformerHooks.after_catalog_created`
3. Register the hook in your `src/<package_name>/settings.py`

```python
# src/<package_name>/hooks.py

from kedro.extras.transformers import ProfileTimeTransformer  # new import
from kedro.framework.hooks import hook_impl  # new import
from kedro.io import DataCatalog  # new import


class TransformerHooks:
    @hook_impl
    def after_catalog_created(self, catalog: DataCatalog) -> None:
        catalog.add_transformer(ProfileTimeTransformer())
```

```python
# src/<package_name>/settings.py
from <package_name>.hooks import TransformerHooks

HOOKS = (TransformerHooks(),)
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

The `ProfileTimeTransformer - INFO` log messages report the latency of dataset load and save operations.

### Transformer scope
You can refine the scope of the transformer by specifying an optional list of the datasets it is applied to in `add_transformer`.

For example, the command `catalog.add_transformer(profile_time, ["dataset1", "dataset2"])` applies the `profile_time` transformer _only_ to the datasets named `dataset1` and `dataset2`.

This is useful when you need to apply a transformer to just a subset of datasets.

## Versioning datasets and ML models

Making a simple addition to your Data Catalog allows you to perform versioning of datasets and machine learning models.

Consider the following versioned dataset defined in the `catalog.yml`:

```yaml
cars.csv:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/cars.csv
  versioned: True
```

The `DataCatalog` will create a versioned `CSVDataSet` called `cars.csv`. The actual csv file location will look like `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` corresponds to a global save version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

You can run the pipeline with a particular versioned data set with `--load-version` flag as follows:

```bash
kedro run --load-version="cars.csv:YYYY-MM-DDThh.mm.ss.sssZ"
```
where `--load-version` is dataset name and version timestamp separated by `:`.

This section shows just the very basics of versioning, which is described further in the documentation about [Kedro IO](../05_data/02_kedro_io.md#versioning).

## Using the Data Catalog with the Code API

The code API allows you to:

* configure data sources in code
* operate the IO module within notebooks

### Configuring a Data Catalog

In a file like `catalog.py`, you can construct a `DataCatalog` object programmatically. In the following, we are using a number of pre-built data loaders documented in the [API reference documentation](/kedro.extras.datasets).

```python
from kedro.io import DataCatalog
from kedro.extras.datasets.pandas import (
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

> *Note:* When using `SQLTableDataSet` or `SQLQueryDataSet` you must provide a `con` key containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) database connection string. In the example above we pass it as part of `credentials` argument. Alternative to `credentials` is to put `con` into `load_args` and `save_args` (`SQLTableDataSet` only).

### Loading datasets

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

### Viewing the available data sources

If you forget what data was assigned, you can always review the `DataCatalog`.

```python
io.list()
```

### Saving data

You can save data using an API similar to that used to load data.

> *Note:* This use is not recommended unless you are prototyping in notebooks.

#### Saving data to memory

```python
from kedro.io import MemoryDataSet

memory = MemoryDataSet(data=None)
io.add("cars_cache", memory)
io.save("cars_cache", "Memory can store anything.")
io.load("car_cache")
```

#### Saving data to a SQL database for querying

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

#### Saving data in Parquet

Finally we can save the processed data in Parquet format.

```python
io.save("ranked", ranked)
```

> *Note:* Saving `None` to a dataset is not allowed!
