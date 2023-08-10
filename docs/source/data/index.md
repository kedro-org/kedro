
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

Further pages describe more advanced usage:

```{toctree}
:maxdepth: 1

kedro_dataset_factories
partitioned_and_incremental_datasets
advanced_data_catalog_usage
```

The section concludes with an advanced use case tutorial to create your own custom dataset:

```{toctree}
:maxdepth: 1

how_to_create_a_custom_dataset
```
