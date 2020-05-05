## Installation guide

### Installing Kedro core

We recommend installing Kedro in a new virtual environment for *each* of your projects. To install it from the Python Package Index (PyPI) simply run:

```
pip install kedro       # Install only core and a minimal set of dependencies
```

It is also possible to install `kedro` using `conda`, a package and environment manager program bundled with Anaconda. With [`conda`](https://kedro.readthedocs.io/en/stable/02_getting_started/01_prerequisites.html#python-virtual-environments) already installed, simply run:

```
conda install -c conda-forge kedro       # Install only core and a minimal set of dependencies
```

This will install Kedro core and a minimal set of dependencies required to run Kedro.

> *Note:* To install a development version of Kedro, follow [these steps](../06_resources/01_faq.md#how-can-i-use-development-version-of-kedro).

### Verifying a successful installation
To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [FAQs](../06_resources/01_faq.md) for help.

### Optional dependencies

The core library of Kedro has minimal requirements so that you can construct your ideal workflow with the tools that you need. You can install Kedro with all dependencies, including `Pandas`, `NumPy`, `PySpark` etc. as follows:

```bash
pip install "kedro[all]"    # Install all dependencies
```

This will install all of the dependencies noted in the below table in your Python virtual environment. However, we realise that you may only want to install specific dependencies.

Let us look at an example where our workflow is completely dependent on `Spark`. Initially, we would have installed Kedro core with `pip install kedro` and after looking at the below table, we would additionally run `pip install "kedro[spark]"` to install the `Spark`-specific dependencies.


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
|                    | networkx    | networkx.NetworkXDataSet      | pip install "kedro[networkx]"           |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | pandas      | pandas.CSVDataSet             | pip install "kedro[pandas]"             |
|                    |             | pandas.ExcelDataSet           |                                         |
|                    |             | pandas.FeatherDataSet         |                                         |
|                    |             | pandas.GBQTableDataSet        |                                         |
|                    |             | pandas.HDFDateSet             |                                         |
|                    |             | pandas.JSONDataSet            |                                         |
|                    |             | pandas.ParquetDataSet         |                                         |
|                    |             | pandas.SQLQueryDataSet        |                                         |
|                    |             | pandas.SQLTableDataSet        |                                         |
|                    +-------------+-------------------------------+-----------------------------------------+
|                    | pillow      | pillow.ImageDataSet           | pip install "kedro[pillow]"             |
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
