# Kedro starters

A Kedro starter contains code in the form of a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template for a Kedro project. Metaphorically, a starter is similar to using a pre-defined layout when creating a presentation or document.

Kedro starters provide pre-defined example code and configuration that can be reused, for example:

* As template code for a typical Kedro project
* To add a `docker-compose` setup to launch Kedro next to a monitoring stack
* To add deployment scripts and CI/CD setup for your targeted infrastructure

You can create your own starters for reuse within a project or team, as described in the documentation about [how to create a Kedro starter](../kedro_project_setup/starters.md#how-to-create-a-kedro-starter).

## How to use Kedro starters

To create a Kedro project using a starter, apply the `--starter` flag to `kedro new`:

```bash
kedro new --starter=<path-to-starter>
```

```{note}
`path-to-starter` could be a local directory or a VCS repository, as long as [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html) supports it.
```

To create a project using the `PySpark` starter:

```bash
kedro new --starter=pyspark
```

## Starter aliases

We provide aliases for common starters maintained by the Kedro team so that users don't have to specify the full path. For example, to use the `PySpark` starter to create a project:

```bash
kedro new --starter=pyspark
```

To list all the aliases we support:

```bash
kedro starter list
```

## List of official starters

The Kedro team maintains the following starters for a range of Kedro projects:

* [`astro-airflow-iris`](https://github.com/kedro-org/kedro-starters/tree/main/astro-airflow-iris): The [Kedro Iris dataset example project](../get_started/new_project.md) with a minimal setup for deploying the pipeline on Airflow with [Astronomer](https://www.astronomer.io/).
* [`standalone-datacatalog`](https://github.com/kedro-org/kedro-starters/tree/main/standalone-datacatalog): A minimum setup to use the traditional [Iris dataset](https://www.kaggle.com/uciml/iris) with Kedro's [`DataCatalog`](../data/data_catalog.md), which is a core component of Kedro. This starter is of use in the exploratory phase of a project. It was formerly known as `mini-kedro`.
* [`pandas-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris): The [Kedro Iris dataset example project](../get_started/new_project.md)
* [`pyspark-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pyspark-iris): An alternative Kedro Iris dataset example, using [PySpark](../integrations/pyspark_integration.md)
* [`pyspark`](https://github.com/kedro-org/kedro-starters/tree/main/pyspark): The configuration and initialisation code for a [Kedro pipeline using PySpark](../integrations/pyspark_integration.md)
* [`spaceflights-pandas`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas): The [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) example code with `pandas` datasets.
* [`spaceflights-pandas-viz`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pandas-viz): The [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) example code with `pandas` datasets and visualisation and experiment tracking `kedro-viz` features.
* [`spaceflights-pyspark`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pyspark): The [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) example code with `pyspark` datasets.
* [`spaceflights-pyspark-viz`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights-pyspark-viz): The [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) example code with `pyspark` datasets and visualisation and experiment tracking `kedro-viz` features.

## Starter versioning

By default, Kedro will use the latest version available in the repository, but if you want to use a specific version of a starter, you can pass a `--checkout` argument to the command:

```bash
kedro new --starter=pyspark --checkout=0.1.0
```

The `--checkout` value points to a branch, tag or commit in the starter repository.

Under the hood, the value will be passed to the [`--checkout` flag in Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html#works-directly-with-git-and-hg-mercurial-repos-too).


## Use a starter with a configuration file

By default, when you create a new project using a starter, `kedro new` asks you to enter the `project_name`, which it uses to set the `repo_name` and `python_package` name. This is the same behavior as when you [create a new empty project](../get_started/new_project.md#create-a-new-empty-project)

However, Kedro also allows you to [specify a configuration file](../get_started/new_project.md#create-a-new-project-from-a-configuration-file) when you create a project using a Kedro starter. Use the `--config` flag alongside the starter:

```bash
kedro new --config=my_kedro_pyspark_project.yml --starter=pyspark
```

This option is useful when the starter requires more configuration than the default mode requires.

## How to create a Kedro starter

Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. A good example is the Iris dataset example of basic Kedro project layout, configuration and initialisation code. A team may find it useful to build Kedro starters to create reusable projects that bootstrap a common base and can be extended.

A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template that contains the boilerplate code for a Kedro project.

To create a Kedro starter, you need a base project to convert to a `cookiecutter` template, which forms the boilerplate for all projects that use the Kedro starter.

Install `cookiecutter` as follows:

```bash
pip install cookiecutter
```

You then need to decide which are:

* the common, boilerplate parts of the project
* the configurable elements, which need to be replaced by `cookiecutter` strings

### Configuration variables

By default, when you create a new project using a Kedro starter, `kedro new` launches in interactive mode. The user is then prompted for the variables that have been set in `prompts.yml`.

The most basic and empty starter triggered by `kedro new` is set up with the following variable:

* `project_name` - A human readable name for the new project

Kedro will then automatically generate the following two variables from the entered `project_name`:

* `repo_name` - A name for the directory that holds the project repository
* `python_package` - A Python package name for the project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

See the configuration for this basic configuration in [the default starter setup](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/prompts.yml).

As the creator of the Kedro starter you can customise the prompts triggered by `kedro new` by adding your own prompts in `prompts.yml`. This is an example of a custom prompt:

```yaml
custom_prompt:
    title: "Prompt title"
    text: |
      Prompt description that explains to the user what
      information they should provide.
```

At the very least, the prompt `title` must be defined for the prompt to be valid. After Kedro gets the user's input for each prompt, we pass the value to [`cookiecutter`](https://cookiecutter.readthedocs.io/en/1.7.2/), so every key in your `prompts.yml` must have a corresponding key in [`cookiecutter.json`](https://cookiecutter.readthedocs.io/en/1.7.2/tutorial1.html#cookiecutter-json).

If the input to the prompts needs to be **validated**, for example to make sure it only has alphanumeric characters, you can add regex validation rules via the `regex_validator` key. For more complex validation, have a look at [cookiecutter pre/post-generate hooks](https://cookiecutter.readthedocs.io/en/1.7.2/advanced/hooks.html#using-pre-post-generate-hooks-0-7-0).

If you want `cookiecutter` to provide sensible **defaults** in case a user doesn't provide any input, you can add those to `cookiecutter.json`. See [the default starter `cookiecutter.json`](https://github.com/kedro-org/kedro/blob/main/kedro/templates/project/cookiecutter.json) as example.

### Example Kedro starter

To review an example Kedro starter, check out the [`pandas-iris` starter on GitHub](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris).

When you create an Iris dataset example project by calling `kedro new`, you supply configuration variables as the documentation in [Create a new project](../get_started/new_project.md) describes. When you go through the interactive flow you must supply the `project_name` variable, which is then used to generate the `repo_name` and `python_package` variables. If you use a configuration file, you must supply all three variables in the file. You can see how these variables are used by inspecting the template:

**project_name**

The human-readable `project_name` variable is used in the [README.md](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/README.md) for the new project.

**repo_name**

The project structure contains a folder labelled [`{{ cookiecutter.repo_name }}`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D), which forms the top-level folder to contain the Iris dataset example when it is created. The folder storing the example project is represented by `cookiecutter.repo_name`, which is a customisable variable, as you would expect.

**python_package**

Within the parent folder, inside the `src` subfolder, is another configurable variable [{{ cookiecutter.python_package }}](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D) which contains the source code for the example pipelines. The variable is also used within [`__main__.py`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris/%7B%7B%20cookiecutter.repo_name%20%7D%7D/src/%7B%7B%20cookiecutter.python_package%20%7D%7D/__main__.py).

Here is the layout of the project as a Cookiecutter template:

```
{{ cookiecutter.repo_name }}     # Parent directory of the template
├── conf                         # Project configuration files
├── data                         # Local project data (not committed to version control)
├── docs                         # Project documentation
├── notebooks                    # Project related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── README.md                    # Project README
└── src                          # Project source code
    └── {{ cookiecutter.python_package }}
       ├── __init.py__
       ├── pipelines
       ├── pipeline_registry.py
       ├── __main__.py
       └── settings.py
    ├── requirements.txt
    ├── pyproject.toml
    └── tests
```

```{note}
You can [add an alias by creating a plugin using `kedro.starters` entry point](../extend_kedro/plugins.md#extend-starter-aliases), which will allows you to do `kedro new --starter=your_starters` and shows up on shows up on `kedro starter list`.
```
