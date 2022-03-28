# Set up the spaceflights project

In this section, we discuss the project set-up phase, which is the first part of the [standard development workflow](./spaceflights_tutorial.md#kedro-project-development-workflow). The set-up steps are as follows:

* Create a new project
* Install dependencies
* Configure the project

## Create a new project

Navigate to your chosen working directory and run the following to [create a new empty Kedro project](../get_started/new_project.md#create-a-new-project-interactively) using the default interactive prompts:

```bash
kedro new
```

When prompted for a project name, enter `Kedro Tutorial`. Subsequently, accept the default suggestions for `repo_name` and `python_package` by pressing enter. Then navigate to the root directory of the project, `kedro-tutorial`.

## Install dependencies

Up to this point, we haven't discussed project dependencies, so now is a good time to examine them. We use a `requirements.txt` file to specify a project's dependencies and make it easier for others to run your project. This avoids version conflicts by ensuring that you use same Python packages and versions.

The generic project template bundles some typical dependencies, in `src/requirements.txt`. Here's a typical example, although you may find that the version numbers are slightly different depending on the version of Kedro that you are using:

```text
black==22.1.0 # Used for formatting code with `kedro lint`
flake8>=3.7.9, <4.0 # Used for linting code with `kedro lint`
ipython==7.0 # Used for an IPython session with `kedro ipython`
isort~=5.0 # Used for linting code with `kedro lint`
jupyter~=1.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyter_client>=5.1.0, <8.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyterlab~=3.0 # Used to open a Kedro-session in Jupyter Lab
kedro==0.17.7
nbstripout~=0.4 # Strips the output of a Jupyter Notebook and writes the outputless version to the original file
pytest-cov~=3.0 # Produces test coverage reports
pytest-mock>=1.7.1, <2.0 # Wrapper around the mock package for easier use with pytest
pytest~=6.2 # Testing framework for Python code
```

```eval_rst
.. note::  If your project has ``conda`` dependencies, you can create a ``src/environment.yml`` file and list them there.
```

The dependencies above may be sufficient for some projects, but for this tutorial you need to add some extra requirements. These will enable us to work with different data formats (including CSV, Excel and Parquet) and to visualise the pipeline.

Edit your `src/requirements.txt` file to include the following lines:

```text
kedro[pandas.CSVDataSet, pandas.ExcelDataSet, pandas.ParquetDataSet]==0.17.7   # Specify optional Kedro dependencies
kedro-viz~=4.0                                                                 # Visualise your pipelines
scikit-learn~=1.0                                                              # For modelling in the data science pipeline
```

To install all the project-specific dependencies, navigate to the root directory of the project and run:

```bash
pip install -r src/requirements.txt
```

You can find out more about [how to work with project dependencies](../kedro_project_setup/dependencies.md) in the Kedro project documentation.


## Configure the project

You may optionally add in any credentials to `conf/local/credentials.yml` that you would need to load specific data sources like usernames and passwords. Some examples are given within the file to illustrate how you store credentials. Additional information can be found in the [advanced documentation on configuration](../kedro_project_setup/configuration.md).

At this stage of the workflow, you may also want to [set up logging](../logging/logging.md), but we do not use it in this tutorial.
