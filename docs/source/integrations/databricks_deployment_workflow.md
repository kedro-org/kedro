# Databricks deployment workflow

In this guide, you will explore the process of packaging a Kedro project and running it as a job on Databricks. Databricks jobs are a way to execute code on Databricks clusters, allowing you to run data processing tasks, ETL jobs, or machine learning workflows.

By packaging your Kedro project and running it on Databricks, you can execute your pipeline without the need for a notebook. This approach is particularly well-suited for production, as it provides a structured and reproducible way to run your code. However, it is not ideal for development, where rapid iteration is necessary. For guidance on developing a Kedro project for Databricks, see the [development workflow guide](./databricks_development_workflow.md).

This guide will cover two methods for running your packaged Kedro project as a job on Databricks:

- [Manually starting a job run via the Databricks workspace UI.](#run-your-packaged-project-via-the-databricks-workspace-ui)
- [Using dbx in your local environment to initiate the job run.](#deploying-a-kedro-project-as-a-databricks-job-using-dbx)

Manually starting your job using the Databricks workspace UI has a shallower learning curve and is more intuitive. Using dbx to run your project saves time and allows you to store information about your job declaratively in your project, but is less intuitive and requires more time to set up.

By the end of this guide, you'll have a clear understanding of the steps involved in packaging your Kedro project and running it as a job on Databricks using either of these methods.

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
dbx is an extension of the Databricks CLI, a command-line program for interacting with Databricks without using its UI. You will use dbx to sync your project's code with Databricks. While Git can sync code to Databricks repos, dbx is preferred for development as it avoids creating new commits for every change, even if those changes do not work.
```

### Create a new Kedro project

Create a Kedro project with the PySpark Iris starter using the following command in your local environment:

```bash
kedro new --starter=pyspark-iris
```

Name your new project `iris-databricks` for consistency with the rest of this guide. This command creates a new Kedro project using the PySpark Iris starter template.

### Create an entry point for Databricks

The default entry point of a Kedro project exposes a Click command line interface (CLI) and cannot be used as the entry point to your package on Databricks. To run your project as a Databricks job, you must define a new entry point for use on Databricks.

This entry point is already created for you in the PySpark Iris starter and therefore there is no extra work to do as part of this guide, though generally **you must create it manually for your own projects using the following steps**:

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
Using the default entry point of a Kedro project on Databricks will cause the job run to fail.
```

## Package and run your project via the Databricks Workspace UI

### Package your project

To package your Kedro project for deployment on Databricks, you must create a Wheel file, which is a binary distribution of your project. In the root directory of your Kedro project, run the following command:

```bash
kedro package
```

This command generates a `.whl` file in the `dist` directory within your project's root directory.

### Run your packaged project on Databricks

To run your packaged project on Databricks using the workspace UI, perform the following steps:

1. **Create a new job**: In the Databricks workspace, navigate to the "Worfklows" tab and click "Create Job":

![Create Databricks job](../meta/images/databricks_create_new_job.png)

2. **Configure the job**: Give the job a name, and in the "Task" section, select "Python file" as the task type. Provide the path to your Kedro project's `run.py` file within the Wheel package. This is the entry point for executing your Kedro pipeline.

![Configure Databricks job](../meta/images/databricks_configure_new_job.png)

3. **Specify options**:

3. **Run the job**: Click "Run Now" to start the job. The job's status will be displayed in the "Runs" tab. You can view the logs and results by clicking on the job run in the list.

![Databricks run job](../meta/images/databricks_run_job.png)

If you now 

By following these steps, you packaged your Kedro project and manually ran it as a job on Databricks using the workspace UI.







## Deploying a Kedro Project as a Databricks Job Using dbx

To deploy your Kedro project as a Databricks job using dbx, follow these steps:

### Install and configure dbx

1. **Install `dbx`**: If you haven't already, install the dbx CLI tool in your local environment by running:

```bash
pip install dbx
```

2. **Configure Databricks CLI**: Ensure that you have the Databricks CLI installed and configured with the appropriate authentication settings. For more information, refer to the [Databricks CLI documentation](https://docs.databricks.com/dev-tools/cli/index.html).

### Package Kedro Project

3. **Create a Wheel file**: Package your Kedro project into a Wheel file by running the following command in the project's root directory:

```bash
python setup.py bdist_wheel
```

This command generates a `.whl` file in the `dist` directory within your project's root directory.

### Deploy and Run the Kedro Project on Databricks

4. **Create a `dbx` deployment configuration**: In your Kedro project's root directory, create a `dbx` deployment configuration file named `dbx_deploy.json`. This file should contain the necessary information to deploy and run your Kedro project on Databricks. Here's an example configuration:

```json
{
    "jobs": {
        "my_kedro_job": {
            "type": "python",
            "python_file": "my_kedro_project/run.py",
            "libraries": [
                {"whl": "dist/my_kedro_project-0.1.0-py3-none-any.whl"}
            ],
            "job_parameters": {
                "params": "{\"param1\": \"value1\", \"param2\": \"value2\"}"
            },
            "cluster": {
                "cluster_name": "my_kedro_cluster",
                "spark_version": "8.4.x-scala2.12",
                "node_type_id": "Standard_DS3_v2",
                "autoscale": {
                    "min_workers": 1,
                    "max_workers": 4
                }
            }
        }
    }
}
```

   Replace the placeholders with the appropriate values for your Kedro project, library, and cluster configuration.

5. **Deploy the job**: In your Kedro project's root directory, run the following command to deploy the job using the `dbx` CLI:

```bash
dbx deploy --config-file dbx_deploy.json
```

This command uploads the Wheel file to the Databricks workspace, creates or updates the job, and configures the job with the specified cluster settings and job parameters.

6. **Run the job**: To start the job, run the following command:

```bash
dbx run --job my_kedro_job
```

This command initiates the job execution, and you can monitor the job's progress in the Databricks workspace's "Jobs" tab.

By following these steps, you can deploy your Kedro project as a Databricks job using `dbx` and run it on the Databricks platform.
