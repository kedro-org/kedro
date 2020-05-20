## Installation guide

### Installing Kedro

We recommend installing Kedro in a [new virtual environment](01_prerequisites.md#working-with-virtual-environments) for *each* of your projects.

To install Kedro from the Python Package Index (PyPI) simply run:

```
pip install kedro
```

It is also possible to install `kedro` using `conda`, a package and environment manager program bundled with [Anaconda](01_prerequisites.md#working-with-virtual-environments), using:

```
conda install -c conda-forge kedro
```

This installs the core Kedro module; which includes the CLI tool, project template, pipeline abstraction, framework and support for configuration.

> *Note:* To install a development version of Kedro, follow [these steps](../06_resources/01_faq.md#how-can-i-use-development-version-of-kedro).

### Verifying a successful installation
To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [FAQs](../06_resources/01_faq.md) for help.

### Installing workflow dependencies

Your workflow may start with `pip install kedro` but it's possible to include packages that you will need for your entire data and ML workflow.

#### Installing all dependencies
To install all of the dependencies recorded in Kedro's [`setup.py`](https://github.com/quantumblacklabs/kedro/blob/develop/setup.py) run:

```bash
pip install "kedro[all]"
```

#### Installing dependencies related to the Data Catalog

The [Data Catalog](../04_user_guide/04_data_catalog.md) is your way of interacting with different data types in Kedro. The modular dependencies in this category include `pandas`, `numpy`, `pyspark`, `matplotlib`, `pillow`, `dask`, and more.

##### Installing dependencies at a group-level

Data types are broken into groups e.g. `pandas`, `spark` and `pickle`. Each group has a collection of data types e.g.`pandas.CSVDataSet`, `pandas.ParquetDataSet` and more. You can choose to install dependencies for an entire group of dependencies as follows:

```bash
pip install "kedro[<group>]"
```

This will install Kedro and dependencies related to the data type group. An example of this could be a workflow that is dependant on the data-types in `pandas`, you would run `pip install "kedro[pandas]"` to install Kedro and the dependencies for the data types in the [`pandas` group](https://github.com/quantumblacklabs/kedro/tree/develop/kedro/extras/datasets/pandas).

##### Installing dependencies at a type-level

The pattern for installing dependencies specific to a data type is the following:

```bash
pip install "kedro[<group>.<dataset>]"
```

For example, your workflow may require use of the `pandas.ExcelDataSet`, so to install its dependencies, you should run `pip install "kedro[pandas.ExcelDataSet]"`.
