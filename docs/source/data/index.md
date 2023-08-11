
# The Kedro Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. The catalog is stored in a YAML file (`catalog.yml`) that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

[Kedro provides different built-in datasets in the `kedro-datasets` package](/kedro_datasets) for numerous file types and file systems, so you don’t have to write any of the logic for reading/writing data.


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

Once you are familiar with the format of `catalog.yml`, you may find your catalog gets repetitive if you need to load multiple datasets with similar configuration. From Kedro 0.18.12 you can use dataset factories to generalise the configuration and reduce the number of similar catalog entries. This works by by matching datasets used in your project’s pipelines to dataset factory patterns and is explained in a new page about Kedro dataset factories:


```{toctree}
:maxdepth: 1

kedro_dataset_factories
```

Further pages describe more advanced concepts:

```{toctree}
:maxdepth: 1

partitioned_and_incremental_datasets
advanced_data_catalog_usage
```

This section on handing data with Kedro concludes with an advanced use case, illustrated with a tutorial that explains how to create your own custom dataset:

```{toctree}
:maxdepth: 1

how_to_create_a_custom_dataset
```
