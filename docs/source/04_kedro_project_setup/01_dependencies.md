# Dependencies

## Project-specific dependencies
When we introduced Kedro, we touched briefly on how to specify a project's dependencies to make it easier for others to run your project and avoid version conflicts downstream.

You can add or remove dependencies. For a new project, edit `src/requirements.txt` and then run the following:

```bash
kedro build-reqs
```

The `build-reqs` command will:

1. Generate `src/requirements.in` from the contents of `src/requirements.txt`
2. [pip compile](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) the requirements listed in `src/requirements.in`
3. Regenerate `src/requirements.txt` to specify a list of pinned project dependencies (those with a strict version)

> *Note:* `src/requirements.in` contains "source" requirements, while `src/requirements.txt` contains the compiled version of those and requires no manual updates.

To further update the project requirements, you should modify `src/requirements.in` (not `src/requirements.txt`) and re-run `kedro build-reqs`.


## `kedro install`

To install the project-specific dependencies, navigate to the root directory of the project and run:

```bash
kedro install
```

`kedro install` automatically compiles project dependencies by running `kedro build-reqs` behind the scenes if the `src/requirements.in` file doesn't exist.

To skip the compilation step and install requirements as-is from `src/requirements.txt`, run the following:
```bash
kedro install --no-build-reqs
```

This takes the latest version of a dependency that is available within the range specified. It allows flexibility in the version of the dependency that `pip` installs. For example, if `ipython>=7.0.0,<8.0` is specified, then the most up-to-date version available is installed.


To force the compilation, even if `src/requirements.in` already exists, run the following:

```bash
kedro install --build-reqs
```

In some cases, such as a production setting, this is useful to eliminate ambiguity and specify exactly the version of each dependency that is installed.

## Workflow dependencies

To install all of the dependencies recorded in Kedro's [`setup.py`](https://github.com/quantumblacklabs/kedro/blob/develop/setup.py) run:

```bash
pip install "kedro[all]"
```

### Install dependencies related to the Data Catalog

The [Data Catalog](../05_data/01_data_catalog.md) is your way of interacting with different data types in Kedro. The modular dependencies in this category include `pandas`, `numpy`, `pyspark`, `matplotlib`, `pillow`, `dask`, and more.

#### Install dependencies at a group-level

Data types are broken into groups e.g. `pandas`, `spark` and `pickle`. Each group has a collection of data types e.g.`pandas.CSVDataSet`, `pandas.ParquetDataSet` and more. You can install dependencies for an entire group of dependencies as follows:

```bash
pip install "kedro[<group>]"
```

This installs Kedro and dependencies related to the data type group. An example of this could be a workflow that depends on the data types in `pandas`. Run `pip install "kedro[pandas]"` to install Kedro and the dependencies for the data types in the [`pandas` group](https://github.com/quantumblacklabs/kedro/tree/develop/kedro/extras/datasets/pandas).

#### Install dependencies at a type-level

To limit installation to dependencies specific to a data type:

```bash
pip install "kedro[<group>.<dataset>]"
```

For example, your workflow may require use of the `pandas.ExcelDataSet`, so to install its dependencies, run `pip install "kedro[pandas.ExcelDataSet]"`.
