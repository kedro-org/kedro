# Set up Kedro

## Summary

* Kedro can be used on Windows, macOS or Linux.
* Installation prerequisites include Python 3.7+, a virtual environment manager like `conda`, and `git`.
* You should install Kedro using `pip install kedro`.

If you encounter any problems as you set up Kedro, you can ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or [search the archives for a solution](https://linen-discord.kedro.org).


## Installation prerequisites
* **Python**: Kedro supports macOS, Linux, and Windows and is built for Python 3.7+. You'll select a version of Python when you create a virtual environment for your Kedro project.

* **Python virtual environment**: We suggest you create a new Python virtual environment for *each* new Kedro project you work on to isolate its dependencies from those of other projects.

* **git**: You must install `git` onto your machine if you do not already have it. Type `git -v` into your terminal window to confirm it is installed. You should see the version of `git` available or an error message. You can download it from the official  [`git`](https://git-scm.com/) website.

## Create a Python virtual environment for your Kedro project

We strongly recommend [installing `conda` as your virtual environment manager](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) if you don't already use it.

``` {tip}
[Read more about Python virtual environments](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).
```

### How to create a new virtual environment using `conda`

This is our recommended approach. From your terminal:

```bash
conda create --name kedro-environment python=3.10 -y
```

In this example, we use Python 3.10, and create a virtual environment called `kedro-environment`. You can opt for a different version of Python (any version >= 3.7 and <3.11) for your project, and name it anything you choose.

The `conda` virtual environment is not dependent on your current working directory and can be activated from any directory:

```bash
conda activate kedro-environment
```

To confirm that a valid version of Python is installed in your virtual environment, type the following in your terminal (macOS and Linux):

```bash
python3 --version
```

On Windows:

```bash
python --version
```

To exit `kedro-environment`:

```bash
conda deactivate
```

### How to create a new Python virtual environment without using `conda`

Depending on your preferred Python installation, you can create virtual environments to work with Kedro using `venv` or `pipenv` instead of `conda`.

<details>
<summary><b>Click to expand instructions for <code>venv</code></b></summary>

If you use Python 3, you should already have the `venv` module installed with the standard library. Create a directory for working with your project and navigate to it. For example:

```bash
mkdir kedro-environment && cd kedro-environment
```

Next, create a new virtual environment in this directory with `venv`:

```bash
python -m venv env/kedro-environment  # macOS / Linux
python -m venv env\kedro-environment  # Windows
```

Activate this virtual environment:

```bash
source env/kedro-environment/bin/activate # macOS / Linux
.\env\kedro-environment\Scripts\activate  # Windows
```

To exit the environment:

```bash
deactivate
```
</details>

<details>
<summary><b>Click to expand instructions for <code>pipenv</code></b></summary>

Install `pipenv` as follows:

```bash
pip install pipenv
```

Create a directory for working with your project and navigate to it. For example:

```bash
mkdir kedro-environment && cd kedro-environment
```

To start a session with the correct virtual environment activated:

```bash
pipenv shell
```

To exit the shell session:

```bash
exit
```

</details>


## Install Kedro using `pip`

To install Kedro from the Python Package Index (PyPI):

```bash
pip install kedro
```

While we recommend you to use `pip`, it is also possible to install Kedro using `conda install -c conda-forge kedro`.

## Verify your Kedro installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, check out the [searchable archive from our retired Discord server](https://linen-discord.kedro.org), or post a new query on the [Slack organisation](https://slack.kedro.org).

## How to upgrade Kedro

The best way to safely upgrade is to check our [release notes](https://github.com/kedro-org/kedro/blob/main/RELEASE.md) for any notable breaking changes. Follow the steps in the migration guide included for that specific release.

Once Kedro is installed, you can check your version as follows:

```bash
kedro --version
```

To later upgrade Kedro to a different version, simply run:

```bash
pip install kedro -U
```

When migrating an existing project to a newer Kedro version, make sure you also update the `project_version`:

* For projects generated with versions of Kedro > 0.17.0, you'll do this in the `pyproject.toml` file from the project root directory.
* If your project was generated with a version of Kedro <0.17.0, you will instead need to update the `ProjectContext`, which is found in `src/<package_name>/run.py`.


## How to install a development version of Kedro

This section explains how to try out a development version of Kedro direct from the [Kedro GitHub repository](https://github.com/kedro-org/kedro).

```{important}
The development version of Kedro is not guaranteed to be bug-free and/or compatible with any of the [stable versions](https://pypi.org/project/kedro/#history). We do not recommend that you use a development version of Kedro in any production systems. Please install and use with caution.
```

To try out latest, unreleased functionality from the `develop` branch of the Kedro GitHub repository, run the following installation command:

```bash
pip install git+https://github.com/kedro-org/kedro.git@develop
```

This will install Kedro from the `develop` branch of the GitHub repository, which is always the most up to date. This command will install Kedro from source, unlike `pip install kedro` which installs Kedro from PyPI.

If you want to roll back to a stable version of Kedro, execute the following in your environment:

```bash
pip uninstall kedro -y
pip install kedro
```
