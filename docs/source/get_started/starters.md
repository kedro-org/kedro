# Kedro starters

Kedro starters are used to create projects that contain code to run as-is, or to adapt and extend. They provide pre-defined example code and configuration that can be reused, for example:

* As example code for a typical Kedro project
* To add a `docker-compose` setup to launch Kedro next to a monitoring stack
* To add deployment scripts and CI/CD setup for your targeted infrastructure

A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template that contains the boilerplate code for a Kedro project. You can create your own starters for reuse within a project or team, as described in the documentation about [how to create a Kedro starter](../extend_kedro/create_kedro_starters.md).

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

If no starter is provided to `kedro new`, the default Kedro template will be used, as documented in ["Creating a new project"](./new_project.md).

### Starter aliases

We provide aliases for common starters maintained by the Kedro team so that users don't have to specify the full path. For example, to use the `PySpark` starter to create a project:

```bash
kedro new --starter=pyspark
```

To list all the aliases we support:

```bash
kedro starter list
```

## List of official starters

The Kedro team maintains the following starters to bootstrap new Kedro projects:

* [Alias `astro-airflow-iris`](https://github.com/kedro-org/kedro-starters/tree/main/astro-airflow-iris): The [Kedro Iris dataset example project](../get_started/example_project.md) with a minimal setup for deploying the pipeline on Airflow with [Astronomer](https://www.astronomer.io/).
* [Alias `standalone-datacatalog`](https://github.com/kedro-org/kedro-starters/tree/main/standalone-datacatalog): A minimum setup to use the traditional [Iris dataset](https://www.kaggle.com/uciml/iris) with Kedro's [`DataCatalog`](../data/data_catalog.md), which is a core component of Kedro. This starter is of use in the exploratory phase of a project. For more information, read the guide to [standalone use of the `DataCatalog`](../get_started/standalone_use_of_datacatalog.md). This starter was formerly known as `mini-kedro`.
* [Alias `pandas-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pandas-iris): The [Kedro Iris dataset example project](./example_project.md)
* [Alias `pyspark-iris`](https://github.com/kedro-org/kedro-starters/tree/main/pyspark-iris): An alternative Kedro Iris dataset example, using [PySpark](../tools_integration/pyspark.md)
* [Alias `pyspark`](https://github.com/kedro-org/kedro-starters/tree/main/pyspark): The configuration and initialisation code for a [Kedro pipeline using PySpark](../tools_integration/pyspark.md)
* [Alias `spaceflights`](https://github.com/kedro-org/kedro-starters/tree/main/spaceflights): The [spaceflights tutorial](../tutorial/spaceflights_tutorial.md) example code

## Starter versioning

By default, Kedro will use the latest version available in the repository, but if you want to use a specific version of a starter, you can pass a `--checkout` argument to the command:

```bash
kedro new --starter=pyspark --checkout=0.1.0
```

The `--checkout` value points to a branch, tag or commit in the starter repository.

Under the hood, the value will be passed to the [`--checkout` flag in Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html#works-directly-with-git-and-hg-mercurial-repos-too).

## Use a starter in interactive mode

By default, when you create a new project using a starter, `kedro new` launches [by asking you to enter the `project_name`](./new_project.md#create-a-new-project-interactively).

* `project_name` - A human readable name for your new project

Kedro will then automatically generate the following two variables from the entered `project_name`:

* `repo_name` - A name for the directory that holds your project repository
* `python_package` - A Python package name for your project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

This mode assumes that the starter requires no additional configuration variables.

## Use a starter with a configuration file

Kedro also allows you to [specify a configuration file](./new_project.md#create-a-new-project-from-a-configuration-file) to create a project. Use the `--config` flag alongside the starter:

```bash
kedro new --config=my_kedro_pyspark_project.yml --starter=pyspark
```

This option is useful when the starter requires more configuration than the interactive mode requires.
