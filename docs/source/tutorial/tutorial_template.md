# Set up the spaceflights project

This section shows how to create a new project (with `kedro new` using the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas)) and install project dependencies (with `pip install -r requirements.txt`).

## Create a new project

[Set up Kedro](../get_started/install.md) if you have not already done so.

```{important}
We recommend that you use the same version of Kedro that was most recently used to test this tutorial (0.18.6). To check the version installed, type `kedro -V` in your terminal window.
```

In your terminal, navigate to the folder you want to store the project. Type the following to generate the project from the [Kedro spaceflights starter](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas). The project will be populated with a complete set of working example code:

```bash
kedro new --starter=spaceflights-pandas
```

When prompted for a project name, you should accept the default choice (`Spaceflights`) as the rest of this tutorial assumes that project name.

When Kedro has created the project, navigate to the [project root directory](./spaceflights_tutorial.md#project-root-directory):

```bash
cd spaceflights
```

## Install project dependencies

Kedro projects have a `requirements.txt` file to specify their dependencies and enable sharable projects by ensuring consistency across Python packages and versions.

The spaceflights project dependencies are stored in `requirements.txt`(you may find that the versions differ slightly depending on the version of Kedro):

```text
# code quality packages
black~=22.0
ipython>=7.31.1, <8.0; python_version < '3.8'
ipython~=8.10; python_version >= '3.8'
ruff~=0.0.290

# notebook tooling
jupyter~=1.0
jupyterlab_server>=2.11.1
jupyterlab~=3.0

# Pytest + useful extensions
pytest-cov~=3.0
pytest-mock>=1.7.1, <2.0
pytest~=7.2

# Kedro dependencies and datasets to work with different data formats (including CSV, Excel, and Parquet)
kedro~=0.18.13
kedro-datasets[pandas.CSVDataset, pandas.ExcelDataset, pandas.ParquetDataset]~=1.1
kedro-telemetry~=0.2.0
kedro-viz~=6.0 # Visualise pipelines

# For modeling in the data science pipeline
scikit-learn~=1.0
```

### Install the dependencies

To install all the project-specific dependencies, run the following from the project root directory:

```bash
pip install -r requirements.txt
```

## Optional: logging and configuration

You might want to [set up logging](../logging/index.md) at this stage of the workflow, but we do not use it in this tutorial.

You may also want to store credentials such as usernames and passwords if they are needed for specific data sources used by the project.

To do this, add them to `conf/local/credentials.yml` (some examples are included in that file for illustration).

### Configuration best practice to avoid leaking confidential data

* Do not commit data to version control.
* Do not commit notebook output cells (data can easily sneak into notebooks when you don't delete output cells).
* Do not commit credentials in `conf/`. Use only the `conf/local/` folder for sensitive information like access credentials.

You can find additional information in the [documentation on configuration](../configuration/configuration_basics.md).
