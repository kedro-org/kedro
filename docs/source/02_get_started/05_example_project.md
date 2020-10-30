# Iris dataset example project

In this chapter we describe the directory structure of a typical Kedro project. We will use an example based on the familiar [Iris dataset](https://www.kaggle.com/uciml/iris).

The dataset was generated in 1936 by the British statistician and biologist Ronald Fisher. It contains 150 samples in total, comprising 50 samples of 3 different species of Iris plant (Iris Setosa, Iris Versicolour and Iris Virginica). For each sample, the flower measurements are recorded for the sepal length, sepal width, petal length and petal width, as illustrated in the following graphic.

![](../meta/images/iris_measurements.png)

The Iris dataset can be used by a machine learning model to illustrate classification (a method used to determine the type of an object by comparison with similar objects that have previously been categorised). Once trained on known data, the machine learning model can make a predictive classification by comparing a test object to the output of its training data.

## Create the example project

You must first [create a project](./04_new_project.md). Feel free to name your project as you like, but here we will assume the project's repository name is `get-started`.

```bash
kedro new --starter=pandas-iris
```

### Project directory structure

This example project illustrates a convenient starting point and some best-practices. It follows the default Kedro project template and uses folders to store datasets, notebooks, configuration and source code. When you create your own projects, you can adapt the folder structure if you need to.

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
    ├── .ipython        # IPython startup scripts
    └── pyproject.toml  # Identifies the project root and [contains configuration information](https://kedro.readthedocs.io/en/latest/11_faq/02_architecture_overview.html#kedro-yml)
```

#### `conf/`

Within the `conf` folder, there are two subfolders for storing configuration information: `base` and `local`.

##### `conf/base/`

For project-specific settings to share across different installations (for example, with different users) you should use the `base` subfolder of `conf`.

The folder contains three files for the example, but you can add others as you require:

-   `catalog.yml` - [Configures the Data Catalog](../05_data/01_data_catalog.md#using-the-data-catalog-within-kedro-configuration) with the file paths and load/save configuration required for different datasets
-   `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging
-   `parameters.yml` - Allows you to define parameters for machine learning experiments e.g. train / test split and number of iterations

##### `conf/local/`

The `local` subfolder of `conf` is used for **settings that should not be shared**, such as access credentials, custom editor configuration, personal IDE configuration and other sensitive or personal content. It is specific to user and installation. The contents of `conf/local/` is ignored by `git` (through inclusion in `.gitignore`).


By default, when Kedro creates `conf/local` folder, it is empty. However, Kedro creates `credentials.yml` in `conf/base/` for use as an example. Before you populate and use the file, **you should first move it to `conf/local/`**.

#### `data`

The `data` folder contains a number of subfolders to store project data. We recommend that you put raw data into `raw` and move processed data to other subfolders according to [data engineering convention](../12_faq/01_faq.md#what-is-data-engineering-convention).

The example project has a single file, `iris.csv`, that contains the Iris dataset. The subfolders of `data` are ignored by `git` through inclusion in `.gitignore` since data is more frequently stored elsewhere, such as a in an S3 bucket. However, if you are familiar with [`.gitignore`](https://help.github.com/en/github/using-git/ignoring-files) you can edit it, if you are confident that you need to manage your data in `git`.

#### `src`

This subfolder contains the project's source code. It contains 2 subfolders:

-   `get_started/` This is the Python package for your project
-   `tests/` The subfolder for unit tests for your project. Projects are preconfigured to run tests using `pytest` when you call `kedro test` from the project's root directory

### What best practice should I follow to avoid leaking confidential data?

* Avoid committing data to version control.
* Avoid committing data to notebook output cells (data can easily sneak into notebooks when you don't delete output cells).
* Don't commit sensitive results or plots to version control (in notebooks or otherwise).
* Don't commit credentials in `conf/`. Only the `conf/local/` folder should be used for sensitive information like access credentials. To add credentials, please refer to the `conf/base/credentials.yml` file in the project template.
* By default any file inside the `conf/` folder (and its subfolders) containing `credentials` in its name will be ignored via `.gitignore` and not committed to your git repository.
* To describe where your colleagues can access the credentials, you may edit the `README.md` to provide instructions.


## Run the example project

Once you have created the project, to run project-specific Kedro commands, you need to navigate to the directory in which it has been created.

Call `kedro install` to install the project's dependencies. Next, call `kedro run`:

```bash
cd getting-started
kedro install
kedro run
```

When the command completes, you should see a log message similar to the following in your console:

```bash
    2019-02-13 16:59:26,293 - kedro.runner.sequential_runner - INFO - Completed 4 out of 4 tasks
    2019-02-13 16:59:26,293 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```

## Under the hood: Pipelines and nodes

The example project contains two modular pipelines:

- A `data_engineering` pipeline (`src/get_started/pipelines/data_engineering/pipeline.py`) responsible for splitting the data into training and testing samples

- A `data_science` pipeline (`src/get_started/pipelines/data_science/pipeline.py`) responsible for model training, predictions and accuracy-reporting


**Data engineering node**

This is the data engineering node function within `src/get_started/pipelines/data_engineering/nodes.py`:

```eval_rst
+-----------------+----------------------------------------------------------------+--------------------------+
| Node            | Description                                                    | Node Function Name       |
+=================+================================================================+==========================+
| Split data      | Splits the example                                             | :code:`split_data`       |
|                 | `Iris dataset <https://archive.ics.uci.edu/ml/datasets/iris>`_ |                          |
|                 | into train and test samples                                    |                          |
+-----------------+----------------------------------------------------------------+--------------------------+
```

**Data science node**

These are the data science node functions within `pipelines/data_science/nodes.py`:

```eval_rst
+-----------------+----------------------------------------------------------------+--------------------------+
| Node            | Description                                                    | Node Function Name       |
+=================+================================================================+==========================+
| Train model     | Trains a simple multi-class logistic regression model          | :code:`train_model`      |
+-----------------+----------------------------------------------------------------+--------------------------+
| Predict         | Makes class predictions given a pre-trained model and a test   | :code:`predict`          |
|                 | set                                                            |                          |
+-----------------+----------------------------------------------------------------+--------------------------+
| Report accuracy | Reports the accuracy of the predictions performed by the       | :code:`report_accuracy`  |
|                 | previous node                                                  |                          |
+-----------------+----------------------------------------------------------------+--------------------------+
```


The file `src/hooks.py` creates and collates the project's modular pipelines into a single pipeline, resolving node execution order from the input and output data dependencies between the nodes.
