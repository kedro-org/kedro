# How to configure the Data Catalog

This guide shows how to configure the most common settings on a Data Catalog entry: load and save arguments, filesystem arguments, credentials, dataset versioning, and how to override entries across configuration environments.

For an explanation of the concepts these settings are based on, see the [Data Catalog introduction](data_catalog.md). For a wider range of YAML recipes (load from S3, GCS, Azure, SQL, and so on), see [Data Catalog YAML examples](data_catalog_yaml_examples.md).

!!! warning
    Datasets are not included in the core Kedro package from Kedro version **`0.19.0`**. Import them from the [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package instead.

## How to specify load, save and filesystem arguments

To load or save a CSV on a local file system, using specified load/save arguments:

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

`load_args` and `save_args` are forwarded directly to the underlying library. In the example above, `load_args` is passed to [`pd.read_csv`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.read_csv.html), and `save_args` is passed to [`pd.DataFrame.to_csv`](https://pandas.pydata.org/pandas-docs/stable/reference/api/pandas.DataFrame.to_csv.html).

To pass arguments to the filesystem rather than the dataset, use `fs_args`. For example, to set the `project` value on the underlying [`GCSFileSystem`](https://gcsfs.readthedocs.io/) when interacting with Google Cloud Storage:

```yaml
test_dataset:
  type: ...
  fs_args:
    project: test_project
```

The `open_args_load` and `open_args_save` keys nested inside `fs_args` are passed to the filesystem's `open` method to configure how a dataset file is opened during a load or save operation.

To load data from a local binary file using `utf-8` encoding:

```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_load:
      mode: "rb"
      encoding: "utf-8"
```

To save a file in append mode rather than overwriting:

```yaml
test_dataset:
  type: ...
  fs_args:
    open_args_save:
      mode: "a"
```

## How to use credentials with the Data Catalog

Store credentials in `conf/local/credentials.yml` and reference them by name from `catalog.yml`. The Data Catalog reads the credentials file before instantiation and passes the relevant block into the dataset as the `credentials` argument.

Suppose `conf/local/credentials.yml` contains:

```yaml
dev_s3:
  client_kwargs:
    aws_access_key_id: key
    aws_secret_access_key: secret
```

The catalog entry references `dev_s3` through the `credentials:` key:

```yaml
motorbikes:
  type: pandas.CSVDataset
  filepath: s3://your_bucket/data/02_intermediate/company/motorbikes.csv
  credentials: dev_s3
  load_args:
    sep: ','
```

The Data Catalog looks up `dev_s3` in the credentials dictionary and passes its values into the dataset as the `credentials` argument to `__init__`.

For background on how Kedro loads credentials, see [the credentials section of the configuration documentation](../configure/parameters_and_credentials_explanation.md#credentials).

## How to version a dataset

To enable versioning on a dataset, add the `versioned: True` flag to its catalog entry:

```yaml
cars:
  type: pandas.CSVDataset
  filepath: data/01_raw/company/cars.csv
  versioned: True
```

In this example, `filepath` is used as the basis of a folder that stores versions of the `cars` dataset. Each time a new version is created by a pipeline run, it is stored within `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` is a timestamp formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

By default, `kedro run` loads the latest version of the dataset. To load a specific version, pass `--load-versions`:

```bash
kedro run --load-versions=cars:YYYY-MM-DDThh.mm.ss.sssZ
```

`--load-versions` takes a dataset name and version timestamp separated by a colon.

For background on how versioning works internally, see [Dataset versioning](data_catalog.md#dataset-versioning) in the concept page.

## How to list available versions of a dataset

All versioned datasets provide a `list_versions()` method to retrieve all available versions:

```python
# In a Kedro session or notebook
dataset = catalog._datasets["cars"]
versions = dataset.list_versions(full_path=False)
print(versions)  # ['2024-01-15T10.30.00.000Z', '2024-01-14T09.15.00.000Z', ...]
```

The `list_versions()` method accepts a `full_path` parameter:

- `full_path=True` (default): returns full file paths to each version.
- `full_path=False`: returns the version strings (timestamps).

Versions are returned in reverse chronological order (newest first).

## How to configure datasets across environments

Kedro merges configuration from `conf/base/` and `conf/local/`, with `conf/local/` overriding `conf/base/` for the same top-level keys. This lets you point the same dataset name at different locations in different environments.

Consider a `cars` dataset defined in `conf/base/catalog.yml` that points to a CSV in an AWS S3 bucket:

```yaml
cars:
  filepath: s3://my_bucket/cars.csv
  type: pandas.CSVDataset
```

You can override it in `conf/local/catalog.yml` to point to a locally stored file instead:

```yaml
cars:
  filepath: data/01_raw/cars.csv
  type: pandas.CSVDataset
```

When the `cars` dataset is referenced in pipeline code, Kedro uses the entry from `conf/local/catalog.yml` while running locally, and the production entry when the local override is absent.

For the full set of merge rules across environments, see the [configuration documentation](../configure/configuration_explanation.md).
