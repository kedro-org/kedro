# Databricks deployment workflow

In this guide, you will explore the process of packaging a Kedro project and running it as a job on Databricks. Databricks jobs are a way to execute code on Databricks clusters, allowing you to run data processing tasks, ETL jobs, or machine learning workflows.

By packaging your Kedro project and running it on Databricks, you can execute your pipeline without the need for a notebook. This approach is particularly well-suited for production, as it provides a structured and reproducible way to run your code. However, it is not ideal for development, where rapid iteration is necessary. For guidance on developing a Kedro project for Databricks, see the [development workflow guide](./databricks_development_workflow.md).

By the end of this guide, you'll have a clear understanding of the steps involved in packaging your Kedro project and running it as a job on Databricks.

## What this page covers

This page covers how to set up your project for deployment to Databricks and two methods for running your packaged Kedro project as a job:

- [Set up your project for deployment on Databricks.](#set-up-your-project)
- [Run your project as a job using the Databricks workspace UI.](#deploy-and-run-your-kedro-project-using-the-workspace-ui)
- [Run your project as a job using dbx.](#deploy-and-run-your-kedro-project-using-dbx)

Manually starting your job using the Databricks workspace UI has a shallower learning curve and is more intuitive. Using dbx to run your project saves time and allows you to store information about your job declaratively in your project, but is less intuitive and requires more time to set up.

## Prerequisites

- An active [Databricks deployment](https://docs.databricks.com/getting-started/index.html).
- A [Databricks cluster](https://docs.databricks.com/clusters/configure.html) configured with a recent version (>= 11.3 is recommended) of the Databricks runtime.
- [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine in order to create a virtual environment with a specific version of Python (>= 3.8 is required to use dbx). If you have Python >= 3.8 installed, you can use other software to create a virtual environment.

## Set up your project

### Note your Databricks username and host

Note your Databricks **username** and **host** as you will need it for the remainder of this guide.

Find your Databricks username in the top right of the workspace UI and the host in the browser's URL bar, up to the first slash (e.g., `https://adb-123456789123456.1.azuredatabricks.net/`):

![Find Databricks host and username](../meta/images/find_databricks_host_and_username.png)

```{note}
Your databricks host must include the protocol (`https://`).
```

### Install Kedro and dbx in a new virtual environment

In your local development environment, create a virtual environment for this tutorial using Conda:

```bash
conda create --name iris-databricks python=3.10
```

Once it is created, activate it:

```bash
conda activate iris-databricks
```

With your Conda environment activated, install Kedro and dbx:

```bash
pip install kedro dbx --upgrade
```

### Authenticate the Databricks CLI

**Now, you must authenticate the Databricks CLI with your Databricks instance.**

[Refer to the Databricks documentation](https://docs.databricks.com/dev-tools/cli/index.html#set-up-authentication) for a complete guide on how to authenticate your CLI. The key steps are:

1. Create a personal access token for your user on your Databricks instance.
2. Run `databricks configure --token`.
3. Enter your token and Databricks host when prompted.
4. Run `databricks fs ls dbfs:/` at the command line to verify your authentication.

```{note}
dbx is an extension of the Databricks CLI, a command-line program for interacting with Databricks without using its UI. You will use dbx to automatically package your project, upload it to Databricks and run it as a job.
```

### Create a new Kedro project

Create a Kedro project with the PySpark Iris starter using the following command in your local environment:

```bash
kedro new --starter=pyspark-iris
```

Name your new project `iris-databricks` for consistency with the rest of this guide. This command creates a new Kedro project using the PySpark Iris starter template.

### Create an entry point for Databricks

The default entry point of a Kedro project uses a Click command line interface (CLI), which is not compatible with Databricks. To run your project as a Databricks job, you must define a new entry point speficially for use on Databricks.

The PySpark Iris starter has this entry point pre-built, so there is no extra work to do in this guide. **Generally you must create it manually for your own projects using the following steps**:

1. **Create an entry point script**: Create a new file in `<project_root>/src` named `databricks_run.py`. Copy the contents of the `<project_root>/src/databricks_run.py` file defined in the [PySpark Iris starter]() to this new file.

2. **Define a new entry point**: Open `<project_root>/src/setup.py` in a text editor or IDE and add a new line in the definition of the `entry_point` tuple, so that it becomes:

```python
entry_point = (
    ...
    "databricks_run = <package_name>.databricks_run"
)
```

Remember to replace <package_name> with the correct package name for your project.

This process adds an entry point to your project which can be used to run it on Databricks.

```{note}
Because you are no longer using the default entry-point for Kedro, you will not be able to run your project with the options it allows. Instead, the `databricks_run` entry point in PySpark-Iris contains a simple implementation of the following options:
- `--package`: 
- `--pipeline`: specifies a pipeline for your run.
- `--tags`:
- `--env`: specifies a configuration environment to load for your run.
- `--conf-source`: specifies the location of the `conf/` directory to use with your Kedro project.
- `--params`: 
```

### Package your project

To package your Kedro project for deployment on Databricks, you must create a Wheel (`.whl`) file, which is a binary distribution of your project. In the root directory of your Kedro project, run the following command:

```bash
kedro package
```

This command generates a `.whl` file in the `dist` directory within your project's root directory.

### Upload project data and configuration to DBFS

Your packaged Kedro project needs access to data and configuration in order to run. Therefore, you will need to upload your project's data and configuration to an accessible location. In this guide, we will store the data on the Databricks File System (DBFS).

The PySpark Iris starter contains an environment that is set up to access data stored in DBFS (`conf/databricks`). To learn more about environments in Kedro configuration, see the [configuration documentation](../configuration/configuration_basics.md#configuration-environments). When you run your project on Databricks, you will pass the name of this environment as an option, as well as the path to the `conf/` directory on DBFS.

There are several ways to upload data to DBFS. In this guide, it is recommended to use [Databricks CLI](https://docs.databricks.com/dev-tools/cli/dbfs-cli.html) because of the convenience it offers. At the command line in your local environment, use the following Databricks CLI commands to upload your project's locally stored data and configuration to DBFS:

```bash
databricks fs cp --recursive <project_root>/data/ dbfs:/FileStore/iris-databricks/data
databricks fs cp --recursive <project_root>/conf/ dbfs:/FileStore/iris-databricks/conf
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

```{note}
A Kedro project's configuration and data do not get included when it is packaged. They must be stored somewhere accessible to allow your packaged project to run.
```

## Deploy and run your Kedro project using the workspace UI

To run your packaged project on Databricks using the workspace UI, perform the following steps:

1. **Create a new job**: In the Databricks workspace, navigate to the "Worfklows" tab and click "Create Job":

![Create Databricks job](../meta/images/databricks_create_new_job.png)

2. **Configure the job**:
- Enter 'iris-databricks' in the `Name` field.
- In the dropdown menu for the `Type` field, select 'Python wheel'
- In the `Package name` field, enter `iris_databricks`. This is the name of your package as defined in your project's `src/setup.py` file.
- In the `Entry Point` field, enter `databricks_run`. This is the name of the [entry point](#create-an-entry-point-for-databricks) to run your package from.
- Select your cluster in the dropdown menu for the `Cluster` field.
- In the `Dependent libraries` field, click `Add` and upload the `.whl` file that you [created of your project](#package-your-project).
- In the `Parameters` field, enter the following list of runtime options:

```bash
["--package","iris_databricks","--conf-source","/dbfs/FileStore/iris-databricks/conf","--env","databricks"]
```

The final configuration for your job should look like the following:

![Configure Databricks job](../meta/images/databricks_configure_new_job.png)

3. **Run the job**: Click "Run Now" to start a run of the job. The job's status will be displayed in the `Runs` tab. Navigate to the `Runs` tab and view the logs and results by clicking on the job run in the list:

![Databricks run job](../meta/images/databricks_run_job.png)

After the job has been run, you can view the output in the logs:

By following these steps, you packaged your Kedro project and manually ran it as a job on Databricks using the workspace UI.

## Deploy and run your Kedro project using dbx

dbx allows you to define a Databricks workflow in a [deployment file](https://dbx.readthedocs.io/en/latest/reference/deployment/). This file stores information about how your project should be run on Databricks and can be either YAML or JSON format. This file can be stored inside your project, where it can be added to version control.

In this section, you will use `dbx deploy` to create a Databricks workflow of your packaged Kedro project using a deployment file in YAML format, then you will run your packaged Kedro project using `dbx launch`.

1. **Create a `dbx` deployment file**: In your Kedro project's `conf` directory, create a `dbx` deployment file named `deployment.yml`. Add the following declarative information on how to deploy and run your Kedro project on Databricks:

```yaml
environments:
  default:
    workflows:
      - name: "iris-databricks"
        tasks:
          - task_key: "main"
            python_wheel_task:
              package_name: "iris_databricks"
              entry_point: "databricks_run"
              parameters: ["--package","iris_databricks","--conf-source","/dbfs/FileStore/iris-databricks/conf","--env","databricks"]
```

2. **Deploy the job**: In your Kedro project's root directory, run the following command to deploy the job using the `dbx` CLI:

```bash
dbx deploy --config-file dbx_deploy.json
```

This command uploads the Wheel file to the Databricks workspace, creates or updates the job, and configures the job with the specified cluster settings and job parameters.

3. **Run the job**: To start the job, run the following command:

```bash
dbx launch --job my_kedro_job
```

This command initiates the job execution, and you can monitor the job's progress in the Databricks workspace's "Jobs" tab.

By following these steps, you can deploy your Kedro project as a Databricks job using `dbx` and run it on the Databricks platform.
