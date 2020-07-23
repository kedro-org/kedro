# Create a new project

In this guide, we explain how to create a new Kedro project.

> Note: We assume that you have [installed Kedro](../02_get_started/02_install.md).

You can create a blank Kedro project, or use a Kedro starter to provide a template to build upon, covered in more detail in the next example, based on the [Iris dataset](../02_get_started/05_example_project).

## Create a new blank project

You can create a new project in the console, either using the default and providing a set of variables when prompted, or by using a configuration file to provide the variables.

### Create a new blank project interactively

To create a new blank project in your current working directory:

```bash
kedro new
```

You will be asked to enter each of the following variables in turn. Once you have entered text for the first option (the project's name), you will be offered a default choice for the other options:

```eval_rst
+------------------------+---------------------+----------------------------------------------------+
| Option                 | Example             | Description                                        |
+========================+=====================+====================================================+
| :code:`project_name`   | :code:`Get Started` | A human-readable name for your new project         |
+------------------------+---------------------+----------------------------------------------------+
| :code:`repo_name`      | :code:`get-started` | Directory that holds your project repository       |
+------------------------+---------------------+----------------------------------------------------+
| :code:`python_package` | :code:`get_started` | A name for the Python package name in your project |
|                        |                     | (short, all-lowercase)                             |
+------------------------+---------------------+----------------------------------------------------+
```

The output lists the directory in which to find the project.

### Create a new blank project from a configuration file

You can create a new blank project by providing the same variable via a configuration file `config.yml`:

```bash
kedro new --config config.yml
```

The configuration file must contain:

-   `project_name`
-   `repo_name`
-   `python_package`
-   `output_dir` (the path in which to create the project directory)

Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: Get Started
repo_name: get-started
python_package: get_started
```

`output_dir` can be set to `~` for home directory, or `.` for the current working directory.


## Create a new project based on a Kedro starter

Kedro starters are used to create template projects that contain code to run as-is, or to adapt and extend. The Kedro starter projects make a useful alternative to creating a blank project, particularly if you are new to Kedro and want a pre-populated example project to explore.

To create a new project using a Kedro starter, use the `--starter` flag with `kedro new`. The following page about the [Iris dataset example](./05_example_project.md) will walk you through the process, and we provide a guide on [how to create a project with a Kedro starter](./06_starters.md) for additional detail.
