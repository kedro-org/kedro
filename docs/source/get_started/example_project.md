# Iris dataset example project

In this chapter, we describe the directory structure of a typical Kedro project. We will use an example based on the familiar [Iris dataset](https://www.kaggle.com/uciml/iris).

The dataset was generated in 1936 by the British statistician and biologist Ronald Fisher. The dataset contains 150 samples in total, comprising 50 samples of 3 different species of Iris plant (Iris Setosa, Iris Versicolour and Iris Virginica). For each sample, the flower measurements are recorded for the sepal length, sepal width, petal length and petal width:

![](../meta/images/iris_measurements.png)

A machine learning model can use the Iris dataset to illustrate classification (a method used to determine the type of an object by comparison with similar objects previously been categorised). Once trained on known data, the machine learning model can make a predictive classification by comparing a test object to the output of its training data.

## Create the example project

You must first [create a project](./new_project.md). Feel free to name your project as you like, but here we will assume the project's repository name is `get-started`.

```bash
kedro new --starter=pandas-iris
```

### Project directory structure

This example project illustrates a convenient starting point and some best practices. The project follows the default Kedro project template and uses folders to store datasets, notebooks, configuration and source code. When you create your own projects, you can adapt the folder structure if you need to.

The example project directory is set out as follows:

```
get-started         # Parent directory of the template
├── conf            # Project configuration files
├── data            # Local project data (not committed to version control)
├── docs            # Project documentation
├── logs            # Project output logs (not committed to version control)
├── notebooks       # Project related Jupyter notebooks (can be used for experimental code before moving the code to src)
├── README.md       # Project README
├── setup.cfg       # Configuration options for `pytest` when doing `kedro test` and for the `isort` utility when doing `kedro lint`
└── src             # Project source code
```

Kedro also creates the following hidden files and folders:

```
get-started
├── .coveragerc     # Configuration file for the coverage reporting when doing `kedro test`
├── .gitignore      # Prevent staging of unnecessary files to `git`
└── pyproject.toml  # Identifies the project root and [contains configuration information](../faq/architecture_overview.md#kedro-project)
```

#### `conf/`

The `conf` folder contains two subfolders for storing configuration information: `base` and `local`.

##### `conf/base/`

For project-specific settings to share across different installations (for example, with different users), you should use the `base` subfolder of `conf`.

The folder contains three files for the example, but you can add others as you require:

-   `catalog.yml` - [Configures the Data Catalog](../data/data_catalog.md#use-the-data-catalog-within-kedro-configuration) with the file paths and load/save configuration required for different datasets
-   `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging
-   `parameters.yml` - Allows you to define parameters for machine learning experiments e.g. train / test split and number of iterations

##### `conf/local/`

The `local` subfolder of `conf` is used for **settings that should not be shared**, such as access credentials, custom editor configuration, personal IDE configuration and other sensitive or personal content. It is specific to user and installation. The contents of `conf/local/` is ignored by `git` (through inclusion in `.gitignore`). By default, Kedro creates one file, `credentials.yml`, in `conf/local`.

#### `data`

The `data` folder contains a number of subfolders to store project data. We recommend that you put raw data into `raw` and move processed data to other subfolders according to [data engineering convention](../faq/faq.md#what-is-data-engineering-convention).

The example project has a single file, `iris.csv`, that contains the Iris dataset. The subfolders of `data` are ignored by `git` through inclusion in `.gitignore` since data is more frequently stored elsewhere, such as in an S3 bucket. However, if you are familiar with [`.gitignore`](https://docs.github.com/en/github/using-git/ignoring-files) you can edit it, if you are confident that you need to manage your data in `git`.

#### `src`

This subfolder contains the project's source code. The `src` folder contains two subfolders:

-   `get_started/` This is the Python package for your project
-   `tests/` The subfolder for unit tests for your project. Projects are preconfigured to run tests using `pytest` when you call `kedro test` from the project's root directory

### What best practice should I follow to avoid leaking confidential data?

* Do not commit data to version control.
* Do not commit notebook output cells (data can easily sneak into notebooks when you don't delete output cells).
* Do not commit credentials in `conf/`. Use only the `conf/local/` folder for sensitive information like access credentials.

```{note}
By default any file inside the `conf/` folder (and its subfolders) that contains `credentials` in its name will be ignored via `.gitignore`.
```


## Run the example project

Once you have created the project, to run project-specific Kedro commands, you must navigate to the directory in which it has been created.

Call `pip install -r src/requirements.txt` to install the project's dependencies. Next, call `kedro run`:

```bash
cd getting-started
pip install -r src/requirements.txt
kedro run
```

When the command completes, you should see a log message similar to the following in your console:

```bash
2022-04-08 11:55:03,043 - get_started.nodes - INFO - Model has a accuracy of 0.933 on test data.
2022-04-08 11:55:03,044 - kedro.runner.sequential_runner - INFO - Completed 3 out of 3 tasks
2022-04-08 11:55:03,044 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```

## Under the hood: Pipelines and nodes

The example project contains a single pipeline:

- The pipeline (`src/get_started/pipeline.py`) is responsible for splitting the data into training and testing samples, running the 1-nearest neighbour algorithm to make predictions and accuracy-reporting.


**Nodes in Pipeline**

These are the node function within `src/get_started/nodes.py`:

| Node            | Description                                                                                      | Node function name |
| --------------- | ------------------------------------------------------------------------------------------------ | ------------------ |
| Split data      | Splits the example [Iris dataset](https://www.kaggle.com/uciml/iris) into train and test samples | `split_data`       |
| Make Predictions| Makes class predictions using 1-nearest neighbour classifier and train-test set                  | `make_predictions` |
| Report accuracy | Reports the accuracy of the predictions performed by the previous node                           | `report_accuracy`  |


The file `src/pipeline_registry.py` creates and collates into a single pipeline, resolving node execution order from the input and output data dependencies between the nodes.
