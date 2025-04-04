
# Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. The catalog is stored in a YAML file (`catalog.yml`) that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

The {py:mod}`kedro-datasets <kedro-datasets:kedro_datasets>` package offers built-in datasets for common file types and file systems.

## Introduction to the Data Catalog

We first introduce the basic sections of `catalog.yml`, which is the file used to register data sources for a Kedro project.

- [Introduction to the Data Catalog](data_catalog.md)

## Examples of data catalog YAML

The following page offers a range of examples of YAML specification for various Data Catalog use cases:

- [Data Catalog YAML Examples](data_catalog_yaml_examples.md)

Once you are familiar with the format of `catalog.yml`, you may find your catalog gets repetitive if you need to load multiple datasets with similar configuration. From Kedro 0.18.12 you can use dataset factories to generalise the configuration and reduce the number of similar catalog entries. This works by matching datasets used in your project’s pipelines to dataset factory patterns and is explained in a new page about Kedro dataset factories:

- [Kedro Dataset Factories](kedro_dataset_factories.md)


## Advanced concepts
Further pages describe more advanced concepts:

- [Advanced: Access the Data Catalog in code](advanced_data_catalog_usage.md)
- [Advanced: Partitioned and incremental datasets](partitioned_and_incremental_datasets.md)

This section on handing data with Kedro concludes with an advanced use case, illustrated with a tutorial that explains how to create your own custom dataset:

- [Advanced: Tutorial to create a custom datase](how_to_create_a_custom_dataset.md)

## `KedroDataCatalog` (experimental feature)

As of Kedro 0.19.9, you can explore a new experimental feature — the `KedroDataCatalog`, an enhanced alternative to `DataCatalog`.

At present, `KedroDataCatalog` replicates the functionality of `DataCatalog` and is fully compatible with the Kedro `run` command. It introduces several API improvements:
* Simplified dataset access: `_FrozenDatasets` has been replaced with a public `get` method to retrieve datasets.
* Added dict-like interface: You can now use a dictionary-like syntax to retrieve, set, and iterate over datasets.

For more details and examples of how to use `KedroDataCatalog`, see the Kedro Data Catalog page.

- [KedroDataCatalog (experimental feature)](kedro_data_catalog.md)

The [documentation](./data_catalog.md) for `DataCatalog` remains relevant as `KedroDataCatalog` retains its core functionality with some enhancements.

> **Note**  
> `KedroDataCatalog` is under active development and may undergo breaking changes in future releases. While we encourage you to try it out, please be aware of potential modifications as we continue to improve it. Additionally, all upcoming catalog-related features will be introduced through `KedroDataCatalog` before it replaces `DataCatalog`.

We value your feedback — let us know if you have any thoughts or suggestions regarding `KedroDataCatalog` or potential new features via our [Slack channel](https://kedro-org.slack.com).
