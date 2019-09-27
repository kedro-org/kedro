# Creating a new project

We recommend that you create projects according to the Kedro default project template, which is ideal for analytics projects and comes with a default folder structure for storing datasets, folders for notebooks, configuration and source code.

Projects can be created interactively or by referencing a configuration file.

## Create a new project interactively
First, select the directory in which you want to work, and if you are using `conda`, make sure you have the [correct environment](../02_getting_started/01_prerequisites.md#Python-virtual-environments) activated:

```bash
conda activate environment_name
```
You are then ready to create a new project:

```bash
kedro new
```

You will need to provide the following variables:

* `project_name` - A human readable name for your new project
* `repo_name` - A name for the directory that holds your project repository
* `python_package` - A Python package name for your project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))
* `include_example` - An affirmative for whether you want to include example code

`kedro new` will create a new project in your current working directory (`<current_dir>/<repo_name>/`). If you entered `Y` to include an example then your new project template contains a small example to get you going. See the [Hello World example](../02_getting_started/04_hello_world.md) for further details.


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

## Starting with an existing project

If you want to work with a Kedro project that has already been created, you may use `git clone` to directly clone it. You don’t need to create a new Kedro project.

## Install project dependencies

Project dependencies are listed under `src/requirements.txt`. You can run the following command

```bash
kedro install
```

to install the dependencies, using the aforementioned file as source of truth.

You can either use the file as is from the project template, or you can run:

```bash
kedro build-reqs
```

This will `pip-compile` requirements from `src/requirements.in` (if non-existent, it will create it with the contents of `requirements.txt` copied over) and generate the list of pinned project dependencies in `src/requirements.txt`. From that point onward, you should only update `requirements.in` and run `build-reqs` to update the project requirements.

If your project has conda dependencies which you would like to install with this command, you can create a `src/environment.yml` file and list them there.
