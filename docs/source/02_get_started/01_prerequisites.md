# Installation prerequisites

- Kedro supports macOS, Linux and Windows (7 / 8 / 10 and Windows Server 2016+). If you encounter any problems on these platforms, please check the [frequently asked questions](../11_faq/01_faq.md), and / or the Kedro community support on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

- To work with Kedro, we highly recommend that you [download and install Anaconda](https://www.anaconda.com/download/) (Python 3.x version).

- If you are using PySpark, you will also need to [install Java](https://www.oracle.com/technetwork/java/javase/downloads/index.html). If you are a Windows user, you will need admin rights to complete the installation.

## Virtual environments

The main purpose of Python virtual environments is to create an isolated environment for a Python project to have its own dependencies, regardless of other projects. We recommend that you create a new virtual environment for *each* new Kedro project you create.

> [Read more about Python Virtual Environments](https://realpython.com/python-virtual-environments-a-primer/).

Depending on your preferred Python installation, you can create virtual environments for working with Kedro as follows:

- With [`conda`](#conda), a package and environment manager program bundled with Anaconda

- Without Anaconda using [`venv`](#venv-instead-of-conda) or [`pipenv`](#pipenv-instead-of-conda)

### `conda`

[Install `conda`](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) on your computer.

Create a new Python virtual environment, called `kedro-environment`, using `conda`:

```bash
conda create --name kedro-environment python=3.7 -y
```

This will create an isolated Python 3.7 environment. To activate it:

```bash
conda activate kedro-environment
```

To exit `kedro-environment`:

```bash
conda deactivate kedro-environment
```

> *Note:* The `conda` virtual environment is not dependent on your current working directory and can be activated from any directory.

### `venv` (instead of `conda`)

If you are using Python 3, you should already have the `venv` module installed with the standard library. Create a directory for working with Kedro within your virtual environment:

```bash
mkdir kedro-environment && cd kedro-environment
```

This will create a `kedro-environment` directory in your current working directory. Then you should create a new virtual environment in this directory by running:

```bash
python -m venv env/kedro-environment  # macOS / Linux
python -m venv env\kedro-environment  # Windows
```

Activate this virtual environment:

```bash
source env/bin/activate # macOS / Linux
.\env\Scripts\activate  # Windows
```

To exit the environment:

```bash
deactivate
```

### `pipenv` (instead of `conda`)

You will need to install `pipenv` as follows:

```bash
pip install pipenv
```

Create a directory for the virtual environment and change to that directory:

```bash
mkdir kedro-environment && cd kedro-environment
```

Once all the dependencies are installed, to start a session with the correct virtual environment activated:

```bash
pipenv shell
```

To exit the shell session:

```bash
exit
```
