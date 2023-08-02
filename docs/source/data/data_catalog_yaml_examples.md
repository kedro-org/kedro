# Data Catalog YAML examples

You can configure your datasets in a YAML configuration file, `conf/base/catalog.yml` or `conf/local/catalog.yml`.

Here are some examples of data configuration in a `catalog.yml`:

Data Catalog accepts two different groups of `*_args` parameters that serve different purposes:
- `fs_args`
- `load_args` and `save_args`

The `fs_args` is used to configure the interaction with a filesystem.
All the top-level parameters of `fs_args` (except `open_args_load` and `open_args_save`) will be passed in an underlying filesystem class.

**Provide the `project` value to the underlying filesystem class (`GCSFileSystem`) to interact with Google Cloud Storage (GCS)
**
```yaml
test_dataset:
  type: ...
  fs_args:
    project: test_project
```

The `open_args_load` and `open_args_save` parameters are passed to the filesystem's `open` method to configure how a dataset file (on a specific filesystem) is opened during a load or save operation, respectively.

**Load data from a local binary file using `utf-8` encoding
**
```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_load:
      mode: "rb"
      encoding: "utf-8"
```

`load_args` and `save_args` configure how a third-party library (e.g. `pandas` for `CSVDataSet`) loads/saves data from/to a file.

**Save data to a CSV file without row names (index) using `utf-8` encoding
**
```yaml
test_dataset:
  type: pandas.CSVDataSet
  ...
  save_args:
    index: False
    encoding: "utf-8"
```

## Load / save a CSV file from / to a local file system

```yaml
bikes:
  type: pandas.CSVDataSet
  filepath: data/01_raw/bikes.csv
```

## Load / save a CSV on a local file system, using specified load / save arguments

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

## Load / save a compressed CSV on a local file system

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

## Load a CSV file from a specific S3 bucket, using credentials and load arguments

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

## Load / save a pickle file from / to a local file system

```yaml
airplanes:
  type: pickle.PickleDataSet
  filepath: data/06_models/airplanes.pkl
  backend: pickle
```

## Load an Excel file from Google Cloud Storage

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

## Load a multi-sheet Excel file from a local file system

```yaml
trains:
  type: pandas.ExcelDataSet
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


## Load / save an HDF file on local file system storage, using specified load / save arguments

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

## Load / save a parquet file on local file system storage, using specified load / save arguments

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


## Load / save a Spark table on S3, using specified load / save arguments

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


## Load / save a SQL table using credentials, a database connection, using specified load / save arguments

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

## Load an SQL table with credentials, a database connection, and applies a SQL query to the table


```yaml
scooters_query:
  type: pandas.SQLQueryDataSet
  credentials: scooters_credentials
  sql: select * from cars where gear=4
  load_args:
    index_col: [name]
```

When you use [`pandas.SQLTableDataSet`](/kedro_datasets.pandas.SQLTableDataSet) or [`pandas.SQLQueryDataSet`](/kedro_datasets.pandas.SQLQueryDataSet), you must provide a database connection string. In the above example, we pass it using the `scooters_credentials` key from the credentials (see the details in the [Feeding in credentials](#feeding-in-credentials) section below). `scooters_credentials` must have a top-level key `con` containing a [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) connection string. As an alternative to credentials, you could explicitly put `con` into `load_args` and `save_args` (`pandas.SQLTableDataSet` only).


## Load data from an API endpoint, example US corn yield data from USDA

```yaml
us_corn_yield_data:
  type: api.APIDataSet
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
  type: pandas.CSVDataSet
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
  type: pickle.PickleDataSet
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
  type: pandas.CSVDataSet
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

```{note}
It's important that the name of the template entry starts with a `_` so Kedro knows not to try and instantiate it as a dataset.
```

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

In this example, the default `csv` configuration is inserted into `airplanes` and then the `load_args` block is overridden. Normally, that would replace the whole dictionary. In order to extend `load_args`, the defaults for that block are then re-inserted.

## Load multiple datasets with similar configuration using dataset factories
For catalog entries that share configuration details, you can also use the dataset factories introduced in Kedro 0.18.12. This syntax allows you to generalise the configuration and
reduce the number of similar catalog entries by matching datasets used in your project's pipelines to dataset factory patterns.

### Generalise datasets with similar names and types into one dataset factory
Consider the following catalog entries:
```yaml
factory_data:
  type: pandas.CSVDataSet
  filepath: data/01_raw/factory_data.csv


process_data:
  type: pandas.CSVDataSet
  filepath: data/01_raw/process_data.csv
```
The datasets in this catalog can be generalised to the following dataset factory:
```yaml
"{name}_data":
  type: pandas.CSVDataSet
  filepath: data/01_raw/{name}_data.csv
```
When `factory_data` or `process_data` is used in your pipeline, it is matched to the factory pattern `{name}_data`. The factory pattern must always be enclosed in
quotes to avoid YAML parsing errors.


