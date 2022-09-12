# Create a new project

Once you have [installed Kedro](./install.md), to create a new, empty project, you can answer a series of questions, or use settings recorded in a configuration file.

If you want to create a Kedro project that is populated with some template or example code, you can specify the `--starter` flag to use Kedro starters. Read the guide to [creating new projects with Kedro Starters](./starters.md) for more information.

## Create a new project interactively

Create a new project in your current working directory:

```bash
kedro new
```

You will be asked to enter the `project_name`. The `project_name` must be at least two characters long, and only contain alphanumeric symbols, spaces, underscores and hyphens. The `project_name` is used to automatically generate the `repo_name` and `python_package`.

| Option           | Example       | Description                                                               |
| ---------------- | ------------- | ------------------------------------------------------------------------- |
| `project_name`   | `Get Started` | A human-readable name for your new project                                |
| `repo_name`      | `get-started` | Directory that holds your project repository                              |
| `python_package` | `get_started` | A name for the Python package name in your project (short, all-lowercase) |


The output lists the directory in which to find the project.

## Create a new project from a configuration file

You can create a new project from a configuration file if you prefer. The file must contain:

-   `output_dir` The path in which to create the project directory
-   `project_name`
-   `repo_name`
-   `python_package`

The `output_dir` can be set to wherever you want to create the project. For example, `~` for your home directory, or `.` for the current working directory. Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: Get Started
repo_name: get-started
python_package: get_started
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
