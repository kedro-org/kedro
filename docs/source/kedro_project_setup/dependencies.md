# Dependencies

Both `pip install kedro` and `conda install -c conda-forge kedro` install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

When you create a project, you then introduce additional dependencies for the tasks it performs.

## Project-specific dependencies

You can specify a project's exact dependencies in the `requirements.txt` file to make it easier for you and others to run your project in the future,
and to avoid version conflicts downstream. This can be achieved with the help of [`pip-tools`](https://pypi.org/project/pip-tools/).
To install `pip-tools` in your virtual environment, run the following command:

```bash
pip install pip-tools
```

To add or remove dependencies to a project, edit the `requirements.txt` file, then run the following:

```bash
pip-compile <project_root>/requirements.txt --output-file <project_root>/requirements.lock
```

This will [pip compile](https://github.com/jazzband/pip-tools#example-usage-for-pip-compile) the requirements listed in
the `requirements.txt` file into a `requirements.lock` that specifies a list of pinned project dependencies
(those with a strict version). You can also use this command with additional CLI arguments such as `--generate-hashes`
to use `pip`'s Hash Checking Mode or `--upgrade-package` to update specific packages to the latest or specific versions.
[Check out the `pip-tools` documentation](https://pypi.org/project/pip-tools/) for more information.

```{note}
The `requirements.txt` file contains "source" requirements, while `src/requirements.lock` contains the compiled version of those and requires no manual updates.
```

To further update the project requirements, modify the `requirements.txt` file (not `src/requirements.lock`) and re-run the `pip-compile` command above.

## Install project-specific dependencies

To install the project-specific dependencies, navigate to the root directory of the project and run:

```bash
pip install -r requirements.txt
```

### Install dependencies related to the Data Catalog

The [Data Catalog](../data/data_catalog.md) is your way of interacting with different data types in Kedro. The modular dependencies in this category include `pandas`, `numpy`, `pyspark`, `matplotlib`, `pillow`, `dask`, and more.

#### Install dependencies at a group-level

Data types are broken into groups e.g. `pandas`, `spark` and `pickle`. Each group has a collection of data types e.g.`pandas.CSVDataset`, `pandas.ParquetDataset` and more. You can install dependencies for an entire group of dependencies as follows:

```bash
pip install "kedro-datasets[<group>]"
```

This installs Kedro and dependencies related to the data type group. An example of this could be a workflow that depends on the data types in `pandas`. Run `pip install "kedro-datasets[pandas]"` to install Kedro and the dependencies for the data types in the [`pandas` group](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets/kedro_datasets/pandas).

#### Install dependencies at a type-level

To limit installation to dependencies specific to a data type:

```bash
pip install "kedro-datasets[<group>.<dataset>]"
```

For example, your workflow might require use of the `pandas.ExcelDataset`, so to install its dependencies, run `pip install "kedro-datasets[pandas.ExcelDataset]"`.