### Generalise datasets of the same type into one dataset factory
You can also combine all the datasets with the same type and configuration details. For example, consider the following
catalog with three datasets named `boats`, `cars` and `planes` of the type `pandas.CSVDataSet`:
```yaml
boats:
  type: pandas.CSVDataSet
  filepath: data/01_raw/shuttles.csv

cars:
  type: pandas.CSVDataSet
  filepath: data/01_raw/reviews.csv

planes:
  type: pandas.CSVDataSet
  filepath: data/01_raw/companies.csv
```
These datasets can be combined into the following dataset factory:
```yaml
"{dataset_name}#csv":
  type: pandas.CSVDataSet
  filepath: data/01_raw/{dataset_name}.csv
```
You will then have to update the pipelines in your project located at `src/<project_name>/<pipeline_name>/pipeline.py` to refer to these datasets as `boats#csv`,
`cars#csv` and `planes#csv`. Adding a suffix or a prefix to the dataset names and the dataset factory patterns, like `#csv` here, ensures that the dataset
names are matched with the intended pattern.
```python
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preprocess_boats,
                inputs="boats#csv",
                outputs="preprocessed_boats",
                name="preprocess_boats_node",
            ),
            node(
                func=preprocess_cars,
                inputs="cars#csv",
                outputs="preprocessed_cars",
                name="preprocess_cars_node",
            ),
            node(
                func=preprocess_planes,
                inputs="planes#csv",
                outputs="preprocessed_planes",
                name="preprocess_planes_node",
            ),
            node(
                func=create_model_input_table,
                inputs=[
                    "preprocessed_boats",
                    "preprocessed_planes",
                    "preprocessed_cars",
                ],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```
### Generalise datasets using namespaces into one dataset factory
You can also generalise the catalog entries for datasets belonging to namespaced modular pipelines. Consider the
following pipeline which takes in a `model_input_table` and outputs two regressors belonging to the
`active_modelling_pipeline` and the `candidate_modelling_pipeline` namespaces:
```python
from kedro.pipeline import Pipeline, node
from kedro.pipeline.modular_pipeline import pipeline

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    pipeline_instance = pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "y_train"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
        ]
    )
    ds_pipeline_1 = pipeline(
        pipe=pipeline_instance,
        inputs="model_input_table",
        namespace="active_modelling_pipeline",
    )
    ds_pipeline_2 = pipeline(
        pipe=pipeline_instance,
        inputs="model_input_table",
        namespace="candidate_modelling_pipeline",
    )

    return ds_pipeline_1 + ds_pipeline_2
```
You can now have one dataset factory pattern in your catalog instead of two separate entries for `active_modelling_pipeline.regressor`
and `candidate_modelling_pipeline.regressor` as below:
```yaml
{namespace}.regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor_{namespace}.pkl
  versioned: true
```
### Generalise datasets of the same type in different layers into one dataset factory with multiple placeholders

You can use multiple placeholders in the same pattern. For example, consider the following catalog where the dataset
entries share `type`, `file_format` and `save_args`:
```yaml
processing.factory_data:
  type: spark.SparkDataSet
  filepath: data/processing/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

processing.process_data:
  type: spark.SparkDataSet
  filepath: data/processing/process_data.pq
  file_format: parquet
  save_args:
    mode: overwrite

modelling.metrics:
  type: spark.SparkDataSet
  filepath: data/modelling/factory_data.pq
  file_format: parquet
  save_args:
    mode: overwrite
```
This could be generalised to the following pattern:
```yaml
"{layer}.{dataset_name}":
  type: spark.SparkDataSet
  filepath: data/{layer}/{dataset_name}.pq
  file_format: parquet
  save_args:
    mode: overwrite
```
All the placeholders used in the catalog entry body must exist in the factory pattern name.

### Generalise datasets using multiple dataset factories
You can have multiple dataset factories in your catalog. For example:
```yaml
"{namespace}.{dataset_name}@spark":
  type: spark.SparkDataSet
  filepath: data/{namespace}/{dataset_name}.pq
  file_format: parquet

"{dataset_name}@csv":
  type: pandas.CSVDataSet
  filepath: data/01_raw/{dataset_name}.csv
```

Having multiple dataset factories in your catalog can lead to a situation where a dataset name from your pipeline might
match multiple patterns. To overcome this, Kedro sorts all the potential matches for the dataset name in the pipeline and picks the best match.
The matches are ranked according to the following criteria :
1. Number of exact character matches between the dataset name and the factory pattern. For example, a dataset named `factory_data$csv` would match `{dataset}_data$csv` over `{dataset_name}$csv`.
2. Number of placeholders. For example, the dataset `preprocessing.shuttles+csv` would match `{namespace}.{dataset}+csv` over `{dataset}+csv`.
3. Alphabetical order

### Generalise all datasets with a catch-all dataset factory to overwrite the default `MemoryDataSet`
You can use dataset factories to define a catch-all pattern which will overwrite the default `MemoryDataSet` creation.
```yaml
"{default_dataset}":
  type: pandas.CSVDataSet
  filepath: data/{default_dataset}.csv

```
Kedro will now treat all the datasets mentioned in your project's pipelines that do not appear as specific patterns or explicit entries in your catalog
as `pandas.CSVDataSet`.
