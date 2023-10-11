# Data Catalog YAML examples

This page contains a set of examples to help you structure your YAML configuration file in `conf/base/catalog.yml` or `conf/local/catalog.yml`.

```{warning}
Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.
```

```{contents} Table of Contents
:depth: 3
```

## Load data from a local binary file using `utf-8` encoding

The `open_args_load` and `open_args_save` parameters are passed to the filesystem `open` method to configure how a dataset file (on a specific filesystem) is opened during a load or save operation respectively.

```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_load:
      mode: "rb"
      encoding: "utf-8"
```

`load_args` and `save_args` configure how a third-party library (e.g. `pandas` for `CSVDataset`) loads/saves data from/to a file.

## Save data to a CSV file without row names (index) using `utf-8` encoding

```yaml
test_dataset:
  type: pandas.CSVDataset
  ...
  save_args:
    index: False
    encoding: "utf-8"
```

## Load/save a CSV file from/to a local file system

```yaml
bikes:
  type: pandas.CSVDataset
  filepath: data/01_raw/bikes.csv
```

## Load/save a CSV on a local file system, using specified load/save arguments

```yaml
cars:
  type: pandas.CSVDataset
  filepath: data/01_raw/company/cars.csv
  load_args:
    sep: ','
  save_args:
    index: False
    date_format: '%Y-%m-%d %H:%M'
    decimal: .

```

## Load/save a compressed CSV on a local file system

```yaml
boats:
  type: pandas.CSVDataset
  filepath: data/01_raw/company/boats.csv.gz
  load_args:
    sep: ','
    compression: 'gzip'
  fs_args:
    open_args_load:
      mode: 'rb'
```

## Load a CSV file from a specific S3 bucket, using credentials and load arguments

```yaml
motorbikes:
  type: pandas.CSVDataset
  filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  load_args:
    sep: ','
    skiprows: 5
    skipfooter: 1
    na_values: ['#NA', NA]
```

## Load/save a pickle file from/to a local file system

```yaml
airplanes:
  type: pickle.PickleDataset
  filepath: data/06_models/airplanes.pkl
  backend: pickle
```

## Load an Excel file from Google Cloud Storage

The example includes the `project` value for the underlying filesystem class (`GCSFileSystem`) within Google Cloud Storage (GCS)

```yaml
rockets:
  type: pandas.ExcelDataset
  filepath: gcs://your_bucket/data/02_intermediate/company/motorbikes.xlsx
  fs_args:
    project: my-project
  credentials: my_gcp_credentials
  save_args:
    sheet_name: Sheet1
```


## Load a multi-sheet Excel file from a local file system

```yaml
trains:
  type: pandas.ExcelDataset
  filepath: data/02_intermediate/company/trains.xlsx
  load_args:
    sheet_name: [Sheet1, Sheet2, Sheet3]
```

## Save an image created with Matplotlib on Google Cloud Storage

```yaml
results_plot:
  type: matplotlib.MatplotlibWriter
  filepath: gcs://your_bucket/data/08_results/plots/output_1.jpeg
  fs_args:
    project: my-project
  credentials: my_gcp_credentials
```


## Load/save an HDF file on local file system storage, using specified load/save arguments

```yaml
skateboards:
  type: pandas.HDFDataset
  filepath: data/02_intermediate/skateboards.hdf
  key: name
  load_args:
    columns: [brand, length]
  save_args:
    mode: w  # Overwrite even when the file already exists
    dropna: True
```

## Load/save a parquet file on local file system storage, using specified load/save arguments

```yaml
trucks:
  type: pandas.ParquetDataset
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


## Load/save a Spark table on S3, using specified load/save arguments

```yaml
weather:
  type: spark.SparkDataset
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


## Load/save a SQL table using credentials, a database connection, and specified load/save arguments

```yaml
scooters:
  type: pandas.SQLTableDataset
  credentials: scooters_credentials
  table_name: scooters
  load_args:
    index_col: [name]
    columns: [name, gear]
  save_args:
    if_exists: replace
```

## Load a SQL table with credentials and a database connection, and apply a SQL query to the table


```yaml
scooters_query:
  type: pandas.SQLQueryDataset
  credentials: scooters_credentials
  sql: select * from cars where gear=4
  load_args:
    index_col: [name]
```

When you use [`pandas.SQLTableDataset`](/kedro_datasets.pandas.SQLTableDataset) or [`pandas.SQLQueryDataset`](/kedro_datasets.pandas.SQLQueryDataset), you must provide a database connection string. In the above example, we pass it using the `scooters_credentials` key from the credentials.

Note that `scooters_credentials` must have a top-level key `con` containing a [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) connection string. As an alternative to credentials, you could explicitly put `con` into `load_args` and `save_args` (`pandas.SQLTableDataset` only).


## Load data from an API endpoint

This example uses US corn yield data from USDA.

