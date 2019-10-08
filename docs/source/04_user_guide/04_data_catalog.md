# The Data Catalog

> *Note:* This documentation is based on `Kedro 0.15.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

This section introduces `catalog.yml`, the project-shareable Data Catalog. The file is located in `conf/base` and is a registry of all data sources available for use by a project; it manages loading and saving of data.

## Using the Data Catalog within Kedro configuration

Kedro uses configuration to make your code reproducible when it has to reference datasets in different locations and/or in different environments.

You can copy this file and reference additional locations for the same datasets. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production while copying and updating a second version of `catalog.yml` that can be placed in `conf/local/` to register the locations of sample datasets on the local computer that you are using for prototyping your data pipeline.

There is built-in functionality for `conf/local/` to overwrite `conf/base/` detailed [here](./03_configuration.md). This means that a dataset called `cars` could exist in the `catalog.yml` files in `conf/base/` and `code/local/`. In code, in `src`, you would only call a dataset named `cars` and Kedro would detect which definition of `cars` dataset to use to run your pipeline - `cars` definition from `code/local/catalog.yml` would take precedence in this case.

The Data Catalog also works with the `credentials.yml` in `conf/local/`, allowing you to specify usernames and passwords that are required to load certain datasets.

The are two ways of defining a Data Catalog: through the use of YAML configuration, or programmatically using an API. Both methods allow you to specify:

 - Dataset name
 - Dataset type
 - Location of the dataset (includes file paths, S3 bucket locations and more)
 - Credentials needed in order to access the dataset
 - Load and saving arguments
 - Whether or not you want a [dataset or ML model to be versioned](./08_advanced_io.md#versioning) when you run your data pipeline

## Using the Data Catalog with the YAML API

The YAML API allows you to configure your datasets in a YAML configuration file, `conf/base/catalog.yml` or `conf/local/catalog.yml`.

Here is an example data config `catalog.yml`:

```yaml
# Example 1: Loads a local csv file
bikes:
  type: CSVLocalDataSet
  filepath: "data/01_raw/bikes.csv"

# Example 2: Loads and saves a local csv file using specified load and save arguments
cars:
  type: CSVLocalDataSet
  filepath: data/01_raw/company/cars.csv
  load_args:
    sep: ','
  save_args:
    index: False
    date_format: '%Y-%m-%d %H:%M'
    decimal: '.'

# Example 3: Loads a csv file from a specific S3 bucket that requires credentials and additional load arguments
motorbikes:
  type: CSVS3DataSet
  filepath: data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  bucket_name: test_bucket
  load_args:
    sep: ','
    skiprows: 5
    skipfooter: 1
    na_values: ['#NA', 'NA']

# Example 4: Loads a local pickle dataset
airplanes:
  type: PickleLocalDataSet
  filepath: data/06_models/airplanes.pkl
  backend: pickle

# Example 5: Loads a local hdf dataset, specifies the selection of certain columns to be loaded as well as overwriting the file when saving
skateboards:
  type: HDFLocalDataSet
  filepath: data/02_intermediate/skateboards.hdf
  key: name
  load_args:
    columns: ['brand', 'length']
  save_args:
    mode: 'w'  # Overwrite even when the file already exists
    dropna: True

# Example 6: Loads a local parquet dataset with load and save arguments
trucks:
  type: ParquetLocalDataSet
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

# Example 7: Loads a SQL table with credentials, load and save arguments
scooters:
  type: SQLTableDataSet
  credentials: scooters_credentials
  table_name: scooters
  load_args:
    index_col: ['name']
    columns: ['name', 'gear']
  save_args:
    if_exists: 'replace'

# Example 8: Load a SQL table with credentials and applies a SQL query to the table
scooters_query:
  type: SQLQueryDataSet
  credentials: scooters_credentials
  sql: 'select * from cars where gear=4'
  load_args:
    index_col: ['name']
```

> *Note:* When using `SQLTableDataSet` or `SQLQueryDataSet` you must provide a database connection string. In the example above we pass it using `scooters_credentials` key from the credentials (see the details in [Feeding in credentials](#feeding-in-credentials) section below). `scooters_credentials` must have a top-level key `con` containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) connection string. Alternative to credentials would be to explicitly put `con` into `load_args` and `save_args` (`SQLTableDataSet` only).

## Feeding in credentials

Before instantiating the `DataCatalog` Kedro will first attempt to read the credentials from project configuration (see [this section](./03_configuration.md#aws-credentials) for more details). Resulting dictionary will then be passed into `DataCatalog.from_config()` as `credentials` argument.

Let's assume that the project contains the file `conf/local/credentials.yml` with the following contents:

```yaml
dev_s3:
  aws_access_key_id: token
  aws_secret_access_key: key

scooters_credentials:
  con: sqlite:///kedro.db
```

In the example above `catalog.yml` contains references to credentials keys `dev_s3` and `scooters_credentials`. It means that when instantiating `motorbikes` dataset, for example, the `DataCatalog` will attempt to read top-level key `dev_s3` from the received `credentials` dictionary, and then will pass its values into the dataset `__init__` as `credentials` argument. This is essentially equivalent to calling this:

```python
CSVS3DataSet(
    bucket_name="test_bucket",
    filepath="data/02_intermediate/company/motorbikes.csv",
    load_args=dict(
        sep=",",
        skiprows=5,
        skipfooter=1,
        na_values=["#NA", "NA"],
    ),
    credentials=dict(
        aws_access_key_id="token",
        aws_secret_access_key="key",
    )
)
```


## Loading multiple datasets that have similar configuration

You may encounter situations where your datasets use the same file format, load and save arguments, and are stored in the same folder. YAML has a [built-in syntax](https://yaml.org/spec/1.2/spec.html#id2765878) for factorising parts of a YAML file, which means that you can decide what is generalisable across your datasets so that you do not have to spend time copying and pasting dataset configurations in `catalog.yml`.

You can see this in the following example:

```yaml
_csv: &csv
  type: kedro.contrib.io.pyspark.spark_data_set.SparkDataSet
  file_format: 'csv'
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
  type: kedro.contrib.io.pyspark.spark_data_set.SparkDataSet
  file_format: 'csv'
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

