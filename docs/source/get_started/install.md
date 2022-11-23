# Install Kedro

If you encounter any problems as you install Kedro, you can ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or [search the archives for a solution](https://linen-discord.kedro.org).


## Installation prerequisites

### Python
Kedro supports macOS, Linux, and Windows and is built for Python 3.7+.

To confirm that Python is installed, type the following in your terminal (macOS and Linux) or command prompt (Windows):

```bash
python
```

You should see the version of Python installed on your machine:

```python
Python 3.8.13 (default, Mar 28 2022, 06:13:39)
[Clang 12.0.0 ] :: Anaconda, Inc. on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```
Type `exit()` to return to the terminal prompt.

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

Depending on your preferred Python installation, you can alternatively create virtual environments to work with Kedro using `venv` or `pipenv` instead of `conda`, as described in the [FAQ](../faq/faq.md)

#### Create a new Python virtual environment using `conda`

To create a new virtual environment, called `kedro-environment` using `conda`. In this example, we use Python 3.10, but you can opt for a different version if you need it for your particular project.:

```bash
conda create --name kedro-environment python=3.10 -y
```

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

If you do not see the graphic displayed, or have any issues with your installation, see the [frequently asked questions](../faq/faq.md), check out the [searchable archive from our retired Discord server](https://linen-discord.kedro.org), or post a new query on the [Slack organisation](https://slack.kedro.org).

## Install a development version

To try out a development version of Kedro direct from the [Kedro GitHub repository](https://github.com/kedro-org/kedro), follow [these steps](../faq/faq.md#how-can-i-use-a-development-version-of-kedro).
