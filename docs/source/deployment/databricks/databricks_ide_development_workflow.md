# Use Databricks Connect to develop a Kedro project

This guide demonstrates a workflow for developing Kedro projects on Databricks using your local environment for development, then using Databricks Connect testing on Databricks.

By working in your local environment, you can take advantage of features within an IDE that are not available on Databricks notebooks:

- Auto-completion and suggestions for code, improving your development speed and accuracy.
- Linters like [Ruff](https://docs.astral.sh/ruff) can be integrated to catch potential issues in your code.
- Static type checkers like Mypy can check types in your code, helping to identify potential type-related issues early in the development process.

To set up these features, look for instructions specific to your IDE (for instance, [VS Code](https://code.visualstudio.com/docs/python/linting)).

If you prefer to develop a projects in notebooks rather than an in an IDE, you should follow our guide on [how to develop a Kedro project within a Databricks workspace](./databricks_notebooks_development_workflow.md) instead.

## What this page covers

The main steps in this tutorial are as follows:

- [Install Kedro and the Databricks CLI in a new virtual environment.](#install-kedro-and-databricks-cli-in-a-new-virtual-environment)
- [Create a new Kedro project using the `databricks-iris` starter.](#create-a-new-kedro-project)
- [Upload project data to a location accessible by Kedro when run on Databricks (such as DBFS).](#upload-project-data-to-dbfs)
- [Modify spark hook to allow remote.](#modify-spark-hook)
- [Modify your project in your local environment and test the changes on Databricks in an iterative loop.](#modify-your-project-and-test-the-changes)

## Prerequisites

- An active [Databricks deployment](https://docs.databricks.com/getting-started/index.html).
- A [Databricks cluster](https://docs.databricks.com/clusters/configure.html) configured with a recent version (>= 14 is recommended) of the Databricks runtime.
- [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine in order to create a virtual environment with a specific version of Python (>= 3.10 is required). If you have Python >= 3.8 installed, you can use other software to create a virtual environment.

## Set up your project

### Note your Databricks username and host

Note your Databricks **username** and **host** as you will need it for the remainder of this guide.

Find your Databricks username in the top right of the workspace UI and the host in the browser's URL bar, up to the first slash (e.g., `https://adb-123456789123456.1.azuredatabricks.net/`):

![Find Databricks host and username](../../meta/images/find_databricks_host_and_username.png)

```{note}
Your databricks host must include the protocol (`https://`).
```

### Install Kedro and Databricks CLI in a new virtual environment

In your local development environment, create a virtual environment for this tutorial using Conda:

```bash
conda create --name databricks-iris python=3.10
```

Once it is created, activate it:

```bash
conda activate databricks-iris
```

With your `conda` environment activated, install Kedro and databricks connect:

```bash
pip install kedro
pip install --upgrade "databricks-connect==14.3*"  # Or X.Y.* to match your cluster version.
```

Install databricks CLI depending on your system [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/install.html):

### Authenticate the Databricks CLI

**Now, you must authenticate the Databricks CLI with your Databricks instance.**

[Refer to the Databricks documentation](https://docs.databricks.com/en/dev-tools/cli/authentication.html) for a complete guide on how to authenticate your CLI. The key steps are:

1. Create a personal access token for your user on your Databricks instance.
2. Run `databricks configure --token --configure-cluster`.
3. Enter your token and Databricks host when prompted and the cluster_id to execute the code
4. Run `databricks fs ls dbfs:/` at the command line to verify your authentication.
5. Run `databricks-connect test` to verify remote cluster

### Create a new Kedro project

Create a Kedro project with the `databricks-iris` starter using the following command in your local environment:

```bash
kedro new --starter=databricks-iris
```

Name your new project `databricks-iris` for consistency with the rest of this guide. This command creates a new Kedro project using the `databricks-iris` starter template.



### Upload project data to DBFS

When run on Databricks, Kedro cannot access data stored in your project's directory. Therefore, you will need to upload your project's data to an accessible location. In this guide, we will store the data on the Databricks File System (DBFS).

The `databricks-iris` starter contains a [catalog](../../data/data_catalog.md) that is set up to access data stored in DBFS (`<project_root>/conf/`). You will point your project to use configuration stored on DBFS using the `--conf-source` option when you create your job on Databricks.

There are several ways to upload data to DBFS. In this guide, it is recommended to use [Databricks CLI](https://docs.databricks.com/archive/dev-tools/cli/dbfs-cli.html) because of the convenience it offers. At the command line in your local environment, use the following Databricks CLI command to upload your locally stored data to DBFS:

```bash
databricks fs cp --recursive <project_root>/data/ dbfs:/FileStore/iris-databricks/data
```

The `--recursive` flag ensures that the entire folder and its contents are uploaded. You can list the contents of the destination folder in DBFS using the following command:

```bash
databricks fs ls dbfs:/FileStore/iris-databricks/data
```

You should see the contents of the project's `data/` directory printed to your terminal:

```bash
01_raw
02_intermediate
03_primary
04_feature
05_model_input
06_models
07_model_output
08_reporting
```

## Modify spark hook
To enable remote execution let's modify `src/databricks_iris/hooks.py`. For more details please review [How to integrate Databricks Connect and Kedro](https://kedro.org/blog/how-to-integrate-kedro-and-databricks-connect)

```python
import configparser
import os
from pathlib import Path

from kedro.framework.hooks import hook_impl
from pyspark.sql import SparkSession

class SparkHooks:
    @hook_impl
    def after_context_created(self) -> None:
        """Initialises a SparkSession using the config
        from Databricks.
        """
        set_databricks_creds()
        _spark_session = SparkSession.Builder().getOrCreate()

def set_databricks_creds():
    """
    Pass databricks credentials as OS variables if using the local machine.
    If you set DATABRICKS_PROFILE env variable, it will choose the desired profile on .databrickscfg,
    otherwise it will use the DEFAULT profile in databrickscfg.
    """
    DEFAULT = os.getenv("DATABRICKS_PROFILE", "DEFAULT")
    if os.getenv("SPARK_HOME") != "/databricks/spark":
        config = configparser.ConfigParser()
        config.read(Path.home() / ".databrickscfg")

        host = (
            config[DEFAULT]["host"].split("//", 1)[1].strip()[:-1]
        )  # remove "https://" and final "/" from path
        cluster_id = config[DEFAULT]["cluster_id"]
        token = config[DEFAULT]["token"]
        os.environ[
            "SPARK_REMOTE"
        ] = f"sc://{host}:443/;token={token};x-databricks-cluster-id={cluster_id}"
```
## Run the project
Now you can run the project in the remote environment with

```bash
kedro run
```
## Modify your project and test the changes

Now that your project has run successfully once, you can make changes using the convenience and power of your local development environment. In this section, you will modify the project to use a different ratio of training data to test data and check the effect of this change on Databricks.

### Modify the training / test split ratio

The `databricks-iris` starter uses a default 80-20 ratio of training data to test data when training the classifier. In this section, you will change this ratio to 70-30 by editing your project in your local environment and then run the modified project on Databricks to observe the different result.

Open the file `<project_root>/conf/base/parameters.yml` in your local environment. Edit the line `train_fraction: 0.8` to `train_fraction: 0.7` and save your changes.
### Re-run your project

```bash
kedro run
```

## Summary

This guide demonstrated a development workflow on Databricks, using your local development environment and Databricks Connect. This approach improves development efficiency and provides access to powerful development features, such as auto-completion, linting, and static type checking, that are not available when working exclusively with Databricks notebooks.
