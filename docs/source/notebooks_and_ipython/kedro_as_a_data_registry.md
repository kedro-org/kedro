# Kedro as a data registry

In some projects you may want to share a Jupyter notebook with others. To make it easy to share you should avoid using hard-coded file paths for data access.

One solution is to set up a lightweight Kedro project that uses the Kedro [`DataCatalog`](../data/data_catalog.md) as a registry for the data without using any of the other features of Kedro.

The Kedro starter with alias `standalone-datacatalog` (formerly known as `mini-kedro`) provides this kind of minimal functionality.

## Usage

Use the [`standalone-datacatalog` starter](https://github.com/kedro-org/kedro-starters/tree/main/standalone-datacatalog) to create a new project:

```bash
kedro new --starter=standalone-datacatalog
```

The starter comprises a minimal setup to use the traditional [Iris dataset](https://www.kaggle.com/uciml/iris) with Kedro's [`DataCatalog`](../data/data_catalog.md).

The starter contains:

* A `conf` directory, which contains an example `DataCatalog` configuration (`catalog.yml`):

 ```yaml
# conf/base/catalog.yml
example_dataset_1:
  type: pandas.CSVDataSet
  filepath: folder/filepath.csv

example_dataset_2:
  type: spark.SparkDataSet
  filepath: s3a://your_bucket/data/01_raw/example_dataset_2*
  credentials: dev_s3
  file_format: csv
  save_args:
    if_exists: replace
```

* A `data` directory, which contains an example dataset identical to the one used by the [`pandas-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris) starter

* An example Jupyter notebook, which shows how to instantiate the `DataCatalog` and interact with the example dataset:

```python
df = catalog.load("example_dataset_1")
df_2 = catalog.save("example_dataset_2")
```
