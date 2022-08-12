# Dependencies

## Project-specific dependencies
When we introduced Kedro, we touched briefly on how to specify a project's dependencies to make it easier for others to run your project and avoid version conflicts downstream.

You can add or remove dependencies. For a new project, edit the `src/requirements.txt` file, then run the following:

```bash
kedro build-reqs
```

The `build-reqs` command will [pip compile](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) the requirements listed in the `src/requirements.txt` file into a `src/requirements.lock` that specifies a list of pinned project dependencies (those with a strict version).

```{note}
The `src/requirements.txt` file contains "source" requirements, while `src/requirements.lock` contains the compiled version of those and requires no manual updates.
```

To further update the project requirements, modify the `src/requirements.txt` file (not `src/requirements.lock`) and re-run `kedro build-reqs`.


## Install project-specific dependencies

To install the project-specific dependencies, navigate to the root directory of the project and run:

```bash
pip install -r src/requirements.txt
```

## Workflow dependencies

To install all of the dependencies recorded in Kedro's [`setup.py`](https://github.com/kedro-org/kedro/blob/develop/setup.py), run:

```bash
pip install "kedro[all]"
```

### Install dependencies related to the Data Catalog

The [Data Catalog](../data/data_catalog.md) is your way of interacting with different data types in Kedro. The modular dependencies in this category include `pandas`, `numpy`, `pyspark`, `matplotlib`, `pillow`, `dask`, and more.

#### Install dependencies at a group-level

Data types are broken into groups e.g. `pandas`, `spark` and `pickle`. Each group has a collection of data types e.g.`pandas.CSVDataSet`, `pandas.ParquetDataSet` and more. You can install dependencies for an entire group of dependencies as follows:

```bash
pip install "kedro[<group>]"
```

This installs Kedro and dependencies related to the data type group. An example of this could be a workflow that depends on the data types in `pandas`. Run `pip install "kedro[pandas]"` to install Kedro and the dependencies for the data types in the [`pandas` group](https://github.com/kedro-org/kedro/tree/develop/kedro/extras/datasets/pandas).

#### Install dependencies at a type-level

To limit installation to dependencies specific to a data type:

```bash
pip install "kedro[<group>.<dataset>]"
```

For example, your workflow might require use of the `pandas.ExcelDataSet`, so to install its dependencies, run `pip install "kedro[pandas.ExcelDataSet]"`.
