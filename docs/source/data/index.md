
# Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. The catalog is stored in a YAML file (`catalog.yml`) that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

The {py:mod}`kedro-datasets <kedro-datasets:kedro_datasets>` package offers built-in datasets for common file types and file systems.

We first introduce the basic sections of `catalog.yml`, which is the file used to register data sources for a Kedro project.

```{toctree}
:maxdepth: 1

data_catalog
```

The following page offers a range of examples of YAML specification for various Data Catalog use cases:

```{toctree}
:maxdepth: 1

data_catalog_yaml_examples
```

Once you are familiar with the format of `catalog.yml`, you may find your catalog gets repetitive if you need to load multiple datasets with similar configuration. From Kedro 0.18.12 you can use dataset factories to generalise the configuration and reduce the number of similar catalog entries. This works by matching datasets used in your project’s pipelines to dataset factory patterns and is explained in a new page about Kedro dataset factories:


```{toctree}
:maxdepth: 1

kedro_dataset_factories
```

Further pages describe more advanced concepts:

```{toctree}
:maxdepth: 1

advanced_data_catalog_usage
partitioned_and_incremental_datasets
```

This section on handing data with Kedro concludes with an advanced use case, illustrated with a tutorial that explains how to create your own custom dataset:

```{toctree}
:maxdepth: 1

how_to_create_a_custom_dataset
```

From Kedro 0.19.0 you can use an experimental feature - `KedroDataCatalog` instead of `DataCatalog`.

Currently, it repeats `DataCatalog` functionality and fully compatible with Kedro `run` with a few API enhancements:
  * Removed `_FrozenDatasets` and access datasets as properties;
  * `KedroDataCatalog` supports dict-like interface to get/set datasets and iterate through them.

A separate page of [Kedro Data Catalog](./kedro_data_catalog.md) shows `KedroDataCatalog` usage examples, and it's new API but all the information provided for the `DataCatalog` is relevant as well.

It is an experimental feature and is under active development. Though all the new catalog features will be released for `KedroDataCatalog` and soon it will fully replace `DataCatalog`. So we encourage you to try it out, but it is possible we'll introduce breaking changes to this class, so be mindful of that. Let us know if you have any feedback about the `KedroDataCatalog` or ideas for new features.
