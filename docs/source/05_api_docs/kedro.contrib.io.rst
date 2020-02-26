kedro.contrib.io
================

.. rubric:: Description

.. automodule:: kedro.contrib.io

   .. rubric:: Data catalog wrapper

   .. autosummary::
      :toctree:
      :template: autosummary/class.rst

      kedro.contrib.io.catalog_with_default.DataCatalogWithDefault

   .. rubric:: DataSets

   .. autosummary::
      :toctree:
      :template: autosummary/class.rst

      kedro.contrib.io.azure.CSVBlobDataSet
      kedro.contrib.io.azure.JSONBlobDataSet
      kedro.contrib.io.bioinformatics.BioSequenceLocalDataSet
      kedro.contrib.io.cached.CachedDataSet
      kedro.contrib.io.feather.FeatherLocalDataSet
      kedro.contrib.io.matplotlib.MatplotlibLocalWriter
      kedro.contrib.io.matplotlib.MatplotlibS3Writer
      kedro.contrib.io.parquet.ParquetS3DataSet
      kedro.contrib.io.pyspark.SparkDataSet
      kedro.contrib.io.pyspark.SparkHiveDataSet
      kedro.contrib.io.pyspark.SparkJDBCDataSet
      kedro.contrib.io.yaml_local.YAMLLocalDataSet
      kedro.contrib.io.gcs.CSVGCSDataSet
      kedro.contrib.io.gcs.JSONGCSDataSet
      kedro.contrib.io.gcs.ParquetGCSDataSet
      kedro.contrib.io.networkx.NetworkXLocalDataSet


   .. rubric:: DataSet Transformers

   .. autosummary::
      :toctree:
      :template: autosummary/class.rst

      kedro.contrib.io.transformers.ProfileTimeTransformer
