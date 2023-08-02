
# Introduction to the Kedro Data Catalog

This section introduces `catalog.yml`, the project-shareable Data Catalog. The file is located in `conf/base` and is a registry of all data sources available for use by a project; it manages loading and saving of data.

All supported data connectors are available in [`kedro-datasets`](/kedro_datasets).

## Use the Data Catalog within Kedro configuration

Kedro uses configuration to make your code reproducible when it has to reference datasets in different locations and/or in different environments.

You can copy this file and reference additional locations for the same datasets. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production, while copying and updating a second version of `catalog.yml` in `conf/local/` to register the locations of sample datasets that you are using for prototyping your data pipeline(s).

Built-in functionality for `conf/local/` to overwrite `conf/base/` is [described in the documentation about configuration](../configuration/configuration_basics.md). This means that a dataset called `cars` could exist in the `catalog.yml` files in `conf/base/` and `conf/local/`. In code, in `src`, you would only call a dataset named `cars` and Kedro would detect which definition of `cars` dataset to use to run your pipeline - `cars` definition from `conf/local/catalog.yml` would take precedence in this case.

The Data Catalog also works with the `credentials.yml` file in `conf/local/`, allowing you to specify usernames and passwords required to load certain datasets.

You can define a Data Catalog in two ways - through YAML configuration, or programmatically using an API. Both methods allow you to specify:

 - Dataset name
 - Dataset type
 - Location of the dataset using `fsspec`, detailed in the next section
 - Credentials needed to access the dataset
 - Load and saving arguments
 - Whether you want a [dataset or ML model to be versioned](kedro_io.md#versioning) when you run your data pipeline

## Specify the location of the dataset

Kedro relies on [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read and save data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. When specifying a storage location in `filepath:`, you should provide a URL using the general form `protocol://path/to/data`.  If no protocol is provided, the local file system is assumed (same as ``file://``).

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




```{toctree}
:maxdepth: 1

data_catalog_yaml_examples
data_catalog_basic_how_to
partitioned_and_incremental_datasets
advanced_data_catalog_usage
how_to_create_a_custom_dataset
```
