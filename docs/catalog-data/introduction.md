
# Data Catalog

In a Kedro project, the Data Catalog is a registry of all data sources available for use by the project. The catalog is stored in a YAML file (`catalog.yml`) that maps the names of node inputs and outputs as keys in the `DataCatalog` class.

The [kedro-datasets documentation](https://docs.kedro.org/projects/kedro-datasets/en/stable/) package offers built-in datasets for common file types and file systems.

## Concepts

These pages explain how the Data Catalog works and the model behind each feature:

- [Data Catalog](data_catalog.md) — what the catalog is and how it organises data.
- [Dataset factories](kedro_dataset_factories.md) — generalising catalog entries with patterns.
- [Partitioned and incremental datasets](partitioned_and_incremental_datasets.md) — working with data split across many files.
- [Lazy loading](lazy_loading.md) — how Kedro defers dataset instantiation until access.

## How-to guides

These pages give step-by-step procedures for common catalog tasks:

- [How to configure the Data Catalog](how_to_configure_the_data_catalog.md) — load and save arguments, credentials, versioning, environments.
- [How to use dataset factories](how_to_use_dataset_factories.md) — applying factory patterns to your catalog.
- [How to use partitioned and incremental datasets](how_to_use_partitioned_and_incremental_datasets.md) — YAML and Python recipes.
- [How to access the Data Catalog in code](how_to_access_the_data_catalog_in_code.md) — programmatic catalog usage.

## Examples

- [Data Catalog YAML examples](data_catalog_yaml_examples.md) — a wide range of `catalog.yml` recipes.

## Related

For an advanced tutorial that explains how to create your own custom dataset, see [Tutorial to create a custom dataset](../extend/how_to_create_a_custom_dataset.md).
