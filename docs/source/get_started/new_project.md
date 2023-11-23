# Create a new Kedro project

There are several ways to create a new Kedro project. This page explains the flow to create a basic project using `kedro new` and selecting from a range of tools and example codes to extend the basic project. The output of `kedro new` is a directory containing all the project files and subdirectories required. The exact code added for the project will depend on your choice of tools and example code as we'll discuss.

You can also create a new Kedro project with a starter that adds a set of code for a common project use case. [Starters are explained separately](../starters/starters.md) later in the documentation set and illustrated with the [spaceflights tutorial](../tutorial/tutorial_template.md).

## Introducing `kedro new`

You can create a basic Kedro project containing the default code needed to set up your own nodes and pipelines. Navigate to your preferred directory and type:

```bash
kedro new
```

The command line interface then asks you to enter a name for the project. This is the human-readable name, and it may contain alphanumeric symbols, spaces, underscores, and hyphens. It must be at least two characters long.

It's best to keep the name simple because the choice is set as the value of `project_name` and is also used to generate the folder and package names for the project automatically.

So, if you enter "Get Started", the folder for the project (`repo_name`) is automatically set to be `get-started`, and the Python package name (`python_package`) for the project is set to be `get_started`.

| Description                                                     | Setting          | Example       |
| --------------------------------------------------------------- | ---------------- | ------------- |
| A human-readable name for the new project                      | `project_name`   | `Get Started` |
| Local directory to store the project                           | `repo_name`      | `get-started` |
| The Python package name for the project (short, all-lowercase) | `python_package` | `get_started` |

## Project tools

The command line interface then asks which tools you'd like to include in the project. The options are as follows and described in more detail above in the [documentation about the new project tools](../starters/new_project_tools.md).

You can add one or more of the options, or follow the default and add none at all:

* Linting: A basic linting setup with Black and ruff
* Testing: A basic testing setup with pytest
* Custom Logging: Additional logging options
* Documentation: Configuration for basic documentation built with Sphinx
* Data Structure: The [directory structure](../faq/faq.md#what-is-data-engineering-convention) for storing data locally
* PySpark: Setup and configuration for working with PySpark
* Kedro Viz: Kedro's native visualisation tool.

## Project example

TO DO


## Create a basic project from a configuration file

To create a new project with custom directory and package names, navigate to your preferred directory and type the following command, which passes in a configuration file `config.yml`:

```bash
kedro new --config=<path>/config.yml
```
The configuration file must contain:

-   `output_dir` The path in which to create the project directory
-   `project_name`
-   `repo_name`
-   `python_package`

The `output_dir` can be set to `~` for the home directory or `.` for the current working directory. Here is an example `config.yml`, which assumes that a directory named `~/code` already exists:

```yaml
output_dir: ~/code
project_name: My First Kedro Project
repo_name: testing-kedro
python_package: test_kedro
```

## Run the project

However you create a Kedro project, once `kedro new` has completed, the next step is to navigate to the project folder (`cd <project-name>`) and install dependencies with `pip` as follows:

```bash
pip install -r requirements.txt
```

Now run the project:

```bash
kedro run
```

```{note}
The first time you type a `kedro` command in a new project, you will be asked whether you wish to opt into [usage analytics](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-telemetry). Your decision is recorded in the `.telemetry` file so that subsequent calls to `kedro` in this project do not ask this question again.
```

## Visualise a Kedro project

This section swiftly introduces project visualisation using Kedro-Viz. See the {doc}`Kedro-Viz documentation<kedro-viz:kedro-viz_visualisation>` for more detail.

The Kedro-Viz package needs to be installed into your virtual environment separately as it is not part of the standard Kedro installation:

```bash
pip install kedro-viz
```

To start Kedro-Viz, navigate to the project folder (`cd <project-name>`) and enter the following in your terminal:

```bash
kedro viz
```

This command automatically opens a browser tab to serve the visualisation at `http://127.0.0.1:4141/`.

To exit the visualisation, close the browser tab. To regain control of the terminal, enter `^+c` on Mac or `Ctrl+c` on Windows or Linux machines.

## Summary

After you have [set up Kedro](install.md), you can use `kedro new` to create a basic Kedro project containing project directories and basic code, which you can configure depending on the tooling and example code you need.

Alternatively, you can use `kedro new` and [pass in a configuration file](#create-a-basic-project-from-a-configuration-file) to manually control project details such as the name, folder and package name.

After you create a new project you need to navigate to its project folder and install its dependencies: `pip install -r requirements.txt`

* **To run the project**: `kedro run`
* **To visualise the project**: `kedro viz`

### Where next?
You have completed the section on Kedro project creation for new users. Here are some useful resources to learn more:

* Understand more about Kedro: The following page explains the [fundamental Kedro concepts](./kedro_concepts.md).

* Learn hands-on: If you prefer to learn hands-on, move on to the [spaceflights tutorial](../tutorial/spaceflights_tutorial.md). The tutorial illustrates how to set up a working project, add dependencies, create nodes, register pipelines, set up the Data Catalog, add documentation, and package the project.

* How-to guide for notebook users: The documentation section following the tutorial explains [how to combine Kedro with a Jupyter notebook](../notebooks_and_ipython/kedro_and_notebooks.md).

If you've worked through the documentation listed and are unsure where to go next, review the [Kedro repositories on GitHub](https://github.com/kedro-org) and [Kedro's Slack channels](https://slack.kedro.org).
