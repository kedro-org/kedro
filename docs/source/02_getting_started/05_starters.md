# Creating new projects with Kedro Starters

> *Note:* This documentation is based on `Kedro 0.16.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

When creating a new project, sometimes you might want to customise the starting boilerplate provided by `kedro new` to adapt to different use cases. For example, you might want to:

* Add initial configuration, initialisation code and example pipeline for PySpark
* Add a docker-compose setup to launch Kedro next to a monitoring stack
* Add deployment scripts and CI/CD setup for your targeted infrastructure

To address this need, we have added the ability to supply a starting project template to `kedro new` through a `--starter` flag.

## Introducing Kedro starters

A **Kedro starter** is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template containing boilerplate code for a Kedro project. Each starter should encode best practices and provide utilities to help users bootstrap a new Kedro project for a particular use case in the most effective way. For example, we have created a [`PySpark` starter](https://github.com/quantumblack/kedro-starter-pyspark), which contains initial configuration and initialisation code for PySpark according to our recommended [best practices](../04_user_guide/09_pyspark.md).

To create a Kedro project using a starter, run:

```bash
kedro new --starter=<path-to-starter>
```
The path to starter could be a local directory or a VCS repository, as long as it is supported by [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html).

For example, to create a project using the `PySpark` starter above, run:

```bash
kedro new --starter=https://github.com/quantumblack/kedro-starter-pyspark.git
```

If no starter is provided to `kedro new`, the default Kedro template will be used, as documented in [Creating a new project](./03_new_project.md).

## Using starter aliases

For common starters maintained by Kedro team like `PySpark`, we provide aliases so that users don't have to specify the full path to the starter. For example, to create a project using `PySpark` starter, you can simply run:

```bash
kedro new --starter=pyspark
```

To see a list of all supported aliases, run:

```bash
kedro starter list
```

## List of official starters

The Kedro team maintains the following starters:

```eval_rst
+----------------------+------------------------------------------------------------------------+-------------------------------------------------------------------------------------------+
| Alias                | Link to starter                                                        | Description                                                                               |
+======================+========================================================================+===========================================================================================+
| pandas-iris          | https://github.com/quantumblacklabs/kedro-starter-pandas-iris          | Provide an example iris-classification pipeline built with Kedro                          |
+----------------------+------------------------------------------------------------------------+-------------------------------------------------------------------------------------------+
| pyspark              | https://github.com/quantumblacklabs/kedro-starter-pyspark              | Provide initial configuration and initialisation code for a Kedro pipeline using PySpark  |
+----------------------+------------------------------------------------------------------------+-------------------------------------------------------------------------------------------+
| pyspark-iris         | https://github.com/quantumblacklabs/kedro-starter-pyspark-iris         | Provide all features in the basic PySpark starter, plus an example pipeline to train      |
|                      |                                                                        | a machine learning model with Spark primitives                                            |
+----------------------+------------------------------------------------------------------------+-------------------------------------------------------------------------------------------+
```

## Using a starter's version

By default, Kedro will use the latest commit in the default branch of the starter repository's. However, if you want to use a specific version of a starter, you can pass a `--checkout` argument to the command as follows:

```bash
kedro new --starter=pyspark --checkout=0.1.0
```

The `--checkout` value could point to a branch, tag or commit in the starter repository.
Under the hood, the value will be passed to the [`--checkout` flag in Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html#works-directly-with-git-and-hg-mercurial-repos-too).

## Using starter in interactive mode

By default, creating a new project using a starter will be launched in [interactive mode](./03_new_project.md#Create-a-new-project-interactively). You will need to provide the following variables similar to running `kedro new` without any argument:

* `project_name` - A human readable name for your new project
* `repo_name` - A name for the directory that holds your project repository
* `python_package` - A Python package name for your project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

This mode assumes that the starter doesn't require any additional configuration variable.

## Using starter with a configuration file

As documented in [Creating a new project from a configuration file](./03_new_project.md#Create-a-new-project-from-a-configuration-file), Kedro also supports specifying a configuration file when creating a project through a `--config` flag. You can use this flag with starter seamlessly:

```console
kedro new --config=my_kedro_pyspark_project.yml --starter=pyspark
```

This is particularly useful when the starter requires more configuration than the default variables supported by the interactive mode.