You may come across a situation where you would like to read the same file using two different dataset implementations. For instance, `parquet` files can not only be loaded via the `ParquetLocalDataSet`, but also directly by `SparkDataSet` using `pandas`. To do this, you can define your `catalog.yml` as follows:

```yaml
mydata@pandas:
  type: ParquetLocalDataSet
  filepath: data/01_raw/data.parquet

mydata@spark:
    type: kedro.contrib.io.pyspark.SparkDataSet
    filepath: data/01_raw/data.parquet
```

In your pipeline, you may refer to either dataset as input or output, and it will ensure the dependencies point to a single dataset `mydata` both while running the pipeline and in the visualisation.


## Transforming datasets

If you need to augment the loading and / or saving of one or more datasets you can use the transformer API. To do this create a subclass of `AbstractTransformer` that implements your changes and then apply it to your catalog with `DataCatalog.add_transformer`. For example to print the runtimes of load and save operations you could do this:

```python
class PrintTimeTransformer(AbstractTransformer):
    def load(self, data_set_name: str, load: Callable[[], Any]) -> Any:
        start = time.time()
        data = load()
        print("Loading {} took {:0.3f}s".format(data_set_name, time.time() - start))
        return data

    def save(self, data_set_name: str, save: Callable[[Any], None], data: Any) -> None:
        start = time.time()
        save(data)
        print("Saving {} took {:0.3}s".format(data_set_name, time.time() - start))

catalog.add_transformer(PrintTimeTransformer())
```

By default transformers are applied to all datasets in the catalog (including any that are added in the future). The `DataCatalog.add_transformers` method has an additional argument `data_set_names` that lets you limit which data sets the transformer will be applied to.

## Versioning datasets and ML models

Making a simple addition to your Data Catalog allows you to perform versioning of datasets and machine learning models.

Consider the following versioned dataset defined in the `catalog.yml`:

```yaml
cars.csv:
  type: CSVLocalDataSet
  filepath: data/01_raw/company/cars.csv
  versioned: true
```

The `DataCatalog` will create a versioned `CSVLocalDataSet` called `cars.csv`. The actual csv file location will look like `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` corresponds to a global save version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

You can run the pipeline with a particular versioned data set with `--load-version` flag as follows:

```bash
kedro run --load-version="cars.csv:YYYY-MM-DDThh.mm.ss.sssZ"
```
where `--load-version` is dataset name and version timestamp separated by `:`.

This section shows just the very basics of versioning. You can learn more about how this feature can be used in [Advanced IO](./08_advanced_io.md#versioning).

## Using the Data Catalog with the Code API

The code API allows you to configure data sources in code. This can also be used to operate the IO module within notebooks.

## Configuring a data catalog

In a file like `catalog.py`, you can generate the Data Catalog. This will allow everyone in the project to review all the available data sources. In the following, we are using the pre-built CSV loader, which is documented in the API reference documentation: [CSVLocalDataSet](/kedro.io.CSVLocalDataSet)

```python
from kedro.io import DataCatalog, CSVLocalDataSet, SQLTableDataSet, SQLQueryDataSet, ParquetLocalDataSet

io = DataCatalog({
  'bikes': CSVLocalDataSet(filepath='../data/01_raw/bikes.csv'),
  'cars': CSVLocalDataSet(filepath='../data/01_raw/cars.csv', load_args=dict(sep=',')), # additional arguments
  'cars_table': SQLTableDataSet(table_name="cars", credentials=dict(con="sqlite:///kedro.db")),
  'scooters_query': SQLQueryDataSet(sql="select * from cars where gear=4", credentials=dict(con="sqlite:///kedro.db")),
  'ranked': ParquetLocalDataSet(filepath="ranked.parquet")
})
```

> *Note:* When using `SQLTableDataSet` or `SQLQueryDataSet` you must provide a `con` key containing [SQLAlchemy compatible](https://docs.sqlalchemy.org/en/13/core/engines.html#database-urls) database connection string. In the example above we pass it as part of `credentials` argument. Alternative to `credentials` would be to put `con` into `load_args` and `save_args` (`SQLTableDataSet` only).

## Loading datasets

Each dataset can be accessed by its name.

```python
cars = io.load('cars') # data is now loaded as a DataFrame in 'cars'
gear = cars['gear'].values
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
io.add('cars_cache', memory)
io.save('cars_cache', 'Memory can store anything.')
io.load('car_cache')
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

io.save('cars_table', cars)
ranked = io.load('scooters_query')[['brand', 'mpg']]
```

### Saving data in parquet

Finally we can save the processed data in Parquet format.

```python
io.save('ranked', ranked)
```

### Creating your own dataset
More specialised datasets can be found in `contrib/io`. [Creating new datasets](../03_tutorial/03_set_up_data.md#creating-custom-datasets) is the easiest way to contribute to the Kedro project.
