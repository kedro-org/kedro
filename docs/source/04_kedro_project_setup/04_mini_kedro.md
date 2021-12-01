# The `mini-kedro` Kedro starter

## Introduction

Mini-Kedro makes it possible to use the [`DataCatalog`](https://kedro.readthedocs.io/en/stable/05_data/01_data_catalog.html) functionality in Kedro.
Use Kedro to configure and explore data sources in a Jupyter notebook using the [DataCatalog](https://kedro.readthedocs.io/en/stable/05_data/01_data_catalog.html) feature.

The DataCatalog allows you to specify data sources that you interact with for loading and saving purposes using a YAML API. See an example:

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

Later on, you can build a full pipeline using the same configuration, with the following steps:

1. Create a new empty Kedro project in a new directory

```bash
kedro new
```

Let's assume that the new project is created at `/path/to/your/project`.

2. Copy the `conf/` and `data/` directories over to the new project

```
cp -fR {conf,data} `/path/to/your/project`
```

This makes it possible to use something like `df = catalog.load("example_dataset_1")` and `df_2 = catalog.save("example_dataset_2")` to interact with data in a Jupyter notebook.
The advantage of this approach is that you never need to specify file paths for loading or saving data in your Jupyter notebook.

## Usage

Create a new project using this starter:

```bash
$ kedro new --starter=mini-kedro
```

## Content

The starter contains:

* A `conf/` directory, which contains an example `DataCatalog` configuration (`catalog.yml`)
* A `data/` directory, which contains an example dataset identical to the one used by the [`pandas-iris`](https://github.com/quantumblacklabs/kedro-starters/tree/main/pandas-iris) starter
* An example notebook showing how to instantiate the `DataCatalog` and interact with the example dataset
* A `README.md`, which explains how to use the project created by the starter and how to transition to a full Kedro project afterwards
