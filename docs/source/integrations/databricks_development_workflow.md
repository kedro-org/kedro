# Databricks development workflow

This guide demonstrates a development workflow for Kedro projects on Databricks using Databricks Repos. This hybrid workflow involves developing your Kedro project using a local Integrated Development Environment (IDE) and Databricks notebooks for testing purposes. This guide demonstrates this workflow using an example based on the Kedro PySpark Iris starter.
This workflow has several advantages, enabling:

- Use of powerful development features offered by an IDE not available on Databricks notebooks.
- Version control of your project.
- Multiuser development.

An IDE offers benefits for development:

- Auto-completion and suggestions for code, improving your development speed and accuracy.
- Linters like Pylint or Flake8 can be integrated to catch potential issues in your code.
- Static type checkers like Mypy can check types in your code, helping to identify potential type-related issues early in the development process.

To set up these features, look for instructions specific to your IDE (for instance, [VS Code](https://code.visualstudio.com/docs/python/linting)).

## Prerequisites

- New or existing [AWS account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/) with administrative privileges.
- Active [Databricks deployment](https://docs.databricks.com/getting-started/index.html) on AWS (Databricks Community Edition won't suffice as it doesn't allow you to provision personal tokens).
- A [Databricks cluster](https://docs.databricks.com/clusters/configure.html) configured with a recent version (>= 11.3 is recommended) of the Databricks runtime.
- [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine.
- An account on a Git provider such as [GitHub](https://github.com/). You can check which [Git providers are supported by Databricks](https://docs.databricks.com/repos/index.html#supported-git-providers).
- [Git installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) on your local machine.

## Develop a project using the hybrid workflow

### Create a virtual environment and install Kedro and the Databricks CLI

Create a virtual environment for this tutorial using Conda:

```bash
conda create --name kedro-hybrid-workflow python=3.10
```

Once it is created, activate it:

```bash
conda activate kedro-hybrid-workflow
```

With your Conda environment activated, install Kedro and the Databricks CLI:

```bash
pip install kedro databricks-cli --upgrade
```

After installing the Databricks CLI, you must authenticate it with your [Databricks instance]([Databricks documentation](https://docs.databricks.com/dev-tools/cli/index.html#set-up-authentication).

### Create a new project and add it to Version Control

Create a Kedro project with the PySpark Iris starter. To do this, run the following command in your local environment:

```bash
kedro new --starter=pyspark-iris
```

Name your new project `iris-databricks` for consistency with the rest of this guide.

This command will create a new Kedro project using the PySpark Iris starter template. Initialize Git for the Kedro project by running the following commands:

```bash
cd iris-databricks
git init
```

### Add your project to Version Control

Create a new private Git repository with your Git provider. Then, generate an access token to connect your Kedro project with Databricks. Look up the documentation of your Git provider to learn how to generate an access token if you are unclear, as this is different for each provider.

To sync your local Git repository with the remote repository stored on your Git provider, use the following commands:

```python
git remote add origin <your-git-repository-url>
git add .
git commit -m "Initial commit"
git push -u origin main
```

Replace `<your-git-repository-url>` with the URL of the Git repository you created earlier.

### Set up Databricks Repos and clone your project

The next step is to sync the remote repository stored on your Git provider to Databricks Repos.

To integrate Databricks Repos with the private Git repository stored by your Git provider, you first need to obtain an access token from your Git provider. Access tokens authenticate an application that wishes to access your private Git repository.

The process for obtaining a token varies depending on your Git provider. Follow the instructions for generating an access token and adding it to Databricks specific to your Git provider in the [Databricks documentation](https://docs.databricks.com/repos/get-access-tokens-from-git-provider.html).

### Sync your Git repository with Databricks

After obtaining your Git access token, sync your remote Git repository to Databricks:

1. Navigate to the Repos tab in your Databricks workspace.
2. Click on the 'Add Repo' button.
3. In the 'Add Repo' dialogue, select your Git provider from the list.
4. Enter the URL of your remote Git repository containing the Kedro project.
5. Click the 'Add Repo' button to complete the setup.

Find the connected Git repository and click on it in the Repos tab. Databricks will automatically clone the repository and display its contents. Your Kedro project is now available in Databricks Repos, and you can start working with it in the Databricks Workspace.

```{note}
Databricks Repos supports some Git operations that you can use to manage your repository, see the [Databricks documentation](https://docs.databricks.com/repos/git-operations-with-repos.html) for reference.
```

### Run your project using Databricks notebooks

Now that your project is synced with Databricks Repos, the following sections will guide you through running it on a cluster using notebooks.

#### Create a new Databricks notebook

To run the Python code from your Databricks repo, [create a new Databricks Notebook](https://docs.databricks.com/notebooks/notebooks-manage.html#create-a-notebook) and attach it to your cluster.

#### Install project dependencies from the requirements.txt file

Before you import and run your Python code, you'll need to install your project's dependencies. Your project has a `requirements.txt` file for this purpose. Install the dependencies using the %pip magic command in a new cell in your notebook:

```bash
%pip install -r "/Workspace/Repos/<your_username>/iris-databricks/src/requirements.txt"
```

This command will install the dependencies listed in your requirements.txt file to the Databricks cluster attached to your notebook.

#### Upload project data to DBFS

In this demonstration project, you will upload the project data to DBFS as the PySpark Iris starter comes with a catalog set up to access data stored on DBFS.

There are several ways to upload data to DBFS. In this guide, it is recommended to use [Databricks CLI](https://docs.databricks.com/dev-tools/cli/dbfs-cli.html) because of the convenience it offers. Use the following Databricks CLI command to upload your data:

```bash
databricks fs cp --recursive data/ dbfs:/root/projects/iris-databricks/data
```

The --recursive flag ensures that the entire folder and its contents are uploaded.

To ensure that your folder has been uploaded to DBFS, you can list the contents of the destination folder in DBFS using the following command:

```bash
databricks fs ls dbfs:/path/to/dbfs/folder
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

#### Run your project

To run your project in your notebook, use the Kedro IPython extension. Start by loading the extension in a new cell:

```bash
%load_ext kedro.ipython
```

Loading the extension allows you to use the `%reload_kedro` line magic to load your Kedro project. The next step is to load your Kedro project with the `databricks` environment. The `databricks` environment is defined in the PySpark Iris starter and directs Kedro to use the configuration in the `conf/databricks` directory. To learn more about environments in Kedro configuration, see the [documentation](../configuration/configuration_basics.md#configuration-environments).

Create a new cell and run the line magic to load your Kedro project.

```bash
%reload_kedro /Workspace/Repos/<your_username>/iris-databricks --env=databricks
```

Replace `<your_username>` with your Databricks username such that `project_root` correctly points to the project stored in Databricks Repos. Loading your Kedro project with the `%reload_kedro` line magic will define four global variables in your notebook: `context`, `session`, `catalog` and `pipelines`. You will use the `session` variable to run your project.

To run your project, create a new cell and execute the following piece of Python code in it:

```bash
session.run()
```

You should see logging output while the cell is running. After execution finishes, you should see output similar to the following:

```bash
...
[08/09/22 11:23:30] INFO     Model has accuracy of 0.960 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```

### Make local changes in your local development environment

Now that your project has run successfully once, you can make changes using the convenience and power of your local development environment. In this section, you will change your project to use a modified classifier to create predictions on the iris data.

#### Create a local feature branch

To isolate your changes from the main branch of your project, you will modify your project in a new feature branch. To create a new Git branch and check it out, use the following command from your project's root directory.

```bash
git branch feat/modified-classifier
git checkout feat/modified-classifier
```

#### Modify the classifier

The PySpark Iris starter uses a one-nearest neighbour classifier to make predictions. In this section, you will modify it to create predictions using a three-nearest neighbour classifier. A three-nearest neighbour classifier works by finding the most common class among the three closest neighbours to make a prediction. A one-nearest neighbour classifier only uses the class of the nearest neighbour.

Open the file `<project_root>/src/iris_databricks/nodes.py` in your IDE. Insert a new line underneath the import statements and add the following code to it:

```python
from scipy.stats import mode
```

Now modify the classifier by changing the code in the function `make_predictions`:

```python
def make_predictions(
    X_train: pd.DataFrame, X_test: pd.DataFrame, y_train: pd.DataFrame
) -> pd.DataFrame:
    """Uses 3-nearest neighbour classifier to create predictions.
    Args:
        X_train: Training data of features.
        y_train: Training data for target.
        X_test: Test data for features.
    Returns:
        y_pred: Prediction of the target variable.
    """

    X_train_numpy = X_train.to_numpy()
    X_test_numpy = X_test.to_numpy()

    squared_distances = np.sum(
        (X_train_numpy[:, None, :] - X_test_numpy[None, :, :]) ** 2, axis=-1
    )
    three_nearest_neighbours = np.argsort(squared_distances, axis=0)[:3]

    # Use list comprehension to index y_train for each test point's three nearest neighbours
    y_nearest_neighbours = np.array(
        [y_train.iloc[three_nearest_neighbours[:, i]] for i in range(X_test.shape[0])]
    )

    y_pred_mode, _ = mode(y_nearest_neighbours, axis=1)
    y_pred = pd.DataFrame(
        y_pred_mode.squeeze(), columns=y_train.columns, index=X_test.index
    )

    return y_pred
```

The next step is to commit the modified code to your repository. Check that you have the `feat/modified-classifier` branch checked out using the following command:

```bash
git branch
```

You should see the following output:

```bash
* feat/modified-classifier
  main
```

The `*` character next to `feat/modified-classifier` indicates that this is the currently checked-out branch. Now commit your changes to the branch and push it to your remote repository:

```bash
git add -u
git commit -m "Modify 1-nearest neighbour classifier to 3-nearest-neighbour classifier"
git push origin --set-upstream feat/modified-classifier
```

#### Pull the new branch and check it out on Databricks Repos

Navigate to your Databricks Repo in the Databricks Workspace UI. To pull the changes from your remote repository, look for the `Pull` button in the upper-right corner of the Repo page. Click it to sync the latest changes from the remote repository into your Databricks Repo.

Next, check the available branches. Click on the "Branches" button in the upper-left corner of the Repo page. You should see the newly pulled branch `feat/modified-classifier` in the list. Check out the `feat/modified-classifier` branch by clicking on it in the drop-down list. Your active branch is now feat/modified-classifier.

#### Re-run your project after your changes

Return to your Databricks notebook. Re-run the cells you used to run your project previously. The project will now run again, giving output similar to the following:

```bash
...
[08/09/22 11:23:30] INFO     Model has accuracy of 1.000 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```

You can see that your model's accuracy has changed now that you are using a different classifier to produce the result. As it seems that the accuracy of your classifier on test data has improved, you decide to merge these changes to the `main` branch of your project.

```{note}
If your cluster terminates, you must re-run the cell containing the `%pip ...` magic to re-install your project's dependencies. If not, repeating this step is only necessary if your project's requirements change.
```

#### Merge the modified code with the main branch

To merge changes from the `feat/modified-classifier` branch into the main branch of your repository, use Git in your local environment. First, check out the main branch:

```bash
git checkout main
```

Now, merge the `feat/modified-classifier` branch:

```bash
git merge feat/modified-classifier
```

Now that the main branch of your local Git repository contains the changes you made, you should sync the main branch of your repository with your remote Git provider. At the command line in your local development environment:

```bash
git push origin
```

To sync the main branch to your Databricks Repo, navigate to your Databricks Repo in the Databricks Workspace UI and use the `Pull` button as you did previously.

```{note}
In a project with collaborators, the best practice for merging your work with the main branch is to open a pull request (PR) using your Git provider's interface. PRs enable your collaborators to review your work before merging it.
```

### Summary

Your PySpark Iris project now has a newly developed feature, and the changes are synced across all three Git repositories (Databricks, remote, and local) that contain your project data.

This tutorial covered a hybrid Kedro project development workflow on Databricks, using your local development environment, Git for versioning, and Databricks Repos to sync code, improving development efficiency and quality.
