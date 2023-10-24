# Introduction to the Data Catalog


In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. It is specified with a YAML catalog file that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

This page introduces the basic sections of `catalog.yml`, which is the file Kedro uses to register data sources for a project.

```{warning}
Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.
```

## The basics of `catalog.yml`
A separate page of [Data Catalog YAML examples](./data_catalog_yaml_examples.md)  gives further examples of how to work with `catalog.yml`, but here we revisit the [basic `catalog.yml` introduced by the spaceflights tutorial](../tutorial/set_up_data.md).

The example below registers two `csv` datasets, and an `xlsx` dataset. The minimum details needed to load and save a file within a local file system are the key, which is name of the dataset, the type of data to indicate the dataset to use (`type`) and the file's location (`filepath`).

```yaml
companies:
  type: pandas.CSVDataset
  filepath: data/01_raw/companies.csv

reviews:
  type: pandas.CSVDataset
  filepath: data/01_raw/reviews.csv

shuttles:
  type: pandas.ExcelDataset
  filepath: data/01_raw/shuttles.xlsx
  load_args:
    engine: openpyxl # Use modern Excel engine (the default since Kedro 0.18.0)
```
### Dataset `type`

Kedro offers a range of datasets, including CSV, Excel, Parquet, Feather, HDF5, JSON, Pickle, SQL Tables, SQL Queries, Spark DataFrames and more. They are supported with the APIs of pandas, spark, networkx, matplotlib, yaml and more.

[The `kedro-datasets` package documentation](/kedro_datasets) contains a comprehensive list of all available file types.

### Dataset `filepath`

Kedro relies on [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read and save data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. When specifying a storage location in `filepath:`, you should provide a URL using the general form `protocol://path/to/data`.  If no protocol is provided, the local file system is assumed (which is the same as ``file://``).

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

`fsspec` also provides other file systems, such as SSH, FTP and WebHDFS. [See the fsspec documentation for more information](https://filesystem-spec.readthedocs.io/en/latest/api.html#implementations).


## Additional settings in `catalog.yml`

This section explains the additional settings available within `catalog.yml`.

### Load and save arguments
The Kedro Data Catalog also accepts two different groups of `*_args` parameters that serve different purposes:

* **`load_args` and `save_args`**: Configures how a third-party library loads/saves data from/to a file. In the spaceflights example above, `load_args`, is passed to the excel file read method (`pd.read_excel`) as a [keyword argument](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html). Although not specified here, the equivalent output is `save_args` and the value would be passed to [`pd.DataFrame.to_excel` method](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_excel.html).

For example, to load or save a CSV on a local file system, using specified load/save arguments:

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

* **`fs_args`**: Configures the interaction with a filesystem.
All the top-level parameters of `fs_args` (except `open_args_load` and `open_args_save`) will be passed to an underlying filesystem class.

For example, to provide the `project` value to the underlying filesystem class (`GCSFileSystem`) to interact with Google Cloud Storage:

```yaml
test_dataset:
  type: ...
  fs_args:
    project: test_project
```

The `open_args_load` and `open_args_save` parameters are passed to the filesystem's `open` method to configure how a dataset file (on a specific filesystem) is opened during a load or save operation, respectively.

For example, to load data from a local binary file using `utf-8` encoding:

```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_load:
      mode: "rb"
      encoding: "utf-8"
```

### Dataset access credentials
The Data Catalog also works with the `credentials.yml` file in `conf/local/`, allowing you to specify usernames and passwords required to load certain datasets.

Before instantiating the `DataCatalog`, Kedro will first attempt to read [the credentials from the project configuration](../configuration/credentials.md). The resulting dictionary is then passed into `DataCatalog.from_config()` as the `credentials` argument.

Let's assume that the project contains the file `conf/local/credentials.yml` with the following contents:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: key
    aws_secret_access_key: secret
```

and the Data Catalog is specified in `catalog.yml` as follows:

```yaml
motorbikes:
  type: pandas.CSVDataset
  filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  load_args:
    sep: ','
```
In the example above, the `catalog.yml` file contains references to credentials keys `dev_s3`. The Data Catalog first reads `dev_s3` from the received `credentials` dictionary, and then passes its values into the dataset as a `credentials` argument to `__init__`.


### Dataset versioning


Kedro enables dataset and ML model versioning through the `versioned` definition. For example:

```yaml
cars:
  type: pandas.CSVDataset
  filepath: data/01_raw/company/cars.csv
  versioned: True
```

In this example, `filepath` is used as the basis of a folder that stores versions of the `cars` dataset. Each time a new version is created by a pipeline run it is stored within `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` corresponds to a version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

By default, `kedro run` loads the latest version of the dataset. However, you can also specify a particular versioned data set with `--load-version` flag as follows:

```bash
kedro run --load-version=cars:YYYY-MM-DDThh.mm.ss.sssZ
```
where `--load-version` is dataset name and version timestamp separated by `:`.

A dataset offers versioning support if it extends the [`AbstractVersionedDataset`](/kedro.io.AbstractVersionedDataset) class to accept a version keyword argument as part of the constructor and adapt the `_save` and `_load` method to use the versioned data path obtained from `_get_save_path` and `_get_load_path` respectively.

To verify whether a dataset can undergo versioning, you should examine the dataset class code to inspect its inheritance [(you can find contributed datasets within the `kedro-datasets` repository)](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets/kedro_datasets). Check if the dataset class inherits from the `AbstractVersionedDataset`. For instance, if you encounter a class like `CSVDataset(AbstractVersionedDataset[pd.DataFrame, pd.DataFrame])`, this indicates that the dataset is set up to support versioning.

```{note}
Note that HTTP(S) is a supported file system in the dataset implementations, but if you it, you can't also use versioning.
```

## Use the Data Catalog within Kedro configuration

Kedro configuration enables you to organise your project for different stages of your data pipeline. For example, you might need different Data Catalog settings for development, testing, and production environments.

By default, Kedro has a `base` and a `local` folder for configuration. The Data Catalog configuration is loaded using a configuration loader class which recursively scans for configuration files inside the `conf` folder, firstly in `conf/base` and then in `conf/local` (which is the designated overriding environment). Kedro merges the configuration information and returns a configuration dictionary according to rules set out in the [configuration documentation](../configuration/configuration_basics.md).

In summary, if you need to configure your datasets for different environments, you can create both `conf/base/catalog.yml` and `conf/local/catalog.yml`. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production, while adding a second version of `catalog.yml` in `conf/local/` to register the locations of sample datasets while you are using them for prototyping data pipeline(s).

To illustrate this, consider the following catalog entry for a dataset named `cars` in `conf/base/catalog.yml`, which points to a csv file stored in a bucket on AWS S3:
```yaml
cars:
  filepath: s3://my_bucket/cars.csv
  type: pandas.CSVDataset
 ```
You can overwrite this catalog entry in `conf/local/catalog.yml` to point to a locally stored file instead:
```yaml
cars:
  filepath: data/01_raw/cars.csv
  type: pandas.CSVDataset
```
In your pipeline code, when the `cars` dataset is used, it will use the overwritten catalog entry from `conf/local/catalog.yml` and rely on Kedro to detect which definition of `cars` dataset to use in your pipeline.
