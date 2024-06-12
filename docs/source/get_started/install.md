# Set up Kedro

## Installation prerequisites
* **Python**: Kedro supports macOS, Linux, and Windows and is built for Python 3.8+. You'll select a version of Python when you create a virtual environment for your Kedro project.

* **Virtual environment**: You should create a new virtual environment for *each* new Kedro project you work on to isolate its Python dependencies from those of other projects.

* **git**: You must install `git` onto your machine if you do not already have it. Type `git -v` into your terminal window to confirm it is installed; it will return the version of `git` available or an error message. [You can download `git` from the official website](https://git-scm.com/).

## Python version support policy
* The core [Kedro Framework](https://github.com/kedro-org/kedro) supports all Python versions that are actively maintained by the CPython core team. When a [Python version reaches end of life](https://devguide.python.org/versions/#versions), support for that version is dropped from Kedro. This is not considered a breaking change.
* The [Kedro Datasets](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package follows the [NEP 29](https://numpy.org/neps/nep-0029-deprecation_policy.html) Python version support policy. This means that `kedro-datasets` generally drops Python version support before `kedro`. This is because `kedro-datasets` has a lot of dependencies that follow NEP 29 and the more conservative version support approach of the Kedro Framework makes it hard to manage those dependencies properly.

## Create a virtual environment for your Kedro project

We strongly recommend using `venv` as your virtual environment manager if you don't already use it.

``` {tip}
[Read more about virtual environments for Python projects](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).
```

### How to create a new virtual environment using `venv`

The recommended approach. If you use Python 3, you should already have the `venv` module installed with the standard library. Create a directory for working with your project and navigate to it. For example:

```bash
mkdir your-kedro-project && cd your-kedro-project
```

Next, create a new virtual environment in this directory with `venv`:

```bash
python -m venv .venv
```

Activate this virtual environment:

```bash
source .venv/bin/activate # macOS / Linux
.\.venv\Scripts\activate  # Windows
```

To exit the environment:

```bash
deactivate
```


### How to create a new virtual environment using `conda`

[Another popular option is to use Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/). After you install it, execute this from your terminal:

```bash
conda create --name kedro-environment python=3.10 -y
```

The example below uses Python 3.10, and creates a virtual environment called `kedro-environment`. You can opt for a different version of Python (any version >= 3.8 and <3.12) for your project, and you can name it anything you choose.

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
### Optional: Setup Kedro with IDE
Working in an IDE can be a great productivity boost.

For VS Code Users: Checkout [Set up Visual Studio Code](../development/set_up_vscode.md) and [Kedro VS Code Extension](../development/set_up_vscode.md#kedro-vscode-extension)
For PyCharm Users: Checkout [Set up PyCharm](../development/set_up_pycharm.md)

## How to install Kedro using `pip`

To install Kedro from the Python Package Index (PyPI):

```bash
pip install kedro
```

You can also install Kedro using `conda install -c conda-forge kedro`.

## How to verify your Kedro installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, check out the [searchable archive of Slack discussions](https://linen-slack.kedro.org/), or post a new query on the [Slack organisation](https://slack.kedro.org).


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

When migrating an existing project to a newer Kedro version, make sure you also update the `kedro_init_version`:

* For projects generated with versions of Kedro > 0.17.0, you'll do this in the `pyproject.toml` file from the project root directory.
* If your project was generated with a version of Kedro <0.17.0, you will instead need to update the `ProjectContext`, which is found in `src/<package_name>/run.py`.


## Summary

* Kedro can be used on Windows, macOS or Linux.
* Installation prerequisites include a virtual environment manager like `conda`, Python 3.8+, and `git`.
* You should install Kedro using `pip install kedro`.

If you encounter any problems as you set up Kedro, ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or review the [searchable archive of Slack discussions](https://linen-slack.kedro.org/).