```yaml
us_corn_yield_data:
  type: api.APIDataset
  url: https://quickstats.nass.usda.gov
  credentials: usda_credentials
  params:
    key: SOME_TOKEN
    format: JSON
    commodity_desc: CORN
    statisticcat_des: YIELD
    agg_level_desc: STATE
    year: 2000
```

Note that `usda_credientials` will be passed as the `auth` argument in the `requests` library. Specify the username and password as a list in your `credentials.yml` file as follows:

```yaml
usda_credentials:
  - username
  - password
```


## Load data from Minio (S3 API Compatible Storage)


```yaml
test:
  type: pandas.CSVDataset
  filepath: s3://your_bucket/test.csv # assume `test.csv` is uploaded to the Minio server.
  credentials: dev_minio
```
In `credentials.yml`, define the `key`, `secret` and the `endpoint_url` as follows:

```yaml
dev_minio:
  key: token
  secret: key
  client_kwargs:
    endpoint_url : 'http://localhost:9000'
```

```{note}
The easiest way to setup MinIO is to run a Docker image. After the following command, you can access the Minio server with `http://localhost:9000` and create a bucket and add files as if it is on S3.
```

`docker run -p 9000:9000 -e "MINIO_ACCESS_KEY=token" -e "MINIO_SECRET_KEY=key" minio/minio server /data`


## Load a model saved as a pickle from Azure Blob Storage

```yaml
ml_model:
  type: pickle.PickleDataset
  filepath: "abfs://models/ml_models.pickle"
  versioned: True
  credentials: dev_abs
```
In the `credentials.yml` file, define the `account_name` and `account_key`:

```yaml
dev_abs:
  account_name: accountname
  account_key: key
```


## Load a CSV file stored in a remote location through SSH

```{note}
This example requires [Paramiko](https://www.paramiko.org) to be installed (`pip install paramiko`).
```
```yaml
cool_dataset:
  type: pandas.CSVDataset
  filepath: "sftp:///path/to/remote_cluster/cool_data.csv"
  credentials: cluster_credentials
```
All parameters required to establish the SFTP connection can be defined through `fs_args` or in the `credentials.yml` file as follows:

```yaml
cluster_credentials:
  username: my_username
  host: host_address
  port: 22
  password: password
```
The list of all available parameters is given in the [Paramiko documentation](https://docs.paramiko.org/en/2.4/api/client.html#paramiko.client.SSHClient.connect).

## Load multiple datasets with similar configuration using YAML anchors

Different datasets might use the same file format, load and save arguments, and be stored in the same folder. [YAML has a built-in syntax](https://yaml.org/spec/1.2.1/#Syntax) for factorising parts of a YAML file, which means that you can decide what is generalisable across your datasets, so that you need not spend time copying and pasting dataset configurations in the `catalog.yml` file.

You can see this in the following example:

```yaml
_csv: &csv
  type: spark.SparkDataset
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

```{note}
It's important that the name of the template entry starts with a `_` so Kedro knows not to try and instantiate it as a dataset.
```

You can also nest reuseable YAML syntax:

```yaml
_csv: &csv
  type: spark.SparkDataset
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

In this example, the default `csv` configuration is inserted into `airplanes` and then the `load_args` block is overridden. Normally, that would replace the whole dictionary. In order to extend `load_args`, the defaults for that block are then re-inserted.

## Read the same file using two different datasets

You might come across a situation where you would like to read the same file using two different dataset implementations (known as transcoding). For example, Parquet files can not only be loaded via the `ParquetDataset` using `pandas`, but also directly by `SparkDataset`. This conversion is typical when coordinating a `Spark` to `pandas` workflow.

Define two `DataCatalog` entries for the same dataset in a common format (Parquet, JSON, CSV, etc.) in your `conf/base/catalog.yml`:

```yaml
my_dataframe@spark:
  type: spark.SparkDataset
  filepath: data/02_intermediate/data.parquet
  file_format: parquet

my_dataframe@pandas:
  type: pandas.ParquetDataset
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

In this example, Kedro understands that `my_dataframe` is the same dataset in its `spark.SparkDataset` and `pandas.ParquetDataset` formats and resolves the node execution order.

In the pipeline, Kedro uses the `spark.SparkDataset` implementation for saving and `pandas.ParquetDataset`
for loading, so the first node outputs a `pyspark.sql.DataFrame`, while the second node receives a `pandas.Dataframe`.

## Create a Data Catalog YAML configuration file via the CLI

You can use the [`kedro catalog create` command to create a Data Catalog YAML configuration](../development/commands_reference.md#create-a-data-catalog-yaml-configuration-file).

This creates a `<conf_root>/<env>/catalog/<pipeline_name>.yml` configuration file with `MemoryDataset` datasets for each dataset in a registered pipeline if it is missing from the `DataCatalog`.

```yaml
# <conf_root>/<env>/catalog/<pipeline_name>.yml
rockets:
  type: MemoryDataset
scooters:
  type: MemoryDataset
```
