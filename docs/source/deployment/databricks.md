# Deployment to a Databricks cluster

This tutorial uses the [PySpark Iris Kedro Starter](https://github.com/kedro-org/kedro-starters/tree/main/pyspark-iris) to illustrate how to bootstrap a Kedro project using Spark and deploy it to a [Databricks](https://databricks.com/) cluster on AWS, Azure or GCP.

>If you are using [Databricks Repos](https://docs.databricks.com/repos/index.html) to run a Kedro project then you should [disable file-based logging](../logging/logging.md#disable-file-based-logging). This prevents Kedro from attempting to write to the read-only file system.

>If you are a Kedro contributor looking for information on deploying a custom build of Kedro to Databricks, see the [development guide](../contribution/development_for_databricks.md).

```{note}
If you are a Kedro contributor looking for information on deploying a custom build of Kedro to Databricks, see the [development guide](../contribution/development_for_databricks.md).
```

## Prerequisites

* New or existing [AWS](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/), [Azure](https://signup.azure.com) or [GCP](https://cloud.google.com) account with administrative privileges
* Active [Databricks deployment](https://docs.databricks.com/getting-started/index.html) (Databricks Community Edition won't suffice as it doesn't allow you to provision personal tokens)
* [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) or [virtualenv](https://virtualenv.pypa.io/en/latest/) installed on your local machine
* An account on [GitHub](https://github.com/) (free tier or above), [Azure DevOps](https://azure.microsoft.com/en-us/products/devops) or [GitLab](https://about.gitlab.com)
* [Git](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) installed on your local machine

>For a full list of supported Git providers check this [Databricks Repos](https://docs.databricks.com/repos/index.html#supported-git-providers) page

## Running Kedro project from a Databricks notebook

As noted in [this post describing CI/CD automation on Databricks](https://databricks.com/blog/2020/06/05/automate-continuous-integration-and-continuous-delivery-on-databricks-using-databricks-labs-ci-cd-templates.html#toc-2), _"Users may find themselves struggling to keep up with the numerous notebooks containing the ETL, data science experimentation, dashboards etc."_

Therefore, we do not recommend that you rely on the notebooks for running and/or deploying your Kedro pipelines unless it is unavoidable. The workflow described in this section may be useful for experimentation and initial data analysis stages, but it is _not_ designed for productionisation.


### 1. Project setup

First, let's create a new virtual environment and, within it, a new Kedro project:

#### Using Conda
```bash
# create fresh virtual env
# NOTE: minor Python version of the environment
# must match the version on the Databricks cluster
conda create --name iris_databricks python=3.9 -y
conda activate iris_databricks

# install Kedro and create a new project
pip install "kedro~=0.18.5"
# name your project Iris Databricks when prompted for it
kedro new --starter=pyspark-iris
```

#### Using virtualenv
```bash
# create fresh virtual env
# NOTE: minor Python version of the environment
# must match the version on the Databricks cluster.
# Make sure to install python and point to
# the install location in the PYTHON_PATH variable
export PYTHON_PATH=/usr/local/bin/python3.9
pip install virtualenv
# create a new virtual environment in .venv inside the project folder
cd iris-databricks/
virtualenv .venv -p $PYTHON_PATH
source .venv/bin/activate

# install Kedro and create a new project
pip install "kedro~=0.18.6"
# name your project Iris Databricks when prompted for it
kedro new --starter=pyspark-iris
cd ..
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

You can also run the following to install the project as a whole to be able to import it and test locally.

```bash
# change the directory to the project root
cd iris-databricks/
# install the project and all its dependecies as defined in src/setup.py
pip install src/
# start a local run
kedro run
```

You should get a similar output:
```console
...
[08/09/22 11:23:30] INFO     Model has accuracy of 0.933 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```
### 3. Create a Databricks cluster

If you already have an active cluster with runtime version `11.3 LTS` or above, you can skip this step and move onto [Step 4](#4-create-repository-personal-access-token-and-add-to-databricks). Here is [how to find clusters in your Databricks workspace](https://docs.databricks.com/clusters/clusters-manage.html).

Follow the [Databricks official guide to create a new cluster](https://docs.databricks.com/clusters/create-cluster.html). For the purpose of this tutorial (and to minimise costs) we recommend the following settings:
* Runtime: `11.3 LTS (Scala 2.12, Spark 3.3.0)`
* Worker type: `Standard_DS3_v2` (Azure) | `m4.large` (AWS) | `n1-standard-4` (GCP)
* Driver Type: `Same as worker`
* Workers: `1`
* Terminate after: `30 minutes`

>While your cluster is being provisioned, you can continue to the next step to setup your repo in Databricks.

As a result you should have:
* A Kedro project, which runs with the local version of PySpark library
* A running Databricks interactive cluster

### 4. Create and add repository personal access token to Databricks

To synchronise the project between the local development environment and Databricks, we will use a private GitHub/Azure DevOps/GitLab repository, which you will create in the next step. For authentication, we will need a GitHub/Azure DevOps/GitLab personal access token, so go ahead and create this token in your [GitHub](https://docs.github.com/en/github/authenticating-to-github/creating-a-personal-access-token), [Azure DevOps](https://learn.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate?view=azure-devops&tabs=Windows), or [GitLab](https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html) developer settings. If you are using another Git provider, follow the instructions for your platform to generate a personal access token.

>Make sure that `repo` scopes are enabled for your token.

Once you have the token, you will add it to your Databricks workspace. 
1. Under `User Settings` 
2. Navigate to `Git integration`
3. Select your Git provider
4. Fill in your Git username 
5. Paste the the [personal access token](#4-create-github-personal-access-token) you setup earlier.

![](../meta/images/databricks_token.png)


>If you do not see this section, reach out to your Databricks administrator to enable Repos in your workspace. If this is not feasible, follow the [alternate instructions](#11-alternative-deployment-without-using-databricks-repos) below to authenticate Databricks with your repo through cluster secrets.

### 5. Create a (private) repository

Now you should create a new repository in [GitHub](https://docs.github.com/en/github/getting-started-with-github/create-a-repo), [Azure DevOps](https://learn.microsoft.com/en-us/azure/devops/repos/git/create-new-repo), [GitLab](https://docs.gitlab.com/ee/user/project/index.html#create-a-project) using the official guides. You can keep the repository private and you don't need to commit to it just yet.

To connect to the newly created repository locally, you can use one of 2 options:

* **SSH:** If you choose to connect with SSH, you will also need to configure the SSH connection to [GitHub](https://docs.github.com/en/github/authenticating-to-github/connecting-to-github-with-ssh), [Azure DevOps](https://learn.microsoft.com/en-us/azure/devops/repos/git/use-ssh-keys-to-authenticate), or [GitLab](https://docs.gitlab.com/ee/user/ssh.html). You might already have an [existing SSH key configured for GitHub](https://docs.github.com/en/github/authenticating-to-github/checking-for-existing-ssh-keys) or your Git provider.
* **HTTPS:** If using HTTPS, you will be asked for your username and password when you push your first commit - please use your git username and your [personal access token](#4-create-github-personal-access-token) generated in the previous step as a password.

### 6. Push the Kedro project to your repository

We will use a CLI to push the newly created Kedro project to your newly created repository. First, you need to initialise Git in your project root directory:

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

Finally, push the commit to your repository. Follow these instructions for getting the SSH/HTTPS URLs for your repository: [GitHub](https://docs.github.com/en/get-started/getting-started-with-git/about-remote-repositories), [Azure DevOps](https://learn.microsoft.com/en-us/azure/devops/repos/git/clone), or [GitLab](https://docs.gitlab.com/ee/gitlab-basics/start-using-git.html#clone-a-repository). Fill in the `<HTTPS URL>` or `<SSH URL>` according to your method of authenticating with git:

```bash
# configure a new remote
# for HTTPS run:
git remote add origin <HTTPS URL>
# or for SSH run:
git remote add origin <SSH URL>

# verify the new remote URL
git remote -v

# push the first commit
git push --set-upstream origin main
```

### 7. Configure Databricks to Read from your Repo

The project has now been pushed to your private repository, and in order to pull it from the Databricks, we need to add the repo to your workspace.

[Log into your Databricks workspace](https://docs.databricks.com/workspace/workspace-details.html#workspace-instance-names-urls-and-ids) and then:
1. Open `Repos` tab
2. Click on `Add Repo`
3. Paste the URL of your repo (HTTPS)
4. Click on `Create Repo`

![](../meta/images/databricks_repo.png)

You should now be able to browse your repository inside Databricks under your email.

### 8. Run your Kedro project from the Databricks notebook

Congratulations, you are now ready to run your Kedro project from Databricks!

[Create your Databricks notebook](https://docs.databricks.com/notebooks/notebooks-manage.html#create-a-notebook) and remember to attach it to the cluster you have just configured.

#### Installing Dependenices

Before running your Kedro pipeline, make sure to install the project dependencies from your `src/requirements.txt` using `%pip install <project_root/src/requirements.txt>`, where `<project_root>` is the path to the repo inside the workspace. 

In your newly-created notebook, put each of the below code snippets into a separate cell, then [run all cells](https://docs.databricks.com/notebooks/run-notebook.html):

* Clone your project from GitHub

```console
%sh rm -rf ~/projects/iris-databricks && git clone --single-branch --branch main https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/<your-repo-name>.git ~/projects/iris-databricks
```

* Install Kedro and the latest compatible version of Kedro-Datasets.

```console
%pip install "kedro==0.18.5" "kedro-datasets[spark.SparkDataSet]~=1.0.2"
```

* Copy input data into DBFS

```python
import logging
from pathlib import Path
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
[08/09/22 11:23:30] INFO     Model has accuracy of 0.933 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```

### 9. Using the Kedro IPython Extension

You can interact with Kedro in Databricks through the Kedro [IPython extension](https://ipython.readthedocs.io/en/stable/config/extensions/index.html), `kedro.ipython`.

The Kedro IPython extension launches a [Kedro session](../kedro_project_setup/session.md) and makes available the useful Kedro variables `catalog`, `context`, `pipelines` and `session`. It also provides the `%reload_kedro` [line magic](https://ipython.readthedocs.io/en/stable/interactive/magics.html) that reloads these variables (for example, if you need to update `catalog` following changes to your Data Catalog).

The IPython extension can be used in a Databricks notebook in a similar way to how it is used in [Jupyter notebooks](../notebooks_and_ipython/kedro_and_notebooks.md).

If you encounter a `ContextualVersionConflictError`, it is likely caused by Databricks using an old version of `pip`. Hence there's one additional step you need to do in the Databricks notebook to make use of the IPython extension. After you load the IPython extension using the below command:

```ipython
In [1]: %load_ext kedro.ipython
```

You must explicitly upgrade your `pip` version by doing the below:

```bash
%pip install -U pip
```

After this, you can reload Kedro by running the line magic command `%reload_kedro <project_root>`.

### 10. Running Kedro-Viz on Databricks

For Kedro-Viz to run with your Kedro project, you need to ensure that both the packages are installed in the same scope (notebook-scoped vs. cluster library). i.e. if you `%pip install kedro` from inside your notebook then you should also `%pip install kedro-viz` from inside your notebook.
If your cluster comes with Kedro installed on it as a library already then you should also add Kedro-Viz as a [cluster library](https://docs.microsoft.com/en-us/azure/databricks/libraries/cluster-libraries).

Kedro-Viz can then be launched in a new browser tab with the `%run_viz` line magic:
```ipython
In [2]: %run_viz
```

## How to use datasets stored on Databricks DBFS

DBFS is a distributed file system mounted into a DataBricks workspace and accessible on a DataBricks cluster. It maps cloud object storage URIs to relative paths so as to simplify the process of persisting files. With DBFS, libraries can read from or write to distributed storage as if it's a local file.
To use datasets with DBFS, the file path passed to the dataset **must** be prefixed with `/dbfs/` and look something like, `/dbfs/example_project/data/02_intermediate/processed_data`. This applies to all datasets, including `SparkDataSet`.
> **Note**: Most Python code, except PySpark, will try to resolve a file path in the driver node storage by default, this will result in an `DataSetError` if the code is using a file path that is actually a DBFS save location. To avoid this, always make sure to point the file path to `/dbfs` when storing or loading data on DBFS. For more rules on what is saved in DBFS versus driver node storage by default, please refer to the [Databricks documentation](https://docs.databricks.com/files/index.html#what-is-the-root-path-for-databricks).

This does not apply to datasets that do not use files.


### 11. Alternative Deployment without using Databricks Repos
* Clone your project from GitHub

```console
%sh rm -rf ~/projects/iris-databricks && git clone --single-branch --branch main https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/<your-repo-name>.git ~/projects/iris-databricks
```

* Install Kedro and the latest compatible version of Kedro-Datasets.

```console
%pip install "kedro==0.18.6" "kedro-datasets[spark.SparkDataSet]~=1.0.2"
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