# Kedro starters


You can use Kedro starters to customise the boilerplate code provided by `kedro new`. This is useful when you need to adapt to different use cases, such as:

* To add initial configuration, initialisation code and an example pipeline for PySpark
* To add a `docker-compose` setup to launch Kedro next to a monitoring stack
* To add deployment scripts and CI/CD setup for your targeted infrastructure


A Kedro starter is a [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/) template that contains the boilerplate code for a Kedro project. Each starter encodes best practices and provides utilities to bootstrap a new Kedro project for a particular use case. For example, we have created a [`PySpark` starter](https://github.com/quantumblack/kedro-starter-pyspark), which contains initial configuration and initialisation code for PySpark according to our [recommended Kedro best practices](../10_tools_integration/01_pyspark.md).

## How to use Kedro starters

To create a Kedro project using a starter, apply the `--starter` flag to `kedro new` as follows:

```bash
kedro new --starter=<path-to-starter>
```
> Note: `path-to-starter` could be a local directory or a VCS repository, as long as it is supported by [Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html).

To create a project using the `PySpark` starter:

```bash
kedro new --starter=https://github.com/quantumblacklabs/kedro-starter-pyspark.git
```

If no starter is provided to `kedro new`, the default Kedro template will be used, as documented in [Creating a new project](./03_new_project.md).

### Starter aliases

We provide aliases for common starters maintained by Kedro team so that users don't have to specify the full path. For example, to create a project using the `PySpark` starter:

```bash
kedro new --starter=pyspark
```

To list all the aliases we support:

```bash
kedro starter list
```

## List of official starters

The Kedro team maintains the following starters:

* [Alias `pandas-iris`](https://github.com/quantumblacklabs/kedro-starter-pandas-iris): An example iris dataset classification pipeline built with Kedro
* [Alias `pyspark`](https://github.com/quantumblacklabs/kedro-starter-pyspark): The configuration and initialisation code for a [Kedro pipeline using PySpark](../10_tools_integration/01_pyspark.md)
* [Alias `pyspark-iris`](https://github.com/quantumblacklabs/kedro-starter-pyspark-iris): An example iris dataset classification pipeline built with [Kedro and PySpark](../10_tools_integration/01_pyspark.md)
## Starter versioning

By default, Kedro will use the latest version available in the repository, but if you want to use a specific version of a starter, you can pass a `--checkout` argument to the command as follows:

```bash
kedro new --starter=pyspark --checkout=0.1.0
```

The `--checkout` value points to a branch, tag or commit in the starter repository.

Under the hood, the value will be passed to the [`--checkout` flag in Cookiecutter](https://cookiecutter.readthedocs.io/en/1.7.2/usage.html#works-directly-with-git-and-hg-mercurial-repos-too).

## Use a starter in interactive mode

By default, when you create a new project using a starter, `kedro new` launches in [interactive mode](./03_new_project.md#Create-a-new-project-interactively). You will be prompted to provide the following variables:

* `project_name` - A human readable name for your new project
* `repo_name` - A name for the directory that holds your project repository
* `python_package` - A Python package name for your project package (see [Python package naming conventions](https://www.python.org/dev/peps/pep-0008/#package-and-module-names))

This mode assumes that the starter doesn't require any additional configuration variables.

## Use a starter with a configuration file

Kedro also allows you to [specify a configuration file](./03_new_project.md#Create-a-new-project-from-a-configuration-file) to create a project. Use the `--config` flag alongside the starter as follows:

```bash
kedro new --config=my_kedro_pyspark_project.yml --starter=pyspark
```

This option is useful when the starter requires more configuration than is required by the interactive mode.
