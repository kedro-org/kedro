# Set up the spaceflights tutorial project

In this section, we discuss the project set-up phase, which is the first part of the standard development workflow. The setup steps are as follows:

* Create a new project with `kedro new`
* Install project dependencies with `pip install -r src/requirements.txt`
* Configure the following in the `conf` folder:
	* Credentials and any other sensitive information
	* Logging

```{note}
Don't forget to check the [tutorial FAQ](spaceflights_tutorial_faqs.md) if you run into problems, or [ask the community for help](spaceflights_tutorial.md#get-help) if you need it!
```

## Create a new project

If you have not yet set up Kedro, do so by [following the guidelines to install Kedro](../get_started/install.md).

```{important}
We recommend that you use the same version of Kedro that was most recently used to test this tutorial (0.18.5).
```

In your terminal window, navigate to the folder you want to store the project and type the following to create an empty project:

```bash
kedro new
```

Alternatively, if you want to include a complete set of working example code within the project, generate the project from the [Kedro starter for the spaceflights tutorial](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights):

```bash
kedro new --starter=spaceflights
```

For either option, when prompted for a project name, enter `Kedro Tutorial`. When Kedro has created your project, you can navigate to the [project root directory](./spaceflights_tutorial.md#project-root-directory):

```bash
cd kedro-tutorial
```

## Project dependencies

Kedro projects have a `requirements.txt` file to specify their dependencies and enable sharable projects by ensuring consistency across Python packages and versions.

The generic project template bundles some typical dependencies in `src/requirements.txt`. Here's a typical example, although you may find that the version numbers differ slightly depending on your version of Kedro:

```text
# code quality packages
black==22.1.0 # Used for formatting code with `kedro lint`
flake8>=3.7.9, <5.0 # Used for linting code with `kedro lint`
ipython==7.0 # Used for an IPython session with `kedro ipython`
isort~=5.0 # Used for linting code with `kedro lint`
nbstripout~=0.4 # Strips the output of a Jupyter Notebook and writes the outputless version to the original file

# notebook tooling
jupyter~=1.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyterlab~=3.0 # Used to open a Kedro-session in Jupyter Lab

# Pytest + useful extensions
pytest-cov~=3.0 # Produces test coverage reports
pytest-mock>=1.7.1, <2.0 # Wrapper around the mock package for easier use with pytest
pytest~=6.2 # Testing framework for Python code
```

You can learn more about [project dependencies](../kedro_project_setup/dependencies.md) in the Kedro documentation.

### Add dependencies to the project

The dependencies above might be sufficient for some projects, but for this tutorial, you must add some extra requirements. These requirements will enable us to work with different data formats (including CSV, Excel, and Parquet) and to visualise the pipeline.

> If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste, but it's worth opening `src/requirements.txt` to inspect the contents.

Add the following lines to your `src/requirements.txt` file:

```text
kedro==0.18.5
kedro-datasets[pandas.CSVDataSet, pandas.ExcelDataSet, pandas.ParquetDataSet]~=1.0.2  # Specify Kedro-Datasets dependencies
kedro-viz~=5.0                                                                 # Visualise your pipelines
scikit-learn~=1.0                                                              # For modelling in the data science pipeline
```

### Install the dependencies

To install all the project-specific dependencies, run the following from the project root directory:

```bash
pip install -r src/requirements.txt
```

## Optional: configuration and logging

You may want to store credentials such as usernames and passwords if they are needed for specific data sources used by the project.

To do this, add them to `conf/local/credentials.yml` (some examples are included in that file for illustration).

You can find additional information in the [advanced documentation on configuration](../kedro_project_setup/configuration.md).

You might also want to [set up logging](../logging/logging.md) at this stage of the workflow, but we do not use it in this tutorial.
