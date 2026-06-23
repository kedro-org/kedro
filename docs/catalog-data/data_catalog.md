# Introduction to the Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. It is specified with a YAML catalog file that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

This page introduces the basic sections of `catalog.yml`, the file Kedro uses to register data sources for a project. It also explains the key concepts behind how the catalog organises and loads data.

!!! warning
    Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.
    From version **`2.0.0`** of `kedro-datasets`, all dataset names have changed to replace the capital letter "S" in "DataSet" with a lower case "s". For example, `CSVDataSet` is now `CSVDataset`.

For step-by-step instructions on configuring a catalog (load and save arguments, credentials, versioning, multiple environments), see the [how-to guide](how_to_configure_the_data_catalog.md).

## The basics of `catalog.yml`

A separate page of [Data Catalog YAML examples](./data_catalog_yaml_examples.md) gives further examples of how to work with `catalog.yml`, but here we revisit the [basic `catalog.yml` introduced by the spaceflights tutorial](../tutorials/set_up_data.md).

The example below registers two `csv` datasets and one `xlsx` dataset. To load or save a file within the local file system you must provide the dataset name (`key`), specify the dataset class through `type`, and set the file location using `filepath`.

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

### Configuring dataset parameters in `catalog.yml`

The dataset configuration in `catalog.yml` is defined as follows:

