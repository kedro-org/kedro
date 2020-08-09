# Create a new project

Once you have [installed Kedro](./02_install.md), you can create a new project interactively by answering a series of questions, or by using settings recorded in a configuration file.

## Create a new project interactively

Create a new project in your current working directory:

```bash
kedro new
```

You will be asked to enter each of the following variables in turn. Once you have entered text for the first option (the project's name), you will be offered a default choice for the other options:

```eval_rst
+------------------------+-------------------------+----------------------------------------------------------------------------+
| Option                 | Example                 | Description                                                                |
+========================+=========================+============================================================================+
| :code:`project_name`   | :code:`Getting Started` | A human-readable name for your new project                                 |
+------------------------+-------------------------+----------------------------------------------------------------------------+
| :code:`repo_name`      | :code:`getting-started` | Directory that holds your project repository                               |
+------------------------+-------------------------+----------------------------------------------------------------------------+
| :code:`python_package` | :code:`getting_started` | A name for the Python package name in your project (short, all-lowercase)  |
+------------------------+-------------------------+----------------------------------------------------------------------------+
| :code:`include_example`| :code:`Y/n`             | Confirms or rejects the inclusion of the Iris example code                 |
|                        |                         | Your new project template contains a small example if you enter :code:`Y`  |
+------------------------+-------------------------+----------------------------------------------------------------------------+

```


The output lists the directory in which to find the project.

## Create a new project from a configuration file

You can create a new project from a configuration file if you prefer. The file must contain:

-   `output_dir` The path in which to create the project directory. For example, the path can be `~` for your home directory, or `.` for the current working directory.
-   `project_name`
-   `repo_name`
-   `python_package`
-   `include_example` (Boolean value) option to confirm or reject the inclusion of the [Iris example code](../02_get_started/05_example_project.md)

Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: Get Started
repo_name: get-started
python_package: get_started
include_example: true
```

To create the new project:

```bash
kedro new --config config.yml
```

## Initialise a `git` repository

Having created your new project, if you are using `git`, you may want to set up a new repository by calling:

```bash
git init
```

## Create a new project using starters

Kedro supports using custom starter templates to create your project via the `--starter` flag. To learn more about this feature, please read the guide to [creating new projects with Kedro Starters](./06_starters.md).
