# Creating a new project

We recommend that you create projects according to the Kedro default project template, which is ideal for analytics projects and comes with a default folder structure for storing datasets, folders for notebooks, configuration and source code.

Projects can be created interactively or by referencing a configuration file.

> You can also work with a Kedro project that has already been created. In this case, you don’t need to create a new Kedro project, but can use `git clone` to clone the existing project.

## Create a new project interactively
First, select the directory in which you want to work, and if you are using `conda`, make sure you have the [correct environment](../02_getting_started/01_prerequisites.md#conda) activated:

```bash
conda activate environment_name
```
You are then ready to create a new project.

Call `kedro new` to create a new project in your current working directory (`<current_dir>/<repo_name>/`):

```bash
kedro new
```

You will need to provide the following variables:

* `project_name` - A human readable name for your new project
* `repo_name` - A name for the directory that holds your project repository
* `python_package` - A Python package name for your project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))
* `include_example` - Confirms or rejects the inclusion of example code. If you enter `Y` to include an example then your new project template contains a small example to get you going. See the [Hello World example](../02_getting_started/04_hello_world.md) for further details


## Create a new project from a configuration file

You can also create a new project from a configuration file by running:

```bash
kedro new --config config.yml
```

The configuration file (`config.yml`) must contain the `project_name`, `repo_name`, `python_package` and `include_example` (Boolean value) variables as described [above](../02_getting_started/03_new_project.md#Create-a-new-project-interactively) as well as `output_dir` - path to the directory where the project folder will be created.

Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: Getting Started
repo_name: getting-started
python_package: getting_started
include_example: true
```

`output_dir` can be set to `~` for home directory, or `.` for the current working directory.

## Working with your new project

### Initialise a `git` repository

Having created a new project, you may want to set up a new `git` repository by calling:

```bash
git init
```

### Specify project-specific dependencies

Once you have created a generic new project, you can update its dependencies to those required by the project. The project template bundles some typical dependencies, in `src/requirements.txt`.

To add or remove dependencies on your first use, either edit `src/requirements.txt` as is, or run:

```bash
kedro build-reqs
```

The `build-reqs` command will:

* `pip-compile` requirements from `src/requirements.in`. If the `src/requirements.in` file is non-existent, Kedro will generate it from the contents of `requirements.txt`).
* Regenerate `src/requirements.txt` to specify a list of pinned project dependencies (those with a strict version).

> Note: Whenever you need to update the project requirements, update `requirements.in` (not `src/requirements.txt`) and run `kedro build-reqs` again.

If your project has `conda` dependencies, you can create a `src/environment.yml` file and list them there.

### Install project-specific dependencies

To install the project-specific dependencies, run the following command:

```bash
kedro install
```
