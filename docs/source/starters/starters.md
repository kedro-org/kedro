# Kedro starters

<!--TO DO-->
<!--This page needs updating-->


A Kedro starter contains code in the form of a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template for a Kedro project. Metaphorically, a starter is similar to using a pre-defined layout when creating a presentation or document.

Kedro starters provide pre-defined example code and configuration that can be reused, for example:

* As template code for a typical Kedro project
* To add a `docker-compose` setup to launch Kedro next to a monitoring stack
* To add deployment scripts and CI/CD setup for your targeted infrastructure

You can create your own starters for reuse within a project or team, as described in the documentation about [how to create a Kedro starter](../starters/create_a_starter.md).

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

The Kedro team maintains the following starters for a range of Kedro projects:

* [`astro-airflow-iris`](https://github.com/kedro-org/kedro-starters/tree/main/astro-airflow-iris): The [Kedro Iris dataset example project](../get_started/new_project.md) with a minimal setup for deploying the pipeline on Airflow with [Astronomer](https://www.astronomer.io/).
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

By default, when you create a new project using a starter, `kedro new` asks you to enter the `project_name`, which it uses to set the `repo_name` and `python_package` name. This is the same behavior as when you [create a new empty project](../get_started/new_project.md#create-a-basic-project)

However, Kedro also allows you to [specify a configuration file](../get_started/new_project.md#create-a-basic-project-from-a-configuration-file) when you create a project using a Kedro starter. Use the `--config` flag alongside the starter:

```bash
kedro new --config=my_kedro_pyspark_project.yml --starter=pyspark
```

This option is useful when the starter requires more configuration than the default mode requires.
