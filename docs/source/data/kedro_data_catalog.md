# Kedro Data Catalog

Since `KedroDataCatalog` repeats `DataCatalog` functionality we will only highlight new API and provide usage examples at this page.
The rest examples provided for `DataCatalog` previously are relevant for `KedroDataCatalog`, thus we recommend first make yourself familiar with them and then start using new catalog.

## How to make `KedroDataCatalog` default catalog for Kedro `run`

To make `KedroDataCatalog` default catalog for Kedro `run` and other CLI commands modify your `settings.py` as follows:

```python
from kedro.io import KedroDataCatalog

DATA_CATALOG_CLASS = KedroDataCatalog
```

Then run your Kedro project as usual.

For more details about `settings.py` see [Project settings page](../kedro_project_setup/settings.md)
