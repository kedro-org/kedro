# Create a new Kedro project

There are several ways to create a new Kedro project depending on whether you want it to contain:

* just the [default project code](#create-a-new-empty-project)
* some ["starter" code as a sample](#create-a-new-project-containing-example-code), to run as-is or to adapt and extend.

## Create a new empty project

You can create a default Kedro project containing just the code needed to set up your own nodes and pipelines. Navigate to your preferred directory and type:

```bash
kedro new
```

Enter a name for the project, which can be human-readable and may contain alphanumeric symbols, spaces, underscores and hyphens. It must be at least two characters long.

It's best to keep the name simple because the choice is set as the value of `project_name` and is also used to generate the folder and package names for the project automatically.

So, if you enter "Get Started", the folder for the project (`repo_name`) is automatically set to be `get-started`, and the Python package name (`python_package`) for the project is set to be `get_started`.

| Description                                                     | Setting          | Example       |
| --------------------------------------------------------------- | ---------------- | ------------- |
| A human-readable name for the new project                      | `project_name`   | `Get Started` |
| Local directory to store the project                           | `repo_name`      | `get-started` |
| The Python package name for the project (short, all-lowercase) | `python_package` | `get_started` |


The output of `kedro new` is a directory containing all the project files and subdirectories required for a basic Kedro project, ready to extend with the code. The exact code added for the project will depend on which add-ons you select, described as follows:

### Kedro add-ons
<!--TO DO-->
<!--Add in some basic new content about using add-ons with kedro new. Don't add too much detail here.-->

### Create a new empty project from a configuration file

To create a new project with custom directory and package names, pass in a configuration file as follows:

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
## Create a new project containing example code

Use a [Kedro starter](../kedro_project_setup/starters.md) to create a project containing some sample code, to run as-is or to adapt and extend.


<!--TO DO-->
<!--Add in new content about using add-ons with a starter-->

The following illustrates a project created with example code based on the familiar [Iris dataset](https://www.kaggle.com/uciml/iris).

The first step is to create the Kedro project using a starter to add the example code and data.

```bash
kedro new --starter=pandas-iris
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

There are a few ways to create a new project once you have [set up Kedro](install.md):

* You can [create a Kedro project populated with template code](#create-a-new-project-containing-example-code) that acts as a starter example. There is a [range of Kedro starter projects](../starters/starters.md#list-of-official-starters) available to use.
* You can use `kedro new` to [create a basic Kedro project](#create-a-new-empty-project) containing project directories and basic code, but empty to extend as you need.
* You can use `kedro new` and [pass in a configuration file](#create-a-new-project-from-a-configuration-file) to manually control project details such as the name, folder and package name.


For any new project, once it is created, you need to navigate to its project folder and install its dependencies: `pip install -r requirements.txt`

* **To run the project**, from the project folder type `kedro run`
* **To visualise the project**, from the project folder type `kedro viz`

### Where next?
You have completed the section on Kedro project creation for new users. Here are some useful resources to learn more:

* Understand more about Kedro: The following page explains the [fundamental Kedro concepts](./kedro_concepts.md).

* Learn hands-on: If you prefer to learn hands-on, move on to the [spaceflights tutorial](../tutorial/spaceflights_tutorial.md). The tutorial illustrates how to set up a working project, add dependencies, create nodes, register pipelines, set up the Data Catalog, add documentation, and package the project.

* How-to guide for notebook users: The documentation section following the tutorial explains [how to combine Kedro with a Jupyter notebook](../notebooks_and_ipython/kedro_and_notebooks.md).

If you've worked through the documentation listed and are unsure where to go next, review the [Kedro repositories on GitHub](https://github.com/kedro-org) and [Kedro's Slack channels](https://slack.kedro.org).
