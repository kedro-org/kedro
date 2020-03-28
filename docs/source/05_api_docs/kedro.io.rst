kedro.io
========

.. rubric:: Description

.. automodule:: kedro.io

Data Catalog
------------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.DataCatalog

Data Sets
---------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.LambdaDataSet
    kedro.io.MemoryDataSet
    kedro.io.PartitionedDataSet
    kedro.io.IncrementalDataSet
    kedro.io.CachedDataSet
    kedro.io.DataCatalogWithDefault

Errors
------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.DataSetAlreadyExistsError
    kedro.io.DataSetError
    kedro.io.DataSetNotFoundError


Base Classes
------------

.. autosummary::
    :toctree:
    :template: autosummary/class.rst

    kedro.io.AbstractDataSet
    kedro.io.AbstractVersionedDataSet
    kedro.io.AbstractTransformer
    kedro.io.Version
