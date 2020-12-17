# Set up the spaceflights project

In this section, we discuss the project set-up phase, which is the first part of the [standard development workflow](./01_spaceflights_tutorial.md#kedro-project-development-workflow). The set-up steps are as follows:


* Create a new project
* Install dependencies
* Configure the project


## Create a new project

Navigate to your chosen working directory and run the following to [create a new empty Kedro project](../02_get_started/04_new_project.md#create-a-new-project-interactively) using the default interactive prompts:

```bash
kedro new
```

Feel free to name your project as you like, but this guide will assume the project is named **`Kedro Tutorial`**.

Keep the default names for the `repo_name` and `python_package` when prompted.

## Install project dependencies

Up to this point, we haven't discussed project dependencies, so now is a good time to introduce them. Specifying a project's dependencies in Kedro makes it easier for others to run your project; it avoids version conflicts by use of the same Python packages.

The generic project template bundles some typical dependencies, in `src/requirements.txt`. Here's a typical example, although you may find that the version numbers are slightly different depending on the version of Kedro that you are using:

```text
black==v19.10b0 # Used for formatting code with `kedro lint`
flake8>=3.7.9, <4.0 # Used for linting code with `kedro lint`
ipython~=7.0 # Used for an IPython session with `kedro ipython`
isort>=4.3.21, <5.0 # Used for linting code with `kedro lint`
jupyter~=1.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyter_client>=5.1.0, <7.0 # Used to open a Kedro-session in Jupyter Notebook & Lab
jupyterlab==0.31.1 # Used to open a Kedro-session in Jupyter Lab
kedro==0.17.0
kedro-viz~=3.1
nbstripout==0.3.3 # Strips the output of a Jupyter Notebook and writes the outputless version to the original file
pytest-cov~=2.5 # Produces test coverage reports
pytest-mock>=1.7.1,<2.0 # Wrapper around the mock package for easier use with pytest
pytest~=6.1.2 # Testing framework for Python code
wheel==0.32.2 # The reference implementation of the Python wheel packaging standard
```

> Note: If your project has `conda` dependencies, you can create a `src/environment.yml` file and list them there.

### Add and remove project-specific dependencies

The dependencies above may be sufficient for some projects, but for the spaceflights project, you need to add a requirement for the `pandas` project because you are working with CSV and Excel files. You can add the necessary dependencies for these files types as follows:

```bash
pip install kedro[pandas.CSVDataSet,pandas.ExcelDataSet]
```

Alternatively, if you need to, you can edit `src/requirements.txt` directly to modify your list of dependencies by replacing the requirement `kedro==0.17.0` with the following (your version of Kedro may be different):

```text
kedro[pandas.CSVDataSet,pandas.ExcelDataSet]==0.17.0
```

Then run the following:

```bash
kedro build-reqs
```

You can find out more about [how to work with project dependencies](../04_kedro_project_setup/01_dependencies) in the Kedro project documentation. In a [later step of this tutorial](./04_create_pipelines.html#update-dependencies), we will modify project's dependencies to illustrate how, once you have installed project-specific dependencies, you can update them.

## `kedro install`

To install the project-specific dependencies, navigate to the root directory of the project and run:

```bash
kedro install
```
You can find further information in our [advanced documentation about working with dependencies](../04_kedro_project_setup/01_dependencies.md).

## Configure the project

You need to configure the credentials within your project's `conf` folder:

* Move `credentials.yml` from `conf/base/` to `conf/local/`. To do this in the terminal, type the following from within the project's root directory:

```bash
mv conf/base/credentials.yml conf/local/
```

* You may optionally add in any credentials to `conf/local/credentials.yml` that you would need to load specific data sources like usernames and passwords. Some examples are given within the file to illustrate how you store credentials. Additional information can be found in the [advanced documentation on configuration](../04_kedro_project_setup/02_configuration.md).

At this stage of the workflow, you may also want to [set up logging](../08_logging/01_logging.md), but we do not use it in this tutorial.
