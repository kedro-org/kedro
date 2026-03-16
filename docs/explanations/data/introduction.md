
# Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. The catalog is stored in a YAML file (`catalog.yml`) that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

The [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) package offers built-in datasets for common file types and file systems.

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
- [Advanced: Lazy loading](lazy_loading.md)
- [Advanced: Partitioned and incremental datasets](partitioned_and_incremental_datasets.md)

This section on handing data with Kedro concludes with an advanced use case, illustrated with a tutorial that explains how to create your own custom dataset:

- [Advanced: Tutorial to create a custom dataset](../extend/how_to_create_a_custom_dataset.md)
