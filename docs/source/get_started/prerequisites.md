# Installation prerequisites

Kedro supports macOS, Linux and Windows. If you encounter any problems on these platforms, please check the [Kedro Slack channels](https://kedro-org.slack.com).

If you are a Windows user, you will need to install [`git`](https://git-scm.com/) onto your machine if you do not have it. To confirm whether you have it installed:

```bash
git -v
```

You should see the version of `git` available, or an error message to indicate that it is not installed.

PySpark users must [install Java](https://www.oracle.com/java/technologies/javase-downloads.html) (if you are working on Windows, you will need admin rights to complete the installation).

## Virtual environments
We recommend that you create a new Python virtual environment for *each* new Kedro project you create. A virtual environment creates an isolated environment for a Python project to have its own dependencies, regardless of other projects.

If you don't already have it, you should [download and install Anaconda](https://www.anaconda.com/products/individual#Downloads) (Python 3.x version), which comes bundled with a package and environment manager called `conda`. 

> [Read more about Python Virtual Environments](https://realpython.com/python-virtual-environments-a-primer/).


Depending on your preferred Python installation, you can also create virtual environments to work with Kedro using `venv` or `pipenv` instead of `conda`. Further information about these can be found in the [FAQ](../faq/faq.md)

### Create a virtual environment with `conda`

1. [Install `conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) on your computer.

2. Create a new Python virtual environment, called `kedro-environment`, using `conda`:

```bash
conda create --name kedro-environment python=3.8 -y
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

