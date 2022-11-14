# Install Kedro

## Installation prerequisites

Kedro supports macOS, Linux and Windows. If you encounter any problems on these platforms, please check the [frequently asked questions](../faq/faq.md), the [searchable archive from our retired Discord server](https://linen-discord.kedro.org) or post a new query on the [Slack organisation](https://join.slack.com/t/kedro-org/shared_invite/zt-1eicp0iw6-nkBvDlfAYb1AUJV7DgBIvw).

If you are a Windows user, you will need to install [`git`](https://git-scm.com/) onto your machine if you do not have it. To confirm whether you have it installed:

```bash
git -v
```

You should see the version of `git` available, or an error message to indicate that it is not installed.

PySpark users must [install Java](https://www.oracle.com/java/technologies/javase-downloads.html) (if you are working on Windows, you will need admin rights to complete the installation).

### Virtual environments
We recommend that you create a new Python virtual environment for *each* new Kedro project you create. A virtual environment creates an isolated environment for a Python project to have its own dependencies, regardless of other projects.

If you don't already have it, you should [download and install Anaconda](https://www.anaconda.com/products/individual#Downloads) (Python 3.x version), which comes bundled with a package and environment manager called `conda`.

> [Read more about Python virtual environments](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).


Depending on your preferred Python installation, you can also create virtual environments to work with Kedro using `venv` or `pipenv` instead of `conda`. Further information about these can be found in the [FAQ](../faq/faq.md)

#### Create a virtual environment with `conda`

1. [Install `conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) on your computer.

2. Create a new Python virtual environment, called `kedro-environment`, using `conda`. In the example below, we use Python 3.10 but you can opt for a different version if you need it for your particular project:

```bash
conda create --name kedro-environment python=3.10 -y
```

This will create an isolated Python 3.8 environment.

3. Activate the new environment:

```bash
conda activate kedro-environment
```

4. To exit `kedro-environment`:

```bash
conda deactivate
```

```{note}
The `conda` virtual environment is not dependent on your current working directory and can be activated from any directory.
```
## Install Kedro using `pip`

To install Kedro from the Python Package Index (PyPI), simply run:

```bash
pip install kedro
```

```{note}
It is also possible to install Kedro using `conda install -c conda-forge kedro` but we recommend you use `pip` at this point to eliminate any potential dependency issues:
```

Both `pip` and `conda` install the core Kedro module, which includes the CLI tool, project template, pipeline abstraction, framework, and support for configuration.

## Verify a successful installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number: for example,

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, see the [frequently asked questions](../faq/faq.md), check out the [searchable archive from our retired Discord server](https://linen-discord.kedro.org) or post a new query on the [Slack organisation](https://join.slack.com/t/kedro-org/shared_invite/zt-1eicp0iw6-nkBvDlfAYb1AUJV7DgBIvw).

## Install a development version

To try out a development version of Kedro direct from the [Kedro Github repository](https://github.com/kedro-org/kedro), follow [these steps](../faq/faq.md#how-can-i-use-a-development-version-of-kedro).
