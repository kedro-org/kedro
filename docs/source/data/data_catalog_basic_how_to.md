# Data Catalog how to guide


TO DO: Revise any explanations where possible to make it more hands on/task based

## How to version datasets and ML models

Making a simple addition to your Data Catalog allows you to perform versioning of datasets and machine learning models.

Consider the following versioned dataset defined in the `catalog.yml`:

```yaml
cars:
  type: pandas.CSVDataSet
  filepath: data/01_raw/company/cars.csv
  versioned: True
```

The `DataCatalog` will create a folder to store a version of the `CSVDataSet` called `cars`. The actual csv file location will look like `data/01_raw/company/cars.csv/<version>/cars.csv`, where `<version>` corresponds to a global save version string formatted as `YYYY-MM-DDThh.mm.ss.sssZ`.

By default, the `DataCatalog` will load the latest version of the dataset. However, you can also specify a particular versioned data set with `--load-version` flag as follows:

```bash
kedro run --load-version=cars:YYYY-MM-DDThh.mm.ss.sssZ
```
where `--load-version` is dataset name and version timestamp separated by `:`.

### Supported datasets

Currently, the following datasets support versioning:

- `kedro_datasets.matplotlib.MatplotlibWriter`
- `kedro_datasets.holoviews.HoloviewsWriter`
- `kedro_datasets.networkx.NetworkXDataSet`
- `kedro_datasets.pandas.CSVDataSet`
- `kedro_datasets.pandas.ExcelDataSet`
- `kedro_datasets.pandas.FeatherDataSet`
- `kedro_datasets.pandas.HDFDataSet`
- `kedro_datasets.pandas.JSONDataSet`
- `kedro_datasets.pandas.ParquetDataSet`
- `kedro_datasets.pickle.PickleDataSet`
- `kedro_datasets.pillow.ImageDataSet`
- `kedro_datasets.text.TextDataSet`
- `kedro_datasets.spark.SparkDataSet`
- `kedro_datasets.yaml.YAMLDataSet`
- `kedro_datasets.api.APIDataSet`
- `kedro_datasets.tensorflow.TensorFlowModelDataSet`
- `kedro_datasets.json.JSONDataSet`

```{note}
Although HTTP(S) is a supported file system in the dataset implementations, it does not support versioning.
```

## How to create a Data Catalog YAML configuration file via the CLI

You can use the [`kedro catalog create` command to create a Data Catalog YAML configuration](../development/commands_reference.md#create-a-data-catalog-yaml-configuration-file).

This creates a `<conf_root>/<env>/catalog/<pipeline_name>.yml` configuration file with `MemoryDataSet` datasets for each dataset in a registered pipeline if it is missing from the `DataCatalog`.

```yaml
# <conf_root>/<env>/catalog/<pipeline_name>.yml
rockets:
  type: MemoryDataSet
scooters:
  type: MemoryDataSet
```


## How to access a dataset that needs credentials

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

In the example above, the `catalog.yml` file contains references to credentials keys `dev_s3` and `scooters_credentials`. This means that when it instantiates the `motorbikes` dataset, for example, the `DataCatalog` will attempt to read top-level key `dev_s3` from the received `credentials` dictionary, and then will pass its values into the dataset `__init__` as a `credentials` argument. 


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


