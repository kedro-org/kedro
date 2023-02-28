# Install Kedro

If you encounter any problems as you install Kedro, you can ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or [search the archives for a solution](https://linen-discord.kedro.org).


## Installation prerequisites

### Python
Kedro supports macOS, Linux, and Windows and is built for Python 3.7+.

To confirm that a valid version of Python is installed, type the following in your terminal (macOS and Linux):

```bash
python3 --version
```
On Windows, type the following into the command prompt:

```bash
python --version
```

You should see the version of Python installed on your machine:

```bash
Python 3.8.13
```

If you see an error message or need to install a later version of Python, you can download it from the [official Python website](https://www.python.org/downloads/).

### `git`
You will need to install `git` onto your machine if you do not already have it. To check if it is installed:

```bash
git -v
```

You should see the version of `git` available or an error message if it is not installed. You can download it from the official  [`git`](https://git-scm.com/) website.

### Virtual environment manager
We suggest you create a new Python virtual environment for *each* new Kedro project you work on to isolate its dependencies from those of other projects. We strongly recommend [installing `conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) if you don't already use it.

``` {note}
[Read more about Python virtual environments](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).
```

```{note}
Depending on your preferred Python installation, you can alternatively create virtual environments to work with Kedro using `venv` or `pipenv` instead of `conda`.
```

#### Create a new Python virtual environment using `conda`

To create a new virtual environment called `kedro-environment` using `conda`:

```bash
conda create --name kedro-environment python=3.10 -y
```

In this example, we use Python 3.10, but you can opt for a different version if you need it for your particular project.

To activate the new environment:

```bash
conda activate kedro-environment
```

```{note}
The `conda` virtual environment is not dependent on your current working directory and can be activated from any directory.
```

To exit `kedro-environment`:

```bash
conda deactivate
```

## Install Kedro using `pip` or `conda`

To install Kedro from the Python Package Index (PyPI):

```bash
pip install kedro
```

```{note}
It is also possible to install Kedro using `conda install -c conda-forge kedro`, but we recommend you use `pip` at this point to eliminate any potential dependency issues:
```

### Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number: for example,

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [searchable archive of past community support discussions](https://linen-discord.kedro.org), or post a new query on [Kedro's Slack organisation](https://slack.kedro.org).

### How do I upgrade Kedro?

We use [Semantic Versioning](https://semver.org/). The best way to safely upgrade is to check our [release notes](https://github.com/kedro-org/kedro/blob/main/RELEASE.md) for any notable breaking changes. Follow the steps in the migration guide included for that specific release.

Once Kedro is installed, you can check your version as follows:

```
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```
pip install kedro -U
```

When migrating an existing project to a newer Kedro version, make sure you also update the `project_version` in your `pyproject.toml` file from the project root directory or, for projects generated with Kedro<0.17.0, in your `ProjectContext`, which is found in `src/<package_name>/run.py`.


## Install a development version of Kedro

This section explains how to try out a development version of Kedro direct from the [Kedro GitHub repository](https://github.com/kedro-org/kedro).

```{important}
The development version of Kedro is not guaranteed to be bug-free and/or compatible with any of the [stable versions](https://pypi.org/project/kedro/#history). We do not recommend that you use a development version of Kedro in any production systems. Please install and use with caution.
```

To try out latest, unreleased functionality, run the following installation command:

```console
pip install git+https://github.com/kedro-org/kedro.git@develop
```

This will install Kedro from the `develop` branch of the GitHub repository, which is always the most up to date. This command will install Kedro from source, unlike `pip install kedro` which installs Kedro from PyPI.

If you want to roll back to a stable version of Kedro, execute the following in your environment:

```console
pip uninstall kedro -y
pip install kedro
```
