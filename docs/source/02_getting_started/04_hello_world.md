# A "Hello World" example

To learn how basic Kedro projects work, you can [create a project interactively](./03_new_project.md#create-a-new-project-interactively) and explore it as you read this section. Feel free to name your project as you like, but this guide will assume the project is named `getting-started`.

Be sure to enter `Y` to include Kedro's example so your new project template contains the well-known [Iris dataset](https://archive.ics.uci.edu/ml/datasets/iris), to get you started.

The Iris dataset, generated in 1936 by the British statistician and biologist Ronald Fisher, is a simple, but frequently-referenced dataset. It contains 150 samples in total, comprising 50 samples of 3 different species of Iris plant (Iris Setosa, Iris Versicolour and Iris Virginica). For each sample, the flower measurements are recorded for the sepal length, sepal width, petal length and petal width.

![](images/iris_measurements.png)

Classification is a method, within the context of machine learning, to determine what group some object belongs to based on known categorisation of similar objects.

The Iris dataset can be used by a machine learning model to illustrate classification. The classification algorithm, once trained on data with known values of species, takes an input of sepal and petal measurements, and compares them to the values it has stored from its training data. It will then output a predictive classification of the Iris species.


## Project directory structure

The project directory will be structured as shown. You are free to adapt the folder structure to your project's needs, but the example shows a convenient starting point and some best-practices:

```
getting-started     # Parent directory of the template
├── .gitignore      # Prevent staging of unnecessary files to git
├── kedro_cli.py    # A collection of Kedro command line interface (CLI) commands
├── .kedro.yml      # Path to discover project context
├── README.md       # Project README
├── .ipython        # IPython startup scripts
├── conf            # Project configuration files
├── data            # Local project data (not committed to version control)
├── docs            # Project documentation
├── logs            # Project output logs (not committed to version control)
├── notebooks       # Project related Jupyter notebooks
└── src             # Project source code
```

If you opted to include Kedro's built-in example when you [created the project](./03_new_project.md) then the `conf/`, `data/` and `src/` directories will be pre-populated with an example configuration, input data and Python source code respectively.

## Project source code

The project's source code can be found in the `src` directory. It contains 2 subfolders:

* `getting_started/` - this is the Python package for your project:

	* `pipelines/data_engineering/nodes.py` and `pipelines/data_science/nodes.py`- Example node functions, which perform the actual operations on the data (more on this in the [Example pipeline](04_hello_world.md#example-pipeline) below)
	* `pipelines/data_engineering/pipeline.py` and `pipelines/data_science/pipeline.py` - Where each individual pipeline is created from the above nodes to form the business logic flow
	* `pipeline.py` - Where the project's main pipelines are collated and named
	* `run.py` - The main entry point of the project, which brings all the components together and runs the pipeline

* `tests/`: This is where you should keep the project unit tests. Newly generated projects are preconfigured to run these tests using `pytest`. To kick off project testing, simply run the following from the project's root directory:

```bash
kedro test
```

### Writing code

Use the `notebooks` folder for experimental code and move the code to `src/` as it develops.

## Project components

A `kedro` project consists of the following main components:

```eval_rst
+--------------+-----------------------------------------------------------------------------+
| Component    | Description                                                                 |
+==============+=============================================================================+
| Data Catalog | A collection of datasets that can be used to form the data pipeline.        |
|              | Each dataset provides :code:`load` and :code:`save` capabilities for        |
|              | a specific data type, e.g. :code:`pandas.CSVDataSet` loads and saves data   |
|              | to a CSV file.                                                              |
+--------------+-----------------------------------------------------------------------------+
| Pipeline     | A collection of nodes. A pipeline takes care of node dependencies           |
|              | and execution order.                                                        |
+--------------+-----------------------------------------------------------------------------+
| Node         | A Python function which executes some business logic, e.g. data             |
|              | cleaning, dropping columns, validation, model training, scoring, etc.       |
+--------------+-----------------------------------------------------------------------------+
| Runner       | An object that runs the :code:`kedro` pipeline using the specified          |
|              | data catalog. Currently :code:`kedro` supports 2 runner types:              |
|              | :code:`SequentialRunner` and :code:`ParallelRunner`.                        |
+--------------+-----------------------------------------------------------------------------+
```


## Data

You can store data under the appropriate layer in the `data` folder. We recommend that all raw data should go into `raw` and processed data should move to other layers according to [data engineering convention](../06_resources/01_faq.md#what-is-data-engineering-convention).

## Example pipeline

The `getting-started` project contains two pipelines: a `data_engineering` pipeline and `data_science` pipeline, found in `src/getting_started/pipelines`, with relevant example node functions pertaining to each of them. The following data-engineering nodes are provided in `src/getting_started/pipelines/data_engineering/nodes.py`:
```eval_rst
+-----------------+----------------------------------------------------------------+--------------------------+
| Node            | Description                                                    | Node Function Name       |
+=================+================================================================+==========================+
| Split data      | Splits the example                                             | :code:`split_data`       |
|                 | `Iris dataset <https://archive.ics.uci.edu/ml/datasets/iris>`_ |                          |
|                 | into train and test samples                                    |                          |
+-----------------+----------------------------------------------------------------+--------------------------+
```

As well as data-science nodes in `src/getting_started/pipelines/data_science/nodes.py`:
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

Node execution order is determined by resolving the input and output data dependencies between the nodes and *not* by the order in which the nodes were passed into the pipeline.

## Configuration

There are two default folders for adding configuration - `conf/base/` and `conf/local/`:

* `conf/base/` - Used for project-specific configuration
* `conf/local/` - Used for access credentials, personal IDE configuration or other sensitive / personal content

### Project-specific configuration

There are three files used for project-specific configuration:

* `catalog.yml` - The Data Catalog allows you to define the file paths and loading / saving configuration required for different datasets
* `logging.yml` - Uses Python's default [`logging`](https://docs.python.org/3/library/logging.html) library to set up logging
* `parameters.yml` - Allows you to define parameters for machine learning experiments e.g. train / test split and number of iterations

### Sensitive or personal configuration

As we described above, any access credentials, personal IDE configuration or other sensitive and personal content should be stored in `conf/local/`. By default, `credentials.yml` is generated in `conf/base/` (because `conf/local/` is ignored by `git`) and to populate and use the file, you should first move it to `conf/local/`. Further safeguards for preventing sensitive information from being leaked onto `git` are discussed in the [FAQs](../06_resources/01_faq.md#what-best-practice-should-i-follow-to-avoid-leaking-confidential-data).


## Running the example

In order to run the `getting-started` project, simply execute the following from the root project directory:

```bash
kedro run
```

This command calls the `run()` method on the `ProjectContext` class defined in `src/getting_started/run.py`, which in turn does the following:

1. Instantiates `ProjectContext` class:
    * Reads relevant configuration
    * Configures Python `logging`
    * Instantiates the `DataCatalog` and feeds a dictionary containing `parameters` config
2. Instantiates the pipeline
3. Instantiates the `SequentialRunner` and runs it by passing the following arguments:
    * `Pipeline` object
    * `DataCatalog` object

Upon successful completion, you should see the following log message in your console:

```
2019-02-13 16:59:26,293 - kedro.runner.sequential_runner - INFO - Completed 4 out of 4 tasks
2019-02-13 16:59:26,293 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```

## Summary
Congratulations! In this chapter you have set up Kedro and used it to create a first example project, which has illustrated the basic concepts of using nodes to form a pipeline, a Data Catalog and the project configuration. This example uses a simple and familiar dataset, to keep your first experience very basic and easy to follow. In the next chapter, we will revisit the core concepts in more detail and walk through a more complex example.
