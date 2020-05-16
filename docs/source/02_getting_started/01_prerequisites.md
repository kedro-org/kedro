# Installation prerequisites

Kedro supports macOS, Linux and Windows (7 / 8 / 10 and Windows Server 2016+). If you encounter any problems on these platforms, please check the [FAQ](../06_resources/01_faq.md), and / or the Kedro community support on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

### macOS / Linux

In order to work effectively with Kedro projects, we highly recommend you download and install [Anaconda](https://www.anaconda.com/download/#macos) (Python 3.x version) and [Java](https://www.oracle.com/technetwork/java/javase/downloads/index.html) (if using PySpark).

## Working with virtual environments

> The main purpose of Python virtual environments is to create an isolated environment for Python projects. This means that each project can have its own dependencies, regardless of what dependencies every other project has. Read more about Python Virtual Environments [here](https://realpython.com/python-virtual-environments-a-primer/).

Follow the instructions that best suit your Python installation preference from below:

 - `conda` environment with Python 3.7
 - `venv` or `pipenv` used when you prefer not to use `conda` and instead use your global Python interpreter.

### `conda`

Follow [this guide](https://docs.conda.io/projects/conda/en/latest/user-guide/install/) to install `conda` on your computer. Once it's done, you can create a new Python virtual environment using `conda`:

```bash
conda create --name kedro-environment python=3.7 -y
```

This will create an isolated Python 3.7 environment. To activate it:

```bash
conda activate kedro-environment
```

To exit the environment:

```bash
conda deactivate kedro-environment
```

> *Note:* Unlike `venv` or `pipenv`, `conda` virtual environment is not dependent on your current working directory and can be activated from anywhere.

### `venv` (instead of `conda`)

If you are using Python 3, then you should already have the `venv` module installed with the standard library. However, for completeness you can install `venv`:

```bash
pip install virtualenv
```

Create a directory for your virtual environment:

```bash
mkdir kedro-environment && cd kedro-environment
```

This will create a `kedro-environment` directory in your current working directory. Then you should create a new virtual environment in this directory by running:

```bash
python -m venv env/kedro-environment  # macOS / Linux
python -m venv env\kedro-environment  # Windows
```

We can activate this virtual environment with:

```bash
source env/bin/activate # macOS / Linux
.\env\Scripts\activate  # Windows
```

To exit the environment:

```bash
deactivate
```

### `pipenv` (instead of `conda`)

You will need to install `pipenv` with:

```bash
pip install pipenv
```

Then create a directory for the virtual environment and change to this working directory:

```bash
mkdir kedro-environment && cd kedro-environment
```

Once all the dependencies are installed you can run `pipenv shell` which will start a session with the correct virtual environment activated.

To exit the shell session:

```bash
exit
```
