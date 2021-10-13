# Datasets

Welcome to `kedro.extras.datasets`, the home of Kedro's data connectors. Here you will find `AbstractDataSet` implementations created by QuantumBlack and external contributors.

## What `AbstractDataSet` implementations are supported?

We support a range of data descriptions, including CSV, Excel, Parquet, Feather, HDF5, JSON, Pickle, SQL Tables, SQL Queries, Spark DataFrames and more. We even allow support for working with images.

These data descriptions are supported with the APIs of `pandas`, `spark`, `networkx`, `matplotlib`, `yaml` and more.

[The Data Catalog](https://kedro.readthedocs.io/en/stable/05_data/01_data_catalog.html) allows you to work with a range of file formats on local file systems, network file systems, cloud object stores, and Hadoop.

Here is a full list of [supported data descriptions and APIs](https://kedro.readthedocs.io/en/stable/kedro.extras.datasets.html).

## How can I create my own `AbstractDataSet` implementation?


Take a look at our [instructions on how to create your own `AbstractDataSet` implementation](https://kedro.readthedocs.io/en/stable/07_extend_kedro/03_custom_datasets.html).
