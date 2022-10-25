# Set up the spaceflights tutorial project

In this section, we discuss the project set-up phase, which is the first part of the [standard development workflow](./spaceflights_tutorial.md#kedro-project-development-workflow). The set-up steps are as follows:

* Create a new project with `kedro new`
* Install project dependencies with `pip install -r src/requirements.txt`
* Configure the following in the `conf` folder:
	* Credentials and any other sensitive information
	* Logging
	
## Create a new project

Navigate to your chosen working directory and run the following to [create a new empty Kedro project](../get_started/new_project.md#create-a-new-project-interactively) using the default interactive prompts:

```bash
kedro new
```

Alternatively, if you want the working example code added to the project in advance, generate a project from the [Kedro starter for the spaceflights tutorial](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights):

```
kedro new --starter=spaceflights
```

When prompted for a project name, enter `Kedro Tutorial`. When your project is ready, navigate to the root directory of the project: `kedro-tutorial`.

## Project dependencies

Up to this point, we have not discussed project dependencies, so now is a good time to examine them. We use a `requirements.txt` file to specify a project's dependencies and make it easier for others to run your project. This avoids version conflicts by ensuring that you use same Python packages and versions.

The generic project template bundles some typical dependencies in `src/requirements.txt`. Here's a typical example, although you may find that the version numbers differ slightly depending on your version of Kedro:

```text
black==22.1.0 # Used for formatting code with `kedro lint`
flake8>=3.7.9, <5.0 # Used for linting code with `kedro lint`
ipython==7.0 # Used for an IPython session with `kedro ipython`
isort~=5.0 # Used for linting code with `kedro lint`
jupyter~=1.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyterlab~=3.0 # Used to open a Kedro-session in Jupyter Lab
kedro~=0.18.3
nbstripout~=0.4 # Strips the output of a Jupyter Notebook and writes the outputless version to the original file
pytest-cov~=3.0 # Produces test coverage reports
pytest-mock>=1.7.1, <2.0 # Wrapper around the mock package for easier use with pytest
pytest~=6.2 # Testing framework for Python code
```

The dependencies above might be sufficient for some projects, but for this tutorial you must add some extra requirements. These requirements will enable us to work with different data formats (including CSV, Excel and Parquet) and to visualise the pipeline.

### Add dependencies to the project

> If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste, but it's worth opening `src/requirements.txt` to inspect the contents.

Add the following lines to your `src/requirements.txt` file:

```text
kedro[pandas.CSVDataSet, pandas.ExcelDataSet, pandas.ParquetDataSet]==0.18.3   # Specify optional Kedro dependencies
kedro-viz~=5.0                                                                 # Visualise your pipelines
scikit-learn~=1.0                                                              # For modelling in the data science pipeline
```

### Install the dependencies

To install all the project-specific dependencies, navigate to the root directory of the project and run:

```bash
pip install -r src/requirements.txt
```

You can find out more about [how to work with project dependencies](../kedro_project_setup/dependencies.md) in the Kedro project documentation.


## Optional: configuration and logging

You may want to store credentials, such as usernames and passwords, if they are needed for specific data sources. 
To do this, add them to `conf/local/credentials.yml`. Some examples are included in that file for illustration. You can find additional information in the [advanced documentation on configuration](../kedro_project_setup/configuration.md).

At this stage of the workflow, you might also want to [set up logging](../logging/logging.md), but we do not use it in this tutorial.
