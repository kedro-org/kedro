# Create a pipeline

This section covers the third part of the standard Kedro development workflow, and covers the following:

* How to create the data transformation steps as Python functions
* How to add a function to make a [Keddro node](../resources/glossary.md#node) 
* How to construct a [Kedro pipeline](../resources/glossary.md#pipeline) as a set of nodes

## Data processing pipeline

You previously registered the raw datasets for your Kedro project, so you can now create nodes to pre-process two of the datasets, companies.csv and shuttles.xlsx, to prepare the data for modelling.

### Generate a new pipeline template

> If you are using the tutorial created by the spaceflights starter, you can omit this command, but it's worth reviewing the files associated with the `data_processing` pipeline as described below.

In the terminal, run the following command to generate a new pipeline for data processing:

```bash
kedro pipeline create data_processing
```

This command generates all the files you need for the pipeline:

* Two python files: `nodes.py` (for the node functions that form the data processing) and `pipeline.py` (to build the pipeline) within `src/kedro_tutorial/pipelines/data_processing` pipeline
* A yaml file: `conf/base/parameters/data_processing.yml` to define the parameters used when running the pipeline
* A folder for test code: `src/tests/pipelines/data_processing` 
* `__init__.py` files in the required folders to ensure that the pipeline can be imported by Python

```bash

├── README.md
├── conf
│   └── base
│       └── parameters
│           └── data_processing.yml
└── src
    ├── kedro_tutorial
    │   ├── __init__.py
    │   └── pipelines
    │       ├── __init__.py
    │       └── data_processing
    │           ├── README.md
    │           ├── __init__.py
    │           ├── nodes.py
    │           └── pipeline.py
    └── tests
        ├── __init__.py
        └── pipelines
            ├── __init__.py
            └── data_processing
                ├── __init__.py
                └── test_pipeline.py
```

### Add node functions

> If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste, but it's worth opening `src/kedro_tutorial/pipelines/data_processing/nodes.py` to inspect the contents.

Open `src/kedro_tutorial/pipelines/data_processing/nodes.py` and add the code below, which provides two functions (`preprocess_companies` and `preprocess_shuttles`) that each take a raw DataFrame as input, convert the data in several columns to different types, and output a DataFrame containing the pre-processed data:

<details>
<summary><b>Click to expand</b></summary>

```python
import pandas as pd


def _is_true(x: pd.Series) -> pd.Series:
    return x == "t"


def _parse_percentage(x: pd.Series) -> pd.Series:
    x = x.str.replace("%", "")
    x = x.astype(float) / 100
    return x


def _parse_money(x: pd.Series) -> pd.Series:
    x = x.str.replace("$", "").str.replace(",", "")
    x = x.astype(float)
    return x


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for companies.

    Args:
        companies: Raw data.
    Returns:
        Preprocessed data, with `company_rating` converted to a float and
        `iata_approved` converted to boolean.
    """
    companies["iata_approved"] = _is_true(companies["iata_approved"])
    companies["company_rating"] = _parse_percentage(companies["company_rating"])
    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    """Preprocesses the data for shuttles.

    Args:
        shuttles: Raw data.
    Returns:
        Preprocessed data, with `price` converted to a float and `d_check_complete`,
        `moon_clearance_complete` converted to boolean.
    """
    shuttles["d_check_complete"] = _is_true(shuttles["d_check_complete"])
    shuttles["moon_clearance_complete"] = _is_true(shuttles["moon_clearance_complete"])
    shuttles["price"] = _parse_money(shuttles["price"])
    return shuttles
```

</details>

### Assemble nodes into the data processing pipeline

The next steps are to create a [node](../resources/glossary.md#node) for each function, and to create a [modular pipeline](../resources/glossary.md#modular-pipeline) for data processing:

> If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste, but it's worth reviewing the code in `src/kedro_tutorial/pipelines/data_processing/pipeline.py`.

Add the following to `src/kedro_tutorial/pipelines/data_processing/pipeline.py`, so the `create_pipeline()` function looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```python
def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocess_companies_node",
            ),
            node(
                func=preprocess_shuttles,
                inputs="shuttles",
                outputs="preprocessed_shuttles",
                name="preprocess_shuttles_node",
            ),
        ]
    )
```

Be sure to import `node`, and your functions by adding them to the beginning of `pipeline.py`:

```python
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import preprocess_companies, preprocess_shuttles
```
</details>


Note that `companies` and `shuttles` refer to the datasets defined in `conf/base/catalog.yml`. These are inputs to the `preprocess_companies` and `preprocess_shuttles` functions. The named node inputs (and outputs) are used by the pipeline to determine interdependencies between the nodes, and hence, their execution order.


### Test the example

Run the following command in your terminal window to test the node named `preprocess_companies_node`:

```bash
kedro run --node=preprocess_companies_node
```

You should see output similar to the below:

```bash
[08/09/22 16:43:10] INFO     Kedro project kedro-tutorial                                         session.py:346
[08/09/22 16:43:11] INFO     Loading data from 'companies' (CSVDataSet)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataSet)...      data_catalog.py:382
                    INFO     Completed 1 out of 1 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataSet)...   data_catalog.py:343

```

To test the entire data processing pipeline:

```bash
kedro run
```

You should see output similar to the following:

```bash
[08/09/22 16:45:46] INFO     Kedro project kedro-tutorial                                         session.py:346
                    INFO     Loading data from 'companies' (CSVDataSet)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataSet)...      data_catalog.py:382
                    INFO     Completed 1 out of 2 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'shuttles' (ExcelDataSet)...                  data_catalog.py:343
[08/09/22 16:46:08] INFO     Running node: preprocess_shuttles_node: preprocess_shuttles([shuttles]) node.py:327
                             -> [preprocessed_shuttles]
                    INFO     Saving data to 'preprocessed_shuttles' (MemoryDataSet)...       data_catalog.py:382
                    INFO     Completed 2 out of 2 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataSet)...   data_catalog.py:343
                    INFO     Loading data from 'preprocessed_shuttles' (MemoryDataSet)...    data_catalog.py:343

```

### Optional: visualise the pipeline

The next section of this tutorial covers visualisation in greater detail, but you can now use Kedro-Viz to show your `data_processing` pipeline. In your terminal type the following:

```bash
kedro viz
```

This command automatically opens a browser tab to serve the visualisation at http://127.0.0.1:4141/:

![simple_pipeline](../meta/images/simple_pipeline.png)

To exit the visualisation, close the browser tab. To regain control of the terminal, enter `Ctrl+C` or `Cmd+C`.

### Optional: persist pre-processed data

Each of the nodes outputs a new dataset (`preprocessed_companies` and `preprocessed_shuttles`). 

When Kedro runs the pipeline, it determines that neither datasets is registered in the data catalog so it stores these _ephemeral datasets_ in memory as Python objects using the [MemoryDataSet](/kedro.io.MemoryDataSet) class. Once all nodes that depend on an ephemeral dataset have executed, the dataset is cleared and the memory is released by the Python garbage collector. 

If you prefer to persist the preprocessed data, add the following to `conf/base/catalog.yml` (If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste):

```yaml
preprocessed_companies:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/preprocessed_companies.pq

preprocessed_shuttles:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/preprocessed_shuttles.pq
```

Adding the data to the catalog declares explicitly that Kedro should use [pandas.ParquetDataSet](/kedro.extras.datasets.pandas.ParquetDataSet) instead of [`MemoryDataSet`](/kedro.io.MemoryDataSet). The [Data Catalog](../resources/glossary.md#data-catalog) automatically saves the datasets (in Parquet format) to the path specified next time the pipeline is run. There is no need to change any code in your preprocessing functions to accommodate this change.

We chose the [Apache Parquet](https://github.com/apache/parquet-format) format for working with processed and typed data. We recommend getting your data out of CSV as soon as possible. Parquet supports things like compression, partitioning and types out of the box. Whilst you lose the ability to view the file as text, the benefits greatly outweigh the drawbacks.

### Extend the data processing pipeline

The next step in the tutorial is to add another node for a function that joins together the three DataFrames into a single model input table. You'll add some code for a function and node called `create_model_input_table`, which Kedro processes as follows:

* Kedro uses the `preprocessed_shuttles`, `preprocessed_companies`, and `reviews` datasets as inputs
* Kedro saves the output as a dataset called `model_input_table`

> If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste, but it's worth reviewing the `create_model_input_table` code in `nodes.py` and `pipeline.py` .

First, add the `create_model_input_table()` function from the snippet below to `src/kedro_tutorial/pipelines/data_processing/nodes.py`.

<details>
<summary><b>Click to expand</b></summary>

```python
def create_model_input_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:
    """Combines all data to create a model input table.

    Args:
        shuttles: Preprocessed data for shuttles.
        companies: Preprocessed data for companies.
        reviews: Raw data for reviews.
    Returns:
        model input table.

    """
    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")
    model_input_table = rated_shuttles.merge(
        companies, left_on="company_id", right_on="id"
    )
    model_input_table = model_input_table.dropna()
    return model_input_table
```

</details>

Add an import statement for `create_model_input_table` at the top of `src/kedro_tutorial/pipelines/data_processing/pipeline.py` and add the code below to include the new node in the pipeline:

```python
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles
```

```python
node(
    func=create_model_input_table,
    inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
    outputs="model_input_table",
    name="create_model_input_table_node",
),
```


### Optional: persist the model input table

If you want the model input table data to be saved to file rather than used in-memory, add an entry to `conf/base/catalog.yml`. (If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste):

```yaml
model_input_table:
  type: pandas.ParquetDataSet
  filepath: data/03_primary/model_input_table.pq
```

### Test the example

To test the progress of the example:

```bash
kedro run
```

You should see output similar to the following:

```bash
[08/09/22 17:00:54] INFO     Kedro project kedro-tutorial                                         session.py:346
[08/09/22 17:01:10] INFO     Reached after_catalog_created hook                                     plugin.py:17
                    INFO     Loading data from 'companies' (CSVDataSet)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataSet)...      data_catalog.py:382
                    INFO     Completed 1 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'shuttles' (ExcelDataSet)...                  data_catalog.py:343
[08/09/22 17:01:25] INFO     Running node: preprocess_shuttles_node: preprocess_shuttles([shuttles]) node.py:327
                             -> [preprocessed_shuttles]

                    INFO     Saving data to 'preprocessed_shuttles' (MemoryDataSet)...       data_catalog.py:382
                    INFO     Completed 2 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'preprocessed_shuttles' (MemoryDataSet)...    data_catalog.py:343
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataSet)...   data_catalog.py:343
                    INFO     Loading data from 'reviews' (CSVDataSet)...                     data_catalog.py:343
                    INFO     Running node: create_model_input_table_node:                            node.py:327
                             create_model_input_table([preprocessed_shuttles,preprocessed_companies,
                             reviews]) -> [model_input_table]
[08/09/22 17:01:28] INFO     Saving data to 'model_input_table' (MemoryDataSet)...           data_catalog.py:382
[08/09/22 17:01:29] INFO     Completed 3 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'model_input_table' (MemoryDataSet)...        data_catalog.py:343
```


## Data science pipeline

We have created a modular pipeline for data processing, which merges three input datasets to create a model input table. Now we will create the data science pipeline for price prediction, which uses the [`LinearRegression`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) implementation from the [scikit-learn](https://scikit-learn.org/stable/) library.

### Create the data science pipeline

Run the following command to create the `data_science` pipeline:
```bash
kedro pipeline create data_science
```

Add the following code to the `src/kedro_tutorial/pipelines/data_science/nodes.py` file:

<details>
<summary><b>Click to expand</b></summary>

```python
import logging
from typing import Dict, Tuple

import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


def split_data(data: pd.DataFrame, parameters: Dict) -> Tuple:
    """Splits data into features and targets training and test sets.

    Args:
        data: Data containing features and target.
        parameters: Parameters defined in parameters/data_science.yml.
    Returns:
        Split data.
    """
    X = data[parameters["features"]]
    y = data["price"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )
    return X_train, X_test, y_train, y_test


def train_model(X_train: pd.DataFrame, y_train: pd.Series) -> LinearRegression:
    """Trains the linear regression model.

    Args:
        X_train: Training data of independent features.
        y_train: Training data for price.

    Returns:
        Trained model.
    """
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(
    regressor: LinearRegression, X_test: pd.DataFrame, y_test: pd.Series
):
    """Calculates and logs the coefficient of determination.

    Args:
        regressor: Trained model.
        X_test: Testing data of independent features.
        y_test: Testing data for price.
    """
    y_pred = regressor.predict(X_test)
    score = r2_score(y_test, y_pred)
    logger = logging.getLogger(__name__)
    logger.info("Model has a coefficient R^2 of %.3f on test data.", score)
```

</details>

### Configure the input parameters

Add the following to `conf/base/parameters/data_science.yml`:

```yaml
model_options:
  test_size: 0.2
  random_state: 3
  features:
    - engines
    - passenger_capacity
    - crew
    - d_check_complete
    - moon_clearance_complete
    - iata_approved
    - company_rating
    - review_scores_rating
```

These are the parameters fed into the `DataCatalog` when the pipeline is executed. More information about [parameters](../kedro_project_setup/configuration.md#parameters) is available in later documentation for advanced usage. Here, the parameters `test_size` and `random_state` are used as part of the train-test split, and `features` gives the names of columns in the model input table to use as features.

### Assemble the data science pipeline

To create a modular pipeline for the price prediction model, add the following to the top of `src/kedro_tutorial/pipelines/data_science/pipeline.py`:

```python
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import evaluate_model, split_data, train_model


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(
                func=split_data,
                inputs=["model_input_table", "params:model_options"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
                name="split_data_node",
            ),
            node(
                func=train_model,
                inputs=["X_train", "y_train"],
                outputs="regressor",
                name="train_model_node",
            ),
            node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs=None,
                name="evaluate_model_node",
            ),
        ]
    )
```

### Register the dataset

The next step is to register the dataset that will save the trained model, by adding the following definition to `conf/base/catalog.yml`:

```yaml
regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor.pickle
  versioned: true
```

Versioning is enabled for `regressor`, which means that the pickled output of the `regressor` will be versioned and saved every time the pipeline is run. This allows us to keep the history of the models built using this pipeline. Further details can be found in the [Versioning section](../data/kedro_io.md#versioning).

### Test the pipelines

Execute the default pipeline:

```bash
kedro run
```

You should see output similar to the following:

<details>
<summary><b>Click to expand</b></summary>

```bash
[08/09/22 16:56:00] INFO     Kedro project kedro-tutorial                                         session.py:346
                    INFO     Loading data from 'companies' (CSVDataSet)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataSet)...      data_catalog.py:382
                    INFO     Completed 1 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'shuttles' (ExcelDataSet)...                  data_catalog.py:343
[08/09/22 16:56:15] INFO     Running node: preprocess_shuttles_node: preprocess_shuttles([shuttles]) node.py:327
                             -> [preprocessed_shuttles]
                    INFO     Saving data to 'preprocessed_shuttles' (MemoryDataSet)...       data_catalog.py:382
                    INFO     Completed 2 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'preprocessed_shuttles' (MemoryDataSet)...    data_catalog.py:343
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataSet)...   data_catalog.py:343
                    INFO     Loading data from 'reviews' (CSVDataSet)...                     data_catalog.py:343
                    INFO     Running node: create_model_input_table_node:                            node.py:327
                             create_model_input_table([preprocessed_shuttles,preprocessed_companies,
                             reviews]) -> [model_input_table]
[08/09/22 16:56:18] INFO     Saving data to 'model_input_table' (MemoryDataSet)...           data_catalog.py:382
[08/09/22 16:56:19] INFO     Completed 3 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'model_input_table' (MemoryDataSet)...        data_catalog.py:343
                    INFO     Loading data from 'params:model_options' (MemoryDataSet)...     data_catalog.py:343
                    INFO     Running node: split_data_node:                                          node.py:327
                             split_data([model_input_table,params:model_options]) ->
                             [X_train,X_test,y_train,y_test]
                    INFO     Saving data to 'X_train' (MemoryDataSet)...                     data_catalog.py:382
                    INFO     Saving data to 'X_test' (MemoryDataSet)...                      data_catalog.py:382
                    INFO     Saving data to 'y_train' (MemoryDataSet)...                     data_catalog.py:382
                    INFO     Saving data to 'y_test' (MemoryDataSet)...                      data_catalog.py:382
                    INFO     Completed 4 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'X_train' (MemoryDataSet)...                  data_catalog.py:343
                    INFO     Loading data from 'y_train' (MemoryDataSet)...                  data_catalog.py:343
                    INFO     Running node: train_model_node: train_model([X_train,y_train]) ->       node.py:327
                             [regressor]
[08/09/22 16:56:20] INFO     Saving data to 'regressor' (PickleDataSet)...                   data_catalog.py:382
                    INFO     Completed 5 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'regressor' (PickleDataSet)...                data_catalog.py:343
                    INFO     Loading data from 'X_test' (MemoryDataSet)...                   data_catalog.py:343
                    INFO     Loading data from 'y_test' (MemoryDataSet)...                   data_catalog.py:343
                    INFO     Running node: evaluate_model_node:                                      node.py:327
                             evaluate_model([regressor,X_test,y_test]) -> None
                    INFO     Model has a coefficient R^2 of 0.462 on test data.                      nodes.py:55
                    INFO     Completed 6 out of 6 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
```

</details>

## Kedro runners

There are three different Kedro runners that can run the pipeline:

* `SequentialRunner` - runs your nodes sequentially; once a node has completed its task then the next one starts.
* `ParallelRunner` - runs your nodes in parallel; independent nodes are able to run at the same time, which is more efficient when there are independent branches in your pipeline and allows you to take advantage of multiple CPU cores.
* `ThreadRunner` - runs your nodes in parallel, similarly to `ParallelRunner`, but uses multithreading instead of multiprocessing.

By default, Kedro uses a `SequentialRunner`, which is instantiated when you execute `kedro run` from the command line. If you decide to use `ParallelRunner`, `ThreadRunner` or a custom runner, you can do so through the `--runner` flag as follows:

```bash
kedro run --runner=ParallelRunner
kedro run --runner=ThreadRunner
kedro run --runner=module.path.to.my.runner
```

```{note}
`ParallelRunner` performs task parallelisation via multiprocessing. `ThreadRunner` is intended for use with remote execution engines such as [Spark](../tools_integration/pyspark.md) and [Dask](https://github.com/kedro-org/kedro/blob/develop/kedro/extras/datasets/dask/parquet_dataset.py). You can find out more about the runners Kedro provides, and how to create your own, in the [pipeline documentation about runners](../nodes_and_pipelines/run_a_pipeline.md).
```

You can find out more about the runners Kedro provides, and how to create your own, in the [pipeline documentation about runners](../nodes_and_pipelines/run_a_pipeline.md).

## Slice a pipeline

In some cases you may want to run just part of a pipeline. For example, you may need to only run the data science pipeline to tune the hyperparameters of the price prediction model and skip data processing execution. You can 'slice' the pipeline and specify just the portion you want to run by using the `--pipeline` command line option. For example, to only run the pipeline named `data_science` (as labelled automatically in `register_pipelines`), execute the following command:

```bash
kedro run --pipeline=data_science
```

See the [pipeline slicing documentation](../nodes_and_pipelines/slice_a_pipeline.md) and the ``kedro run`` [CLI documentation](../development/commands_reference.md#modifying-a-kedro-run) for other ways to run sections of your pipeline.

```{warning}
To successfully run the pipeline, you need to make sure that all required input datasets already exist, otherwise you may get an error similar to this:
```

```bash
kedro run --pipeline=data_science

2019-10-04 12:36:12,135 - root - INFO - ** Kedro project kedro-tutorial
2019-10-04 12:36:12,158 - kedro.io.data_catalog - INFO - Loading data from `model_input_table` (CSVDataSet)...
2019-10-04 12:36:12,158 - kedro.runner.sequential_runner - WARNING - There are 3 nodes that have not run.
You can resume the pipeline run with the following command:
kedro run
Traceback (most recent call last):
  ...
  File "pandas/_libs/parsers.pyx", line 382, in pandas._libs.parsers.TextReader.__cinit__
  File "pandas/_libs/parsers.pyx", line 689, in pandas._libs.parsers.TextReader._setup_parser_source
FileNotFoundError: [Errno 2] File b'data/03_primary/model_input_table.csv' does not exist: b'data/03_primary/model_input_table.csv'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
    raise DataSetError(message) from exc
kedro.io.core.DataSetError: Failed while loading data from data set CSVDataSet(filepath=data/03_primary/model_input_table.csv, save_args={'index': False}).
[Errno 2] File b'data/03_primary/model_input_table.csv' does not exist: b'data/03_primary/model_input_table.csv'
```
