# Development Workflow

This guide demonstrates a development workflow for Kedro projects on Databricks using Databricks Repos. This hybrid workflow involves developing your Kedro project using a local Integrated Development Environment (IDE) and using Databricks notebooks for testing purposes, this approach has several advantages, it allows for:

- Use of powerful development features offered by an IDE that are not available on Databricks notebooks.
- Ensuring version control for your project.
- Enhanced multiuser development.

An IDE offers various benefits for development:

- Auto-completion and suggestions for code, improving your development speed and accuracy.
- Linters like pylint or flake8 can be integrated to catch potential issues in your code.
- Static type checkers like mypy can check types in your code, helping to identify potential type-related issues early in the development process.

To set up these features, look for instructions specific to your IDE (for instance, [VS Code](https://code.visualstudio.com/docs/python/linting)).

We will demonstrate this using an example based on the Kedro PySpark Iris starter. This workflow also enables multiuser collaboration on a Kedro project and facilitates best practices by keeping project code version controlled.

## Prerequisites

- New or existing [AWS account](https://aws.amazon.com/premiumsupport/knowledge-center/create-and-activate-aws-account/) with administrative privileges.
- Active [Databricks deployment](https://docs.databricks.com/getting-started/index.html) on AWS (Databricks Community Edition won't suffice as it doesn't allow you to provision personal tokens).
- A [Databricks cluster](https://docs.databricks.com/clusters/configure.html) configured with a recent version (>= 11.3 is recommended) of the Databricks runtime.
- [Conda installed](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html) on your local machine.
- An account on a Git provider such as [GitHub](https://github.com/), you can check which [Git providers are supported by Databricks](https://docs.databricks.com/repos/index.html#supported-git-providers).
- [Git installed](https://git-scm.com/book/en/v2/Getting-Started-Installing-Git) on your local machine.

## Develop a project using the hybrid workflow

### Create a new project and add it to version control

Initialize a Kedro project with the PySpark Iris starter. To do this, run the following command in your local environment:

```{bash}
kedro new --starter=pyspark-iris
```

Name your new project `iris-databricks` for observability.

This command will create a new Kedro project using the PySpark Iris starter template. After creating the project, initialize Git for the Kedro project by running the following commands:

```{bash}
cd <project_root>
git init
```

### Add your project to version control

Create a new Git repository with your Git provider. Once the repository is set up, generate an access token, which will be used to connect your Kedro project with Databricks. Look up the documentation of your Git provider to learn how to generate an access token if you are unclear, as this is different for each provider.

To sync your local Git repository with the remote repository stored on your Git provider, use the following commands:

```{python}
git remote add origin <your-git-repository-url>
git add .
git commit -m "Initial commit"
git push -u origin main
```

Replace `<your-git-repository-url>` with the URL of the Git repository you created earlier.

### Set up Databricks Repos and clone your project

The next step is to sync the remote repository stored on your Git provider to Databricks Repos.

To integrate Databricks Repos with your remote Git repository, you first need to obtain an access token from your Git provider. Access tokens are used for authentication and authorization. The process for obtaining a token varies depending on your Git provider. For detailed instructions on how to generate an access token for your specific Git provider, refer to the [Databricks documentation](https://docs.databricks.com/repos/get-access-tokens-from-git-provider.html).

### Sync your Git repository with Databricks

After obtaining your Git access token, you need to sync your remote Git repository to Databricks. To do this, follow these steps:

1. Navigate to the Repos tab in your Databricks workspace.
2. Click on the 'Add Repo' button.
3. In the 'Add Repo' dialog, select your Git provider from the list.
4. Enter the URL of your remote Git repository containing the Kedro project.
5. Paste the access token you generated earlier in the 'Access Token' field.
6. Click on the 'Add Repo' button to complete the setup.
7. Clone your Kedro project into Databricks Repos

In the Repos tab, find the connected Git repository and click on it. Databricks will automatically clone the repository and display its contents. Your Kedro project is now available in Databricks Repos, and you can start working with it in the Databricks Workspace.

```{note}
Databricks Repos supports common Git operations that you can use to manage your repository, see the [Databricks documentation](https://docs.databricks.com/repos/git-operations-with-repos.html) for reference.
```

### Run your project using Databricks notebooks

Now that your project is synced with Databricks repos, you can run it on a Databricks cluster using Databricks notebooks.

#### Create a new Databricks Notebook

To run the Python code from your Databricks Repo, [create a new Databricks Notebook](https://docs.databricks.com/notebooks/notebooks-manage.html#create-a-notebook) and attach it to your cluster.

#### Install project dependencies from the requirements.txt file

Before you import and run your Python code, you'll need to install your project's dependencies. Your project has a `requirements.txt` file for this purpose. Install the dependencies using the %pip magic command in a new cell in your notebook:

```{bash}
%pip install -r "/Repos/<your_username>/iris-databricks/requirements.txt"
```

This command will install the dependencies listed in your requirements.txt file to the Databricks cluster attached to your notebook.

#### Upload project data to DBFS

In this demonstration project, you will upload the project data to DBFS as the PySpark Iris starter catalog is set up for data stored in this location. In general, you can store project data in any  location accessible over the internet.

There are several ways to upload data to DBFS. In this guide, it is recommended to use [Databricks CLI](https://docs.databricks.com/dev-tools/cli/dbfs-cli.html) because of the convenience it offers. Use the following Databricks CLI command to upload your data:

```{bash}
databricks fs cp --recursive /data dbfs:/root/projects/iris-databricks/data
```

The --recursive flag ensures that the entire folder and its contents are uploaded.

To ensure that your folder has been successfully uploaded to DBFS, you can list the contents of the destination folder in DBFS using the following command:

```{bash}
databricks fs ls dbfs:/path/to/dbfs/folder
```

You should see the contents of the project's `data/` directory.

#### Run your project

To run your project in your notebook, enter the following code in a new cell:

```{python}
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
project_root = "/Repos/<your_username>/iris-databricks/"
bootstrap_project(project_root)
with KedroSession.create(project_path=project_root, env="databricks") as session:
    session.run()
```

Replace `<your_username>` with your Databricks username such that `project_root` correctly points to the project stored in Databricks Repos.

Run this newly created cell to start a run of your project on the attached cluster. You should see logging output while the cell is running. After execution finishes, you should see output similar to the following:

```{bash}
...
[08/09/22 11:23:30] INFO     Model has accuracy of 0.933 on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```


### Make local changes in your local development environment

Now that your project has run successfully once, you can make changes to your project using the convenience and power of your local development environment. In this section, you will change your project to use a modified classifier to create predictions on the iris data. 

#### Create a local feature branch

To isolate your changes from the main branch of your project, you will modify your project in a new feature branch. To create a new Git branch and check it out, use the following command from your project's root directory.

```{bash}
git branch feat/modified-classifier
git checkout feat/modified-classifier
```

#### Modify the classifier

Next, modify the given Python code in your local development environment to create predictions using a three-nearest neighbour classifier. A three-nearest neighbour classifier works by finding the most common class among the three closest neighbours to make a prediction. Modify the code for `make_predictions` in the file `<project_root>/src/<package_name>/node.py` to the following:

```{python}
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
    # Find the indices of the three smallest values along axis 0
    nearest_neighbours = np.argpartition(squared_distances, 2, axis=0)[:3]
    # Get the labels of the three nearest neighbors
    labels = y_train.iloc[nearest_neighbours]
    # Find the most common class among the three nearest neighbors
    y_pred = labels.apply(lambda x: Counter(x).most_common(1)[0][0], axis=0)
    # Set the index of y_pred to match the index of X_test
    y_pred.index = X_test.index
    return y_pred
```

The next step is to commit the modified code to your repository. Check that you have the `feat/modified-classifier` branch checked out using the following command:

```{bash}
git branch
```

You should see the following output:

```{bash}
* feat/modified-classifier
  main
```

The `*` character next to `feat/modified-classifier` indicates that this is the currently checked-out branch.]

Now push your changes to your remote repository:

```{bash}
git push origin --set-upstream feat/modified-classifier
```

#### Pull the new branch and check it out on Databricks Repos

First, navigate to your Databricks Repo in the Databricks Workspace UI. To pull the changes from your remote repository, look for the "Git actions" button inn the upper-right corner of the repo page (it looks like a circular arrow). From the drop-down menu, click on "Pull". This will pull the latest changes from the remote repository into your Databricks Repo.

Next, check the available branches. Click on the "Branches" button located in the upper-right corner of the repo page. You should see the newly pulled branch `feat/modified-classifier` in the list. Checkout the `feat/modified-classifier` branch by clicking on it in the list. This will switch your active branch to feat/modified-classifier. Your workspace will now show the contents of the selected branch.

#### Re-run your project after your changes

Return to your Databricks notebook. Re-run the cells you used to run your project previously. The project will now run again, giving output similar to the following:

```{bash}
...
[08/09/22 11:23:30] INFO     Model has accuracy of X.XXX on test data.                                        nodes.py:74
                    INFO     Saving data to 'metrics' (MetricsDataSet)...                             data_catalog.py:382
                    INFO     Completed 3 out of 3 tasks                                           sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                                      runner.py:89
```

As you can see, your model's accuracy has changed as you are using a different classifier to produce the result.

```{note}
If your cluster terminates, you must re-run the cell containing the `%pip ...` magic to re-install your project's dependencies. If not, repeating this step is only necessary if your project's requirements change.
```

#### Merge the modified code with the main branch

Now that you have tested your modified classifier, you can merge your changes into the main branch of your project. To merge changes from the `feat/modified-classifier branch` into the main branch of your repository in Databricks Repos follow these steps:

1. Check out the main branch in the Databricks Repos UI by clicking the branch dropdown and selecting the `main` branch.
2. Click the Merge button located next to the branch dropdown. Select the feat/modified-classifier branch from the list of branches, and click Merge.

#### Synchronise your changes with your remote and local repositories

To synchronize the main branch of your Databricks repository with your local machine and remote Git repository, follow these steps:


1. Click the Push button located in the upper-right corner of the Databricks Repos UI. This will push the merged changes to your remote Git provider.
2. In your local environment, run the following commands:

```{bash}
git pull
git checkout main
```

Now, you should be able to see the modifications made to your classifier in your local IDE.

This concludes the demonstration workflow. Your PySpark Iris project now has a newly developed feature, and the changes are synchronized across all three Git repositories (Databricks, remote, and local) that contain your project data.

```{note}
In a real project with collaborators, the best practice for merging your work with the main branch of your project is to open a pull request (PR) using your Git provider's interface. This allows your collaborators to review your work before it is merged.
```

### Summary

This simple demonstration took you through a hybrid development workflow for your Kedro project on Databricks. By using an IDE for development, Git for version control and collaboration and Databricks Repos to sync your code with Databricks, you can enhance your development experience and improve your project's velocity and quality.
