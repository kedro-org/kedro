# Dependencies

Both `pip install kedro` and `conda install -c conda-forge kedro` install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

When you create a project, you then introduce additional dependencies for the tasks it performs.

## Declare project-specific dependencies

When you create a new Kedro project, the project's dependencies are declared in the `[project].dependencies` section of `pyproject.toml`, which is the source of truth. The generated `requirements.txt` is deprecated and will be removed in a future release.

To add a dependency, run `uv add <package>`, or edit `pyproject.toml` directly.

## Install project-specific dependencies

When someone clones your project, they can install the project-specific dependencies by navigating to the root directory of the project and running the following command:

```bash
uv sync
```

If you use `pip` instead, run:

```bash
pip install -e .
```

### Install dependencies related to the Data Catalog

The [Data Catalog](../catalog-data/data_catalog.md) is your way of interacting with different data types in Kedro. You can use [`kedro-datasets`](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) to interact with the data used in your projects. Depending on the datasets that you use in your Data Catalog, you might need to include additional dependencies in your `pyproject.toml`. The modular dependencies in this category include `pandas`, `numpy`, `pyspark`, `matplotlib`, `pillow`, `dask`, and more.

#### Install dependencies at a group-level

Data types are broken into groups, for example, `pandas`, `spark` and `pickle`. Each group has a collection of data types, for example, `pandas.CSVDataset`, `pandas.ParquetDataset` and more. You can install dependencies for an entire group of dependencies as follows:

```bash
pip install "kedro-datasets[<group>]"
```

This installs Kedro and dependencies related to the data type group. An example of this could be a workflow that depends on the data types in `pandas`. Run `pip install "kedro-datasets[pandas]"` to install Kedro and the dependencies for the data types in the [`pandas` group](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets/kedro_datasets/pandas).

#### Install dependencies at a type-level

To limit installation to dependencies specific to a data type:

```bash
pip install "kedro-datasets[<group>-<dataset>]"
```

For example, your workflow might require the `pandas.ExcelDataset`, so to install its dependencies, run `pip install "kedro-datasets[pandas-exceldataset]"`.

!!! note

    From `kedro-datasets` version 3.0.0 and later, the names of the optional dataset-level dependencies have been normalised to follow [PEP 685](https://peps.python.org/pep-0685/). The '.' character has been replaced with a '-' character and the names are in lowercase. For example, if you had `kedro-datasets[pandas.ExcelDataset]` in your requirements file, it would have to be changed to `kedro-datasets[pandas-exceldataset]`.

## Reproducible environments

To pin the project dependencies and the transitive dependencies to specific versions, use [`uv`](https://docs.astral.sh/uv/). Running `uv sync` (or `uv lock`) creates a cross-platform `uv.lock` file. Commit `uv.lock` to your repository so that everyone gets the same environment.

To update specific packages, run `uv lock --upgrade-package <package>`.

If you need a `requirements.txt` for tooling that expects one, generate it with `uv export --format requirements-txt`.


