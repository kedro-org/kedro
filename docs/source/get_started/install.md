# Set up Kedro

## Summary

* Kedro can be used on Windows, macOS or Linux
* Installation prerequisites include Python 3.7+, a virtual environment manager like `conda` and `git`
* You should install Kedro using `pip install kedro`

If you encounter any problems as you install Kedro, you can ask for help on Kedro's [Slack organisation](https://slack.kedro.org) or [search the archives for a solution](https://linen-discord.kedro.org).


## Installation prerequisites
* **Python**: Kedro supports macOS, Linux, and Windows and is built for Python 3.7+. You'll select a version of Python when you create a virtual environment for your Kedro project.

* **Python virtual environment**: We suggest you create a new Python virtual environment for *each* new Kedro project you work on to isolate its dependencies from those of other projects.

* **git**: You will need to install `git` onto your machine if you do not already have it. To confirm it is installed, type `git -v` into your terminal window. You should see the version of `git` available or an error message. You can download it from the official  [`git`](https://git-scm.com/) website.

## Create a Python virtual environment for your Kedro project

We strongly recommend [installing `conda` as your virtual environment manager](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) if you don't already use it.

``` {note}
[Read more about Python virtual environments](https://realpython.com/python-virtual-environments-a-primer/) or [watch an explainer video about them](https://youtu.be/YKfAwIItO7M).
```

To create a new virtual environment called `kedro-environment` using `conda`:

```bash
conda create --name kedro-environment python=3.10 -y
```

In this example, we use Python 3.10, but you can opt for a different version if you need it for your particular project.

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

### Create a new Python virtual environment without using `conda`

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

```{note}
While we recommend you to use `pip`, it is also possible to install Kedro using `conda install -c conda-forge kedro`.
```

## Verify your Kedro installation

To check that Kedro is installed:

```bash
kedro info
```

You should see an ASCII art graphic and the Kedro version number: for example,

![](../meta/images/kedro_graphic.png)

If you do not see the graphic displayed, or have any issues with your installation, check out the [searchable archive from our retired Discord server](https://linen-discord.kedro.org), or post a new query on the [Slack organisation](https://slack.kedro.org).

## Install a development version

To try out a development version of Kedro direct from the [Kedro GitHub repository](https://github.com/kedro-org/kedro), follow [these steps](../faq/faq.md#how-can-i-use-a-development-version-of-kedro).
