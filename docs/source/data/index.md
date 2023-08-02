
# The Kedro Data Catalog

Kedro's Data Catalog is a registry for all the data sources that a project can use. The Data Catalog is used to manage loading and saving data and it maps the names of node inputs and outputs as keys in a `DataCatalog`, a Kedro class that can be specialised for different types of data storage.

[Kedro provides different built-in datasets](/kedro_datasets) for numerous file types and file systems, so you don’t have to write any of the logic for reading/writing data.

This section is comprised of a set of pages that do the following:

TO DO -- summarise

```{toctree}
:maxdepth: 1

data_catalog
data_catalog_yaml_examples
data_catalog_basic_how_to
partitioned_and_incremental_datasets
advanced_data_catalog_usage
how_to_create_a_custom_dataset
```
