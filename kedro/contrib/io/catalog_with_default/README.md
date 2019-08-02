# `DataCatalogWithDefault` class

`DataCatalogWithDefault` is a `DataCatalog` that will fall back to a default `AbstractDataSet` implementation if the requested key in not already registered in the catalog.
Handy **during development** when you are working with many `DataSet`s which all originate from a source, and you don't want to create a huge `DataCatalog`.

Now, it is possible to do the following:

```python
from kedro.contrib.io.catalog_with_default import DataCatalogWithDefault
from kedro.io import ParquetLocalDataSet
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

def default_io(name):
    return ParquetLocalDataSet(name)

catalog = DataCatalogWithDefault({},
                                 default=default_io,
                                 default_prefix='data/')

def my_node(input):
    return None

pipeline = Pipeline([
    node(my_node, 'input1', 'output1')
    ])

SequentialRunner().run(pipeline, catalog)
```

This will load `parquet` files from the `data/` local directory, without having to prepopulate your data catalog with anything.

Less safe during production, very handy during development.


### Motivation and Context

Very useful during development, saves a lot of time. Usually most datasets in a pipeline come from a single-source.
