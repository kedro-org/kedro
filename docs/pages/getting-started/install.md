# Set up Kedro

## Installation prerequisites
* **Python**: Kedro works on macOS, Linux, and Windows and requires Python 3.9+. You should create a new virtual environment for *each* new Kedro project you work on to isolate its Python dependencies from those of other projects.

* **git**: You must install `git` onto your machine if you do not already have it. Type `git -v` into your terminal window to confirm it is installed; it will return the version of `git` available or an error message. [You can download `git` from the official website](https://git-scm.com/).

## Python version support policy
* The core [Kedro Framework](https://github.com/kedro-org/kedro) supports all Python versions that are actively maintained by the CPython core team. When a [Python version reaches end of life](https://devguide.python.org/versions/#versions), support for that version is dropped from Kedro. This is not considered a breaking change.
* The [Kedro Datasets](https://github.com/kedro-org/kedro-plugins/tree/main/kedro-datasets) package follows the [NEP 29](https://numpy.org/neps/nep-0029-deprecation_policy.html) Python version support policy. This means that `kedro-datasets` generally drops Python version support before `kedro`. This is because `kedro-datasets` has a lot of dependencies that follow NEP 29 and the more conservative version support approach of the Kedro Framework makes it hard to manage those dependencies properly.

## Quickstart

The simplest way to get started with Kedro is to create a new project using our [starters](../create/starters.md),
for example our Spaceflights starter.
To do that, we recommend using [`uv`](https://docs.astral.sh/uv/),
a fast, modern Python package and project manager.

First, use `uvx` to seamlessly run `kedro new`:

```bash
uvx kedro new --starter spaceflights-pandas --name spaceflights
```

The command will create a directory with the contents of your project.
Navigate to it:

```bash
cd spaceflights
```

And finally, verify that everything works:

```bash
uv run kedro run --pipeline __default__
```

## How to verify your Kedro installation

!!! note

    For the sake of brevity, the rest of the Kedro documentation assumes
    that you either run `kedro` through your project management tool,
    for example executing `uv run kedro`,
    or that the appropriate virtual environment is activated.
    If you get "command not found" errors or other unexpected results,
    double check that you are adding the prefixes required by your tooling
    or follow standard troubleshooting steps first to verify that
    the proper environment is activated.

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number. For example:

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, check out the [searchable archive of Slack discussions](https://linen-slack.kedro.org/), or post a new query on the [Slack organisation](https://slack.kedro.org).

## Alternative methods

### How to create a new Kedro project using `kedro new`

To create a new Kedro project using `kedro new` you will need Kedro installed first.
The best way to achieve this is to have a "global" installation of Kedro
that you can use only for this purpose.
There are several ways to do it:

=== "uv"

    `uvx` is an alias for `uv tool`, a uv feature that allows you to work with "tools"
    or globally-installed Python packages. After installing `uv`,
    you can use it to run `kedro new` as follows:

    ```bash
    uvx kedro new
    ```

=== "Other native tools"

    `pipx` is a tool that allows you to install and run Python applications and tools
    in isolated environments. After installing it,
    you can use it to run `kedro new` as follows:

    ```bash
    pipx run kedro new
    ```

=== "conda"

    `conda` provides package, dependency, and environment management for any language.
    Since it uses centralized environments, it is a good option for managing applications and tools.
    After installing it,
    you can use it to run `kedro new` as follows:

    ```bash
    conda create --name kedro-environment python=3.13 kedro --yes
    conda activate kedro-environment
    kedro new
    ```

### How to manually create a virtual environment for your Kedro project

There are two main types of virtual environments in Python:
native environments and conda environments.
The former are created with tools like `venv`, `virtualenv` and also `uv`,
and the latter are created with `conda`.

!!! tip
    [Read more about virtual environments for Python projects](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).

=== "uv"

    `uv` is also capable of creating virtual environments.

    First, navigate to where your project is:

    ```bash
    cd your-kedro-project
    ```

    Next, create a new virtual environment inside the `.venv` subdirectory:

    ```bash
    uv venv
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

=== "Other native tools"

    Modern versions of Python 3 include the [`venv`](https://docs.python.org/3/library/venv.html) module
    in the standard library.
    Otherwise you can install [`virtualenv`](https://pypi.org/project/virtualenv/).

    First, navigate to where your project is:

    ```bash
    cd your-kedro-project
    ```

    Next, create a new virtual environment inside the `.venv` subdirectory:

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

=== "conda"

    [Another popular option is to use Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/). After you install it, execute this from your terminal:

    ```bash
    conda create --name kedro-environment python=3.13 -y
    ```

    The example above uses Python 3.13, and creates a virtual environment called `kedro-environment`.
    Notice that conda allows you to choose your Python version,
    as well as the environment name.

    The `conda` virtual environment is not dependent on your current working directory and can be activated from any directory:

    ```bash
    conda activate kedro-environment
    ```

    To confirm that a valid version of Python is installed in your virtual environment, type the following in your terminal:

    ```bash
    python --version
    ```

    To exit `kedro-environment`:

    ```bash
    conda deactivate
    ```

### How to manually install Kedro in an environment

Depending on your environment of choice, you can install Kedro
using uv, other native tools (pip, uv, Poetry, PDM, and others),
or conda.

=== "uv"

    You can use `uv` to manually install Kedro in a native virtual environment as follows:

    ```bash
    uv pip install kedro
    ```

    Alternatively, you can add it to your project so it gets automatically declared
    in your project metadata (`pyproject.toml`) and a lock file gets generated:

    ```bash
    uv add kedro
    ```

=== "Other native tools"

    To install Kedro in a native Python environment from the Python Package Index (PyPI):

    ```bash
    pip install kedro
    ```

    You can use any modern Python packaging tool you want, such as Poetry, PDM, or Hatch:

    ```bash
    poetry add kedro
    ```

=== "conda"

    You can also install Kedro using `conda` as follows:

    ```bash
    conda install -c conda-forge kedro
    ```

### How to manually install the project dependencies in an environment

Kedro projects have a `pyproject.toml` that specifies their dependencies
and enable sharable projects by ensuring consistency across Python packages and versions.
A `requirements.txt` file is also included for compatibility with legacy workflows.

This is a sample of the dependencies found in the Spaceflights Kedro project
(you may find that the versions differ slightly depending on the version of Kedro):

```text
# code quality packages
ipython~=8.10; python_version >= '3.8'
ruff==0.1.8

# notebook tooling
jupyter~=1.0
jupyterlab_server>=2.11.1
jupyterlab~=3.0

# Pytest + useful extensions
pytest-cov~=3.0
pytest-mock>=1.7.1, <2.0
pytest~=7.2

# Kedro dependencies and datasets to work with different data formats (including CSV, Excel, and Parquet)
kedro~=0.19.0
kedro-datasets[pandas-csvdataset, pandas-exceldataset, pandas-parquetdataset]>=3.0
kedro-telemetry>=0.3.1
kedro-viz~=6.0 # Visualise pipelines

# For modeling in the data science pipeline
scikit-learn~=1.0
```

=== "uv"

    You can use `uv` to sync the environment with the project dependencies:

    ```bash
    uv sync
    ```

    Alternatively, you can use the lower level interface to install the dependencies
    directly from the `requirements.txt` file:

    ```bash
    uv pip install -r requirements.txt
    ```

=== "Other native tools"

    You can use pip or similar tools to install the dependencies
    directly from the `requirements.txt` file:

    ```bash
    pip install -r requirements.txt
    ```

=== "conda"

    !!! warning

        The official Kedro starters don't ship with `environment.yml` files
        that can be consumed by `conda`.
        Use `uv` or other native tools instead.

## Other setup steps

### How to integrate Kedro in your IDE
Working in an IDE can be a great productivity boost.

For VS Code Users: Check out [Set up Visual Studio Code](../ide/set_up_vscode.md) and [Kedro VS Code Extension](../ide/set_up_vscode.md#kedro-vs-code-extension).

For PyCharm Users: Checkout [Set up PyCharm](../ide/set_up_pycharm.md).

### How to upgrade Kedro

Kedro follows the [Semantic Versioning](https://semver.org/) paradigm.
Upgrades between bugfix or patch releases of the same minor series are expected to not require any special user action,
otherwise it's considered a bug.
Upgrades between minor releases of the 0.x series, or major releases after 1.0, can include backwards-incompatible changes
that may require some user intervention to achieve a clean upgrade.

The best way to safely upgrade when backwards-incompatible changes are expected
is to check our [release notes](https://github.com/kedro-org/kedro/blob/main/RELEASE.md).
Follow the steps in the migration guide included for that specific release.

Apart from installing the latest version (see above),
when migrating an existing project to a newer Kedro version
make sure you also update the `kedro_init_version`:

* For projects generated with versions of Kedro > 0.17.0, you'll do this in the `pyproject.toml` file from the project root directory.
* If your project was generated with a version of Kedro <0.17.0, you will instead need to update the `ProjectContext`, which is found in `src/<package_name>/run.py`.

Once Kedro is installed, you can check your version as follows:

```bash
kedro --version
```

## Summary

* Kedro can be used on Windows, macOS or Linux.
* Installation prerequisites include a Python 3.9+ and `git`.
* The simplest way to get started with Kedro is to use create a new project using our starters.
* `uv` is a great choice for managing Kedro projects, but you can use other tools such as `pip`, `Poetry`, `conda`, and more.

If you encounter any problems as you set up Kedro, ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or review the [searchable archive of Slack discussions](https://linen-slack.kedro.org/).
