# Use databricks asset bundles and jobs to deploy a Kedro project

Databricks jobs are a way to execute code on Databricks clusters, allowing you to run data processing tasks, ETL jobs, or machine learning workflows. In this guide, we explain how to package and run a Kedro project as a job on Databricks.



## Prerequisites

- An active [Databricks deployment](https://docs.databricks.com/getting-started/index.html).
- [`conda` installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine to create a virtual environment with a specific version of Python (>= 3.7 is required). If you have Python >= 3.7 installed, you can use other software to create a virtual environment.

## Set up your project for deployment to Databricks

The sequence of steps described in this section is as follows:

1. [Note your Databricks username and host](#note-your-databricks-username-and-host)
2. [Install Kedro and the Databricks CLI in a new virtual environment](#install-kedro-and-the-databricks-cli-in-a-new-virtual-environment)
3. [Authenticate the Databricks CLI](#authenticate-the-databricks-cli)
4. [Create a new Kedro project](#create-a-new-kedro-project)
5. [Create an entry point for Databricks](#create-an-entry-point-for-databricks)
6. [Create Asset bundles files](#create-asset-bundles-files)
7. [Upload project data to DBFS](#upload-project-data-to-dbfs)

### Note your Databricks username and host

Note your Databricks **username** and **host** as you will need it for the remainder of this guide.

Find your Databricks username in the top right of the workspace UI and the host in the browser's URL bar, up to the first slash (e.g., `https://adb-123456789123456.1.azuredatabricks.net/`):

![Find Databricks host and username](../../meta/images/find_databricks_host_and_username.png)

```{note}
Your Databricks host must include the protocol (`https://`).
```

### Install Kedro and the Databricks CLI in a new virtual environment

The following commands will create a new `conda` environment, activate it, and then install Kedro and the Databricks CLI.

In your local development environment, create a virtual environment for this tutorial using `conda`:

```bash
conda create --name databricks-iris python=3.10
```

Once it is created, activate it:

```bash
conda activate databricks-iris
```

With your `conda` environment activated, install Kedro:

```bash
pip install kedro
```

Install databricks CLI depending on your system [Databricks CLI](https://docs.databricks.com/en/dev-tools/cli/install.html):

### Authenticate the Databricks CLI

**Now, you must authenticate the Databricks CLI with your Databricks instance.**

[Refer to the Databricks documentation](https://docs.databricks.com/en/dev-tools/cli/authentication.html) for a complete guide on how to authenticate your CLI. The key steps are:

1. Create a personal access token for your user on your Databricks instance.
2. Run `databricks configure --token`.
3. Enter your token and Databricks host when prompted.
4. Run `databricks fs ls dbfs:/` at the command line to verify your authentication.

### Create a new Kedro project

Create a Kedro project by using the following command in your local environment:

```bash
kedro new --starter=databricks-iris
```

This command creates a new Kedro project using the `databricks-iris` starter template. Name your new project `databricks-iris` for consistency with the rest of this guide.

 ```{note}
 If you are not using the `databricks-iris` starter to create a Kedro project, **and** you are working with a version of Kedro **earlier than 0.19.0**, then you should [disable file-based logging](https://docs.kedro.org/en/0.18.14/logging/logging.html#disable-file-based-logging) to prevent Kedro from attempting to write to the read-only file system.
 ```

create a file `.telemetry` in the root
 ```yaml
consent: false
 ```
### Create an entry point for Databricks

The default entry point of a Kedro project uses a Click command line interface (CLI), which is not compatible with Databricks. To run your project as a Databricks job, you must define a new entry point specifically for use on Databricks.

The `databricks-iris` starter has this entry point pre-built, so there is no extra work to do here, but generally you must **create an entry point manually for your own projects using the following steps**:

1. **Create an entry point script**: Create a new file in `<project_root>/src/databricks_iris` named `databricks_run.py`. Copy the following code to this file:

```python
import argparse
import logging

from kedro.framework.project import configure_project
from kedro.framework.session import KedroSession


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", dest="env", type=str)
    parser.add_argument("--conf-source", dest="conf_source", type=str)
    parser.add_argument("--package-name", dest="package_name", type=str)

    args = parser.parse_args()
    env = args.env
    conf_source = args.conf_source
    package_name = args.package_name

    # https://kb.databricks.com/notebooks/cmd-c-on-object-id-p0.html
    logging.getLogger("py4j.java_gateway").setLevel(logging.ERROR)
    logging.getLogger("py4j.py4j.clientserver").setLevel(logging.ERROR)

    configure_project(package_name)
    with KedroSession.create(env=env, conf_source=conf_source) as session:
        session.run()


if __name__ == "__main__":
    main()
```

2. **Define a new entry point**: Open `<project_root>/pyproject.toml` in a text editor or IDE and add a new line in the `[project.scripts]` section, so that it becomes:

```python
[project.scripts]
databricks_run = "<package_name>.databricks_run:main"
```

Remember to replace <package_name> with the correct package name for your project.

This process adds an entry point to your project which can be used to run it on Databricks.

```{note}
Because you are no longer using the default entry-point for Kedro, you will not be able to run your project with the options it usually provides. Instead, the `databricks_run` entry point in the above code and in the `databricks-iris` starter contains a simple implementation of two options:
- `--package_name` (required): the package name (defined in `pyproject.toml`) of your packaged project.
- `--env`: specifies a [Kedro configuration environment](../../configuration/configuration_basics.md#configuration-environments) to load for your run.
- `--conf-source`: specifies the location of the `conf/` directory to use with your Kedro project.
```




### Upload project data to DBFS

```{note}
A Kedro project's configuration and data do not get included when it is packaged. They must be stored somewhere accessible to allow your packaged project to run.
```

Your packaged Kedro project needs access to data and configuration to run. Therefore, you will need to upload your project's data  to a location accessible to Databricks. In this guide, we will store the data on the Databricks File System (DBFS).

The `databricks-iris` starter contains a [catalog](../../data/data_catalog.md) that is set up to access data stored in DBFS (`<project_root>/conf/`). You will point your project to use configuration stored on DBFS using the `--conf-source` option when you create your job on Databricks.

There are several ways to upload data to DBFS: you can use the [DBFS API](https://learn.microsoft.com/en-us/azure/databricks/dev-tools/api/latest/dbfs), the [`dbutils` module](https://docs.databricks.com/dev-tools/databricks-utils.html) in a Databricks notebook or the [Databricks CLI](https://docs.databricks.com/archive/dev-tools/cli/dbfs-cli.html). In this guide, it is recommended to use the Databricks CLI because of the convenience it offers.

- **Upload your project's data**: at the command line in your local environment, use the following Databricks CLI commands to upload your project's locally stored data and configuration to DBFS:

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

### Create asset bundles files



#### 1. Create the bundle

Create a folder called `assets` in the root directory containing the file `batch-inference-workflow-asset.yml`, this name is just an example:
```yaml
common_permissions: &permissions
  permissions:
    - level: CAN_VIEW
      group_name: users

experimental:
  python_wheel_wrapper: true

artifacts:
  default:
    type: whl
    build: kedro package
    path: ..
resources:
  jobs:
    iris-databricks-job: #used to run job from CLI
      name: "iris-databricks"
      tasks:
        - task_key: kedro_run
          existing_cluster_id: ${var.existing_cluster_id}
          python_wheel_task:
            package_name: databricks_iris
            entry_point: databricks_run
            named_parameters:
              --conf-source: /Workspace${workspace.file_path}/conf
              --package-name: databricks_iris
              --env: ${var.environment}
          libraries:
            - whl: ../dist/*.whl
      schedule:
        quartz_cron_expression: "0 0 11 * * ?" # daily at 11am
        timezone_id: UTC
      <<: *permissions
```
This file provides a template for a job utilizing Kedro as a package, and it allows for multiple definitions per job. For instance, you could have one definition per pipeline.

#### 2. Create the bundle’s configuration file


Create the file `databricks.yml` in the root directory

```yaml
bundle:
  name: databricks_iris

variables:
  existing_cluster_id:
    description: The ID of an existing cluster for development
    default: replace_your_cluster_id
  environment:
    description: The environment to run the job in
    default: dev

include:
  - assets/*.yml

# Deployment Target specific values for workspace
targets:
  dev:
    default: true
    mode: development
    workspace:
      host: replace_your_host
    run_as:
      user_name: your_user@mail.com
    variables:
      environment: base

  prod:
    mode: production
    workspace:
      host: replace_your_host
    run_as:
      # This runs as your_user@mail.com in production. We could also use a service principal here
      # using service_principal_name (see https://docs.databricks.com/dev-tools/bundles/permissions.html).
      user_name: your_user@mail.com
```
### Deploy and run the job

You can deploy to remote workspace with following command:
```bash
databricks bundle deploy -t dev
```

This will:
1. Create the wheel of your kedro project: `databricks_iris-0.1-py3-none-any.whl`
2. Create a notebook containing the code to be used by a job to execute the kedro project. You can see it in `<project_root>/.databricks/bundle/dev/.internal/notebook_iris-databricks-job_kedro_run.py`
3. Upload the wheel to `/Workspace/Users/your_user/.bundle/databricks_iris/dev/artifacts/.internal/`
4. Upload all the files of the root directory to `/Workspace/Users/your_user/.bundle/databricks_iris/dev/files` including `conf`
5. Create the job using the notebook from 2.

You can execute now the project with
```bash
databricks bundle run -t dev databricks_iris
```
and you can destroy all resources with:

```bash
databricks bundle destroy --auto-approve -t dev --force-lock
```
