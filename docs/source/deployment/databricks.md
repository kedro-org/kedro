# Deployment to a Databricks cluster

This tutorial uses the [PySpark Iris Kedro Starter](https://github.com/kedro-org/kedro-starters/tree/main/pyspark-iris) to illustrate how to bootstrap a Kedro project using Spark and deploy it to a [Databricks cluster on AWS](https://databricks.com/aws).

```{note}
If you are using [Databricks Repos](https://docs.databricks.com/repos/index.html) to run a Kedro project then you should [disable file-based logging](../logging/logging.md#disable-file-based-logging). This prevents Kedro from attempting to write to the read-only file system.
```

## Prerequisites

* New or existing [AWS account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/) with administrative privileges
* Active [Databricks deployment](https://docs.databricks.com/getting-started/account-setup.html) on AWS (Databricks Community Edition won't suffice as it doesn't allow you to provision personal tokens)
* [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine
* An account on [GitHub](https://github.com/) (free tier or above)
* [Git installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) on your local machine


## Running Kedro project from a Databricks notebook

As noted in [this post describing CI/CD automation on Databricks](https://databricks.com/blog/2020/06/05/automate-continuous-integration-and-continuous-delivery-on-databricks-using-databricks-labs-ci-cd-templates.html#toc-2), _"Users may find themselves struggling to keep up with the numerous notebooks containing the ETL, data science experimentation, dashboards etc."_

Therefore, we do not recommend that you rely on the notebooks for running and/or deploying your Kedro pipelines unless it is unavoidable. The workflow described in this section may be useful for experimentation and initial data analysis stages, but it is _not_ designed for productionisation.


### 1. Project setup

First, let's create a new virtual environment and, within it, a new Kedro project:

```bash
# create fresh virtual env
# NOTE: minor Python version of the environment
# must match the version on the Databricks cluster
conda create --name iris_databricks python=3.7 -y
conda activate iris_databricks

# install Kedro and create a new project
pip install "kedro~=0.18.0"
# name your project Iris Databricks when prompted for it
kedro new --starter pyspark-iris
```

### 2. Install dependencies and run locally

Now, as the project has been successfully created, we should move into the project root directory, install project dependencies, and then start a local test run using [Spark local execution mode](https://stackoverflow.com/a/54064507/3364156), which means that all Spark jobs will be executed in a single JVM locally, rather than in a cluster. `pyspark-iris` Kedro starter used to generate the project already has all necessary configuration for it to work, you just need to have `pyspark` Python package installed, which is done for you by `pip install -r src/requirements.txt` command below.

```bash
# change the directory to the project root
cd iris-databricks/
# compile and install the project dependencies, this may take a few minutes
pip install -r src/requirements.txt
# start a local run
kedro run
```

You should get a similar output:
```console
...
2020-09-09 18:57:36,762 - iris_databricks.pipelines.data_science.nodes - INFO - Model accuracy: 100.00%
2020-09-09 18:57:36,762 - kedro.runner.sequential_runner - INFO - Completed 5 out of 5 tasks
2020-09-09 18:57:36,762 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```
### 3. Create a Databricks cluster

If you already have an active cluster with runtime version `7.1`, you can skip this step. Here is [how to find clusters in your Databricks workspace](https://docs.databricks.com/clusters/clusters-manage.html).

Follow the [Databricks official guide to create a new cluster](https://docs.databricks.com/clusters/create.html). For the purpose of this tutorial (and to minimise costs) we recommend the following settings:
* Runtime: `7.1 (Scala 2.12, Spark 3.0.0)`
* Enable autoscaling: `off`
* Terminate after 120 minutes of inactivity: `on`
* Worker type: `m4.large`
* Driver Type: `Same as worker`
* Workers: `2`
* Advanced options -> Instances -> # Volumes: `1`

While your cluster is being provisioned, you can continue to the next step.

As a result you should have:
* A Kedro project, which runs with the local version of PySpark library
* A running Databricks cluster

### 4. Create GitHub personal access token

To synchronise the project between the local development environment and Databricks, we will use a private GitHub repository, which you will create in the next step. For authentication, we will need a GitHub personal access token, so go ahead and [create this token in your GitHub developer settings](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token).

```{note}
Make sure that `repo` scopes are enabled for your token.
```

### 5. Create a GitHub repository

Now you should [create a new repository in GitHub](https://docs.github.com/en/github/getting-started-with-github/create-a-repo) using the official guide. You can keep the repository private and you don't need to commit to it just yet.

To connect to the newly created repository you can use one of 2 options:

* **SSH:** If you choose to connect with SSH, you will also need to configure [the SSH connection to GitHub](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh), unless you already have [an existing SSH key configured for GitHub](https://docs.github.com/en/github/authenticating-to-github/checking-for-existing-ssh-keys)
* **HTTPS:** If using HTTPS, you will be asked for your GitHub username and password when you push your first commit - please use your GitHub username and your [personal access token](#4-create-github-personal-access-token) generated in the previous step as a password and [_not_ your original GitHub password](https://docs.github.com/en/rest/overview/other-authentication-methods#via-username-and-password).

### 6. Push Kedro project to the GitHub repository

We will use a CLI to push the newly created Kedro project to GitHub. First, you need to initialise Git in your project root directory:

```bash
# change the directory to the project root
cd iris-databricks/
# initialise git
git init
```

Then, create the first commit:

```bash
# add all files to git staging area
git add .
# create the first commit
git commit -m "first commit"
```

Finally, push the commit to GitHub:

```bash
# configure a new remote
# for HTTPS run:
git remote add origin https://github.com/<username>/<repo-name>.git
# or for SSH run:
git remote add origin git@github.com:<username>/<repo-name>.git

# verify the new remote URL
git remote -v

# push the first commit
git push --set-upstream origin main
```

### 7. Configure the Databricks cluster

The project has now been pushed to your private GitHub repository, and in order to pull it from the Databricks, we need to configure personal access token you generated in [Step 2](#4-create-github-personal-access-token).

[Log into your Databricks workspace](https://docs.databricks.com/workspace/workspace-details.html#workspace-instance-names-urls-and-ids) and then:
1. Open `Clusters` tab
2. Click on your cluster name
3. Press `Edit`
4. Go to the `Advanced Options` and then `Spark`

![](../meta/images/databricks_cluster_edit.png)

Then in the `Environment Variables` section add your `GITHUB_USER` and `GITHUB_TOKEN` as shown on the picture:

![](../meta/images/databricks_cluster_env_vars.png)


```{note}
For security purposes, we strongly recommend against hard-coding any secrets into your notebooks.
```

Then press `Confirm` button. Your cluster will be restarted to apply the changes, this will take a few minutes.

### 8. Run your Kedro project from the Databricks notebook

Congratulations, you are now ready to run your Kedro project from the Databricks!

[Create your Databricks notebook](https://docs.databricks.com/notebooks/notebooks-manage.html#create-a-notebook) and remember to [attach it to the cluster](https://docs.databricks.com/notebooks/notebooks-manage.html#attach) you have just configured.

In your newly created notebook put each code snippet from below into a separate cell and then [run all notebook cells](https://docs.databricks.com/notebooks/notebooks-use.html#run-all-cells):

* Clone your project from GitHub

```console
%sh rm -rf ~/projects/iris-databricks && git clone --single-branch --branch main https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/<your-repo-name>.git ~/projects/iris-databricks
```

* Install the latest version of Kedro compatible with version `0.18.1`

```console
%pip install "kedro[spark.SparkDataSet]~=0.18.1"
```

* Copy input data into DBFS

```python
import logging
from pathlib import Path

# suppress excessive logging from py4j
logging.getLogger("py4j.java_gateway").setLevel(logging.ERROR)

# copy project data into DBFS
project_root = Path.home() / "projects" / "iris-databricks"
data_dir = project_root / "data"
dbutils.fs.cp(
    f"file://{data_dir.as_posix()}", f"dbfs://{data_dir.as_posix()}", recurse=True
)

# make sure the data has been copied
dbutils.fs.ls((data_dir / "01_raw").as_posix())
```

You should get a similar output:
```console
Out[11]: [FileInfo(path='dbfs:/root/projects/iris-databricks/data/01_raw/.gitkeep', name='.gitkeep', size=0),
 FileInfo(path='dbfs:/root/projects/iris-databricks/data/01_raw/iris.csv', name='iris.csv', size=3858)]
```

* Run Kedro project

```python
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project

bootstrap_project(project_root)

with KedroSession.create(project_path=project_root) as session:
    session.run()
```

You should get a similar output:

```console
...
2020-09-16 10:45:21,991 - kedro.io.data_catalog - INFO - Loading data from `example_predictions` (MemoryDataSet)...
2020-09-16 10:45:21,991 - kedro.pipeline.node - INFO - Running node: report_accuracy([example_predictions]) -> None
2020-09-16 10:45:23,128 - iris_databricks.pipelines.data_science.nodes - INFO - Model accuracy: 97.30%
2020-09-16 10:45:23,144 - kedro.runner.sequential_runner - INFO - Completed 5 out of 5 tasks
2020-09-16 10:45:23,145 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
Out[12]: {}
```

Your complete notebook should look similar to this (the results are hidden):

![](../meta/images/databricks_notebook_example.png)


### 9. Using the Kedro IPython Extension

You can interact with Kedro in Databricks through the Kedro [IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions/index.html), `kedro.extras.extensions.ipython`.

The Kedro IPython extension launches a [Kedro session](../kedro_project_setup/session.md) and makes available the useful Kedro variables `catalog`, `context`, `pipelines` and `session`. It also provides the `%reload_kedro` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) that reloads these variables (for example, if you need to update `catalog` following changes to your Data Catalog).

The IPython extension can be used in a Databricks notebook in a similar way to how it is used in [Jupyter notebooks](../tools_integration/ipython.md).

If you encounter a `ContextualVersionConflictError`, it is likely caused by Databricks using an old version of `pip`. Hence there's one additional step you need to do in the Databricks notebook to make use of the IPython extension. After you load the IPython extension using the below command:

```ipython
In [1]: %load_ext kedro.extras.extensions.ipython
```

You must explicitly upgrade your `pip` version by doing the below:

```bash
%pip install -U pip
```

After this, you can reload Kedro by running the line magic command `%reload_kedro <path_to_project_root>`.

### 10. Running Kedro-Viz on Databricks

For Kedro-Viz to run with your Kedro project, you need to ensure that both the packages are installed in the same scope (notebook-scoped vs. cluster library). i.e. if you `%pip install kedro` from inside your notebook then you should also `%pip install kedro-viz` from inside your notebook.
If your cluster comes with Kedro installed on it as a library already then you should also add Kedro-Viz as a [cluster library](https://docs.microsoft.com/en-us/azure/databricks/libraries/cluster-libraries).

Currently, if you try to run `%run_viz` on Databricks it will only display the below instead of running the Kedro-Viz app in the notebook.

```console
<IPython.core.display.HTML object>
```

While we fix this issue, we have a temporary workaround which involves you setting up a R Shiny application to run Kedro-Viz on Databricks.

To run Kedro-Viz, first ensure that you are in your Kedro project directory and then run the below command in your Databricks notebook:

```bash
%sh kedro viz --no-browser --host 0.0.0.0 --port 4141
```

```{note}
The command execution continues to run and will need to be cancelled manually before proceeding to the next step. Cancelling the command will not quit the Kedro-Viz server. Please see below GIF on how to cancel.
```

![](../meta/images/databricks_cancel_command.gif)


After this, you must try and run an example Shiny app using the below command:

```bash
%r
library(shiny)
runExample("01_hello")
```

![](../meta/images/databricks_shiny_command.png)

When you click on the Shiny app link, it will open a browser with an example Shiny app running. Now edit the port at the end of the URL and change it to 4141.

![](../meta/images/databricks_kedro_viz.gif)

You will notice Kedro-Viz is blank at first, but if you click on the flowchart tab, Kedro-Viz will run as normal.

```{note}
Ctrl+C to quit the Kedro-Viz server doesn't work on Databricks. To end the process you will need to find the process-id on port=4141 or the port you used and kill it using the Linux command `kill -9 PID`.
```
