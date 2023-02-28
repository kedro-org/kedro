# Set up the spaceflights tutorial project

In this section, we discuss the project set-up phase, which is the first part of the standard development workflow. The setup steps are as follows:

* Create a new project with `kedro new`
* Install project dependencies with `pip install -r src/requirements.txt`
* Configure the following in the `conf` folder:
	* Credentials and any other sensitive information
	* Logging

## Create a new project

If you have not yet set up Kedro, do so by [following the guidelines to install Kedro](../get_started/install.md).

```{important}
We recommend that you use the same version of Kedro that was most recently used to test this tutorial (0.18.5).
```

In your terminal window, navigate to the folder you want to store the project. Type the following to generate the project from the [Kedro starter for the spaceflights tutorial](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights) - your project will be populated with a complete set of working example code:

```bash
kedro new --starter=spaceflights
```

When prompted for a project name, enter `Kedro Tutorial`. When Kedro has created your project, you can navigate to the [project root directory](./spaceflights_tutorial.md#project-root-directory):

```bash
cd kedro-tutorial
```

## Install project dependencies

Kedro projects have a `requirements.txt` file to specify their dependencies and enable sharable projects by ensuring consistency across Python packages and versions.

The spaceflights project dependencies are stored in `src/requirements.txt`(you may find that the versions differ slightly depending on your chosen version of Kedro):

```text
# code quality packages
black==22.0  
flake8>=3.7.9, <5.0 
ipython>=7.31.1, <8.0 
isort~=5.0 
nbstripout~=0.4 

# notebook tooling
jupyter~=1.0 
jupyterlab~=3.0 
jupyterlab_server>=2.11.1, <2.16.0

# Pytest + useful extensions
pytest-cov~=3.0 
pytest-mock>=1.7.1, <2.0 
pytest~=7.2 

# Kedro dependencies and datasets to work with different data formats (including CSV, Excel, and Parquet)
kedro~=0.18.5
kedro-datasets[pandas.CSVDataSet, pandas.ExcelDataSet, pandas.ParquetDataSet]~=1.0.0
kedro-telemetry~=0.2.0
kedro-viz~=5.0 # Visualise your pipelines
 
# For modelling in the data science pipeline
scikit-learn~=1.0
```

To install all the project-specific dependencies, run the following from the project root directory:

```bash
pip install -r src/requirements.txt
```

You can learn more about [project dependencies](../kedro_project_setup/dependencies.md) in the Kedro documentation.


## Optional: logging and configuration

You might want to [set up logging](../logging/logging.md) at this stage of the workflow, but we do not use it in this tutorial.

You may also want to store credentials such as usernames and passwords if they are needed for specific data sources used by the project.

To do this, add them to `conf/local/credentials.yml` (some examples are included in that file for illustration).

### Configuration best practice to avoid leaking confidential data?

* Do not commit data to version control.
* Do not commit notebook output cells (data can easily sneak into notebooks when you don't delete output cells).
* Do not commit credentials in `conf/`. Use only the `conf/local/` folder for sensitive information like access credentials.

You can find additional information in the [advanced documentation on configuration](../kedro_project_setup/configuration.md).
