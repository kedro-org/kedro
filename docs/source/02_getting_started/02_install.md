## Installation guide

We recommend installing Kedro in a new virtual environment for *each* of your projects. To install Kedro:

```bash
pip install kedro     # Install only core and a minimal set of dependencies
```

This will install Kedro core and a minimal set of dependencies required to run Kedro.

You can install Kedro with all dependencies, including Pandas, NumPy, PySpark etc. as follows:

```bash
pip install "kedro[all]"    # Install all dependencies
```

> *Note:* To install development version of Kedro, follow [these steps](../06_resources/01_faq.md#how-can-i-use-development-version-of-kedro).

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [FAQs](../06_resources/01_faq.md) for help.

## Optional dependencies

Kedro has optional dependency sets required to work with a specific functionality.
For example, having installed only Kedro core you will require to install `spark` dependency set to with `Spark` datasets.

```bash
pip install "kedro[spark]"
```

These dependency sets are listed below.

```eval_rst
+--------------------+-------------+-------------------------------+-----------------------------------------+
| Theme              | Directory   | Component                     | Installation Command                    |
+--------------------+-------------+-------------------------------+-----------------------------------------+
| Dataset            | biosequence | biosquence.BioSequenceDataSet | pip install "kedro[bioinformatics]"     |
+--------------------+-------------+-------------------------------+-----------------------------------------+
|                    | dask        | dask.ParquetDataSet           | pip install "kedro[dask]"               |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | geopandas   | geopandas.GeoJSONDataSet      | pip install "kedro[geopandas]"          |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | matplotlib  | matplotlib.MatplotlibWriter   | pip install "kedro[matplotlib]"         |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | holoviews   | holoviews.HoloviewsWriter     | pip install "kedro[holoviews]"         |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | networkx    | networkx.NetworkXDataSet      | pip install "kedro[networkx]"           |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | pandas      | pandas.CSVBlobDataSet         | pip install "kedro[pandas]"             |
|                    |             | pandas.CSVDataSet             |                                         |
|                    |             | pandas.ExcelDataSet           |                                         |
|                    |             | pandas.FeatherDataSet         |                                         |
|                    |             | pandas.GBQTableDataSet        |                                         |
|                    |             | pandas.HDFDateSet             |                                         |
|                    |             | pandas.JSONBlobDataSet        |                                         |
|                    |             | pandas.JSONDataSet            |                                         |
|                    |             | pandas.ParquetDataSet         |                                         |
|                    |             | pandas.SQLQueryDataSet        |                                         |
|                    |             | pandas.SQLTableDataSet        |                                         |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | spark       | spark.SparkDataSet            | pip install "kedro[spark]"              |
|                    |             | spark.SparkHiveDataSet        |                                         |
|                    |             | spark.SparkJDBCDataSet        |                                         |
+--------------------+-------------+-------------------------------+-----------------------------------------+
| Decorators         |             | mem_profile                   | pip install "kedro[profilers]"          |
| Transformers       |             | ProfileMemoryTransformer      |                                         |
+--------------------+-------------+-------------------------------+-----------------------------------------+
| Documentation      |             |                               | pip install "kedro[docs]"               |
+--------------------+-------------+-------------------------------+-----------------------------------------+
| Notebook templates |             |                               | pip install "kedro[notebook_templates]" |
+--------------------+-------------+-------------------------------+-----------------------------------------+
```
