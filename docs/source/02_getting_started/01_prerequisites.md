# Installation prerequisites

Kedro supports macOS, Linux and Windows (7 / 8 / 10 and Windows Server 2016+). If you encounter any problems on these platforms, please check the [FAQ](../06_resources/01_faq.md), and / or the Kedro community support on [Stack Overflow](https://stackoverflow.com/questions/tagged/kedro).

### macOS / Linux

In order to work effectively with Kedro projects, we highly recommend you download and install [Anaconda](https://www.anaconda.com/download/#macos) (Python 3.x version) and [Java](https://www.oracle.com/technetwork/java/javase/downloads/index.html) (if using PySpark).


### Windows

You will require admin rights to complete the installation of the following tools on your machine:

* [Anaconda](https://www.anaconda.com/download/#windows) (Python 3.x version)
* [Java](https://www.oracle.com/technetwork/java/javase/downloads/index.html) (if using PySpark)

## Python virtual environments

Python's virtual environments can be used to isolate the dependencies of different individual projects, avoiding Python version conflicts. They also prevent permission issues for non-administrator users.
For more information, please refer to this [guide](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html).

### Using `conda`

We recommend creating your virtual environment using [`conda`](https://conda.io/docs/), a package and environment manager program bundled with Anaconda.

#### Create an environment with `conda`

Use [`conda create`](https://conda.io/docs/user-guide/tasks/manage-environments.html#id1) to create a python 3.6  environment called `environment_name` by running:

```bash
conda create --name environment_name python=3.6
```

#### Activate an environment with `conda`

Use [`conda activate`](https://conda.io/docs/user-guide/tasks/manage-environments.html#activating-an-environment) to activate an environment called `environment_name` by running:

```bash
conda activate environment_name
```

When you want to deactivate the environment you are using with Kedro, you can use [`conda deactivate`](https://conda.io/docs/user-guide/tasks/manage-environments.html#id6):

```bash
conda deactivate
```

#### Other `conda` commands

To list all existing `conda` environments:

```bash
conda env list
```

To delete an environment:

```bash
conda remove --name environment_name --all
```

### Alternatives to `conda`

If you prefer an alternative environment manager such as [`venv`](https://docs.python.org/3/library/venv.html), [`pyenv`](https://github.com/pyenv/pyenv), etc, please read their respective documentation.