1. The top-level key is the dataset name used as a dataset identifier in the catalog - `shuttles`, `weather` in the example below.
2. The next level includes multiple keys. The first mandatory key is `type`, which declares the dataset type to use.
The rest of the keys are dataset parameters and vary depending on the implementation.
To get the extensive list of dataset parameters, see the [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) and navigate to the `__init__` method of the target dataset.
3. Some dataset parameters can be further configured depending on the libraries underlying the dataset implementation.
In the example below, a configuration of the `shuttles` dataset includes the `load_args` parameter which is defined by the `pandas` option for loading CSV files.
While the `save_args` parameter in a configuration of the `weather` dataset is defined by the `snowpark` `saveAsTable` method.
To get the extensive list of dataset parameters, see the [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) and navigate to the target parameter in the `__init__` definition for the dataset.
For those parameters we provide a reference to the underlying library configuration parameters. For example, under the `load_args` parameter section for [pandas.ExcelDataset](https://docs.kedro.org/projects/kedro-datasets/en/stable/api/kedro_datasets/pandas.ExcelDataset/) you can find a reference to the [pandas.read_excel](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html) method defining the full set of the parameters accepted.

!!! note
    Kedro datasets delegate any of the `load_args` / `save_args` directly to the underlying implementation.

The example below showcases the configuration of two datasets - `shuttles` of type [pandas.ExcelDataset](https://docs.kedro.org/projects/kedro-datasets/en/stable/api/kedro_datasets/pandas.ExcelDataset/) and `weather` of type [snowflake.SnowparkTableDataset](https://docs.kedro.org/projects/kedro-datasets/en/stable/api/kedro_datasets/snowflake.SnowparkTableDataset/).

```yaml
shuttles: # Dataset name
  type: pandas.ExcelDataset # Dataset type
  filepath: data/01_raw/shuttles.xlsx # pandas.ExcelDataset parameter
  load_args: # pandas.ExcelDataset parameter
    engine: openpyxl # Pandas option for loading CSV files

weather: # Dataset name
  type: snowflake.SnowparkTableDataset # Dataset type
  table_name: "weather_data"
  database: "meteorology"
  schema: "observations"
  credentials: snowflake_client
  save_args: # snowflake.SnowparkTableDataset parameter
    mode: overwrite # Snowpark saveAsTable input option
    column_order: name
    table_type: ''
```


### Dataset `type`

Kedro supports a range of connectors, for CSV files, Excel spreadsheets, Parquet files, Feather files, HDF5 files, JSON documents, pickled objects, SQL tables, SQL queries, and more. They are supported using libraries such as pandas, PySpark, NetworkX, and Matplotlib.

[kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) contains a comprehensive list of all available file types.

### Dataset `filepath`

Kedro relies on [`fsspec`](https://filesystem-spec.readthedocs.io/en/latest/) to read and save data from a variety of data stores including local file systems, network file systems, cloud object stores, and Hadoop. When specifying a storage location in `filepath:`, you should provide a URL using the general form `protocol://path/to/data`.  If no protocol is provided, the local file system is assumed (which is the same as ``file://``).

The following protocols are available:

- **Local or Network File System**: `file://` - the local file system is default in the absence of any protocol, it also permits relative paths.
- **Hadoop File System (HDFS)**: `hdfs://user@server:port/path/to/data` - Hadoop Distributed File System, for resilient, replicated files within a cluster.
- **Amazon S3**: `s3://my-bucket-name/path/to/data` - Amazon S3 remote binary store, often used with Amazon EC2,
  using the library s3fs.
- **S3 Compatible Storage**: `s3://my-bucket-name/path/_to/data` - for example, MinIO, using the s3fs library.
- **Google Cloud Storage**: `gcs://` - Google Cloud Storage, typically used with Google Compute
  resource using `gcsfs` (in development).
- **Azure Blob Storage / Azure Data Lake Storage Gen2**: `abfs://` - Azure Blob Storage, typically used when working on an Azure environment.
- **HTTP(s)**: ``http://`` or ``https://`` for reading data directly from HTTP web servers.

`fsspec` also provides other file systems, such as SSH, FTP, and WebHDFS. [See the fsspec documentation for more information](https://filesystem-spec.readthedocs.io/en/latest/api.html#implementations).


## Additional settings in `catalog.yml`

Beyond `type` and `filepath`, the catalog accepts several other groups of settings that change how a dataset is loaded, saved, or accessed. The most common are summarised below; see [how to configure the Data Catalog](how_to_configure_the_data_catalog.md) for worked examples.

### Load, save and filesystem arguments

The catalog accepts three groups of `*_args` parameters:

* **`load_args` and `save_args`**: control how the underlying third-party library loads or saves data. For example, `load_args` for a [`pandas.ExcelDataset`](https://docs.kedro.org/projects/kedro-datasets/en/stable/api/kedro_datasets/pandas.ExcelDataset/) is passed to [`pandas.read_excel`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_excel.html) as keyword arguments.
* **`fs_args`**: control how Kedro interacts with the filesystem itself. Top-level keys are passed to the underlying filesystem class (for example, `GCSFileSystem` for Google Cloud Storage), while `open_args_load` and `open_args_save` are forwarded to the filesystem's `open` method to control how the file is opened during a load or save.

!!! note
    Default load, save and filesystem arguments are defined inside each dataset implementation as `DEFAULT_LOAD_ARGS`, `DEFAULT_SAVE_ARGS`, and `DEFAULT_FS_ARGS`. Check the [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) for the defaults that apply to a particular dataset.

For examples of each, see [how to specify load, save and filesystem arguments](how_to_configure_the_data_catalog.md#how-to-specify-load-save-and-filesystem-arguments).

### Dataset access credentials

The Data Catalog reads credentials from `credentials.yml` (typically in `conf/local/`) and passes them into the dataset constructor. Before instantiating the `DataCatalog`, Kedro first attempts to read [the credentials from the project configuration](../configure/parameters_and_credentials_explanation.md#credentials). The resulting dictionary is then passed into `DataCatalog.from_config()` as the `credentials` argument.

A `catalog.yml` entry refers to a credentials block by name through a top-level `credentials:` key. The Data Catalog looks up the matching block in the credentials dictionary and passes its values into the dataset as the `credentials` argument to `__init__`.

For a worked example, see [how to use credentials with the Data Catalog](how_to_configure_the_data_catalog.md#how-to-use-credentials-with-the-data-catalog).

### Dataset versioning

Kedro enables dataset and ML model versioning through the `versioned: True` flag in a catalog entry. When versioning is enabled, the `filepath` is used as the basis of a folder that stores versions of the dataset. Each time a new version is created by a pipeline run, it is stored within `<filepath>/<version>/<filename>`, where `<version>` is a timestamp formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

By default, `kedro run` loads the latest version of a versioned dataset. See [how to version a dataset](how_to_configure_the_data_catalog.md#how-to-version-a-dataset) for the steps to enable versioning, load a specific version, and list available versions.

A dataset supports versioning if it extends the [kedro.io.AbstractVersionedDataset][] class to accept a `version` keyword argument as part of the constructor and adapts the `_save` and `_load` methods to use the versioned data path obtained from `_get_save_path` and `_get_load_path` respectively.

To verify whether a dataset supports versioning, examine the dataset class code to inspect its inheritance [(you can find contributed datasets within the `kedro-datasets` repository)](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets/kedro_datasets). Check whether the dataset class inherits from `AbstractVersionedDataset`. For example, a class declared as `CSVDataset(AbstractVersionedDataset[pd.DataFrame, pd.DataFrame])` is set up to support versioning.

!!! note
    HTTP(S) is a supported file system in the dataset implementations, but it cannot be combined with versioning.

## Use the Data Catalog within Kedro configuration

Kedro configuration enables you to organise your project for different stages of your data pipeline. For example, you might need different Data Catalog settings for development, testing, and production environments.

By default, Kedro has a `base` and a `local` folder for configuration. The Data Catalog configuration is loaded by a configuration loader class. This class recursively scans for configuration files inside the `conf` folder, firstly in `conf/base` and then in `conf/local` (the designated overriding environment). Kedro merges the configuration and returns a dictionary. See the [configuration documentation](../configure/configuration_explanation.md) for the full rules.

In summary, if you need to configure your datasets for different environments, you can create both `conf/base/catalog.yml` and `conf/local/catalog.yml`. For instance, you can use the `catalog.yml` file in `conf/base/` to register the locations of datasets that would run in production, while adding a second version of `catalog.yml` in `conf/local/` to register the locations of sample datasets while you are using them for prototyping data pipeline(s).

For a worked example with `conf/base` and `conf/local` overrides, see [how to configure datasets across environments](how_to_configure_the_data_catalog.md#how-to-configure-datasets-across-environments).
