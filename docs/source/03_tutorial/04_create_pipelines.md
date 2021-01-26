# Create a pipeline

This section covers the third part of the [standard development workflow](./01_spaceflights_tutorial.md#kedro-project-development-workflow), and covers the following:

* How to create each [node](../13_resources/02_glossary.md#node) required by the example
* How to set up a [pipeline](../13_resources/02_glossary.md#pipeline)


## Data engineering pipeline

You previously registered the raw datasets for your Kedro project, so you can now create nodes to pre-process two of the datasets, [companies.csv](https://github.com/quantumblacklabs/kedro-starters/blob/master/spaceflights/%7B%7B%20cookiecutter.repo_name%20%7D%7D/data/01_raw/companies.csv) and [shuttles.xlsx](https://github.com/quantumblacklabs/kedro-starters/blob/master/spaceflights/%7B%7B%20cookiecutter.repo_name%20%7D%7D/data/01_raw/shuttles.xlsx), to prepare the data for modelling.

### Node functions

Create a file in the following location, adding the subfolders too if necessary `src/kedro_tutorial/pipelines/data_engineering/nodes.py`.

Add the code below, which provides two functions (`preprocess_companies` and `preprocess_shuttles`) that each input a raw dataframe and output a dataframe containing pre-processed data:

<details>
<summary><b>Click to expand</b></summary>

```python
import pandas as pd


def _is_true(x):
    return x == "t"


def _parse_percentage(x):
    if isinstance(x, str):
        return float(x.replace("%", "")) / 100
    return float("NaN")


def _parse_money(x):
    return float(x.replace("$", "").replace(",", ""))


def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the data for companies.

        Args:
            companies: Source data.
        Returns:
            Preprocessed data.

    """

    companies["iata_approved"] = companies["iata_approved"].apply(_is_true)

    companies["company_rating"] = companies["company_rating"].apply(_parse_percentage)

    return companies


def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    """Preprocess the data for shuttles.

        Args:
            shuttles: Source data.
        Returns:
            Preprocessed data.

    """
    shuttles["d_check_complete"] = shuttles["d_check_complete"].apply(_is_true)

    shuttles["moon_clearance_complete"] = shuttles["moon_clearance_complete"].apply(
        _is_true
    )

    shuttles["price"] = shuttles["price"].apply(_parse_money)

    return shuttles
```
</details>

### Assemble nodes into the data engineering pipeline


The next steps are to create a [node](../13_resources/02_glossary.md#node) for each function, and to create a [modular pipeline](../13_resources/02_glossary.md#modular-pipeline) for [data engineering](../13_resources/02_glossary.md#data-engineering-vs-data-science):

Add the following to `src/kedro_tutorial/pipelines/data_engineering/pipeline.py`, so the `create_pipeline()` function looks as follows:

<details>
<summary><b>Click to expand</b></summary>

```python
def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=preprocess_companies,
                inputs="companies",
                outputs="preprocessed_companies",
                name="preprocessing_companies",
            ),
            node(
                func=preprocess_shuttles,
                inputs="shuttles",
                outputs="preprocessed_shuttles",
                name="preprocessing_shuttles",
            ),
        ]
    )
```
</details>

>Note: `companies` and `shuttles` refer to the datasets defined in `conf/base/catalog.yml`. These are inputs to the `preprocess_companies` and `preprocess_shuttles` functions. The named node inputs (and outputs) are used by the pipeline to determine interdependencies between the nodes, and hence, their execution order.

Be sure to import `node`, and your functions by adding them to the beginning of `pipeline.py`:

```python
from kedro.pipeline import node, Pipeline
from kedro_tutorial.pipelines.data_engineering.nodes import (
    preprocess_companies,
    preprocess_shuttles,
)
```

### Update the project pipeline

Now update the project's pipeline in `src/kedro_tutorial/hooks.py` to add the [modular pipeline](../13_resources/02_glossary.md#modular-pipeline) for [data engineering](../13_resources/02_glossary.md#data-engineering-vs-data-science):

<details>
<summary><b>Click to expand</b></summary>

```python
from typing import Dict

from kedro.framework.hooks import hook_impl
from kedro.pipeline import Pipeline

from kedro_tutorial.pipelines.data_engineering import pipeline as de


class ProjectHooks:
    @hook_impl
    def register_pipelines(self) -> Dict[str, Pipeline]:
        """Register the project's pipeline.

        Returns:
            A mapping from a pipeline name to a ``Pipeline`` object.

        """
        de_pipeline = de.create_pipeline()

        return {
            "de": de_pipeline,
            "__default__": de_pipeline,
        }


project_hooks = ProjectHooks()
```
</details>

### Test the example

Run the following command in your terminal window to test the `preprocessing_companies` node:

```bash
kedro run --node=preprocessing_companies
```

You should see output similar to the below:

```bash
2019-08-19 10:44:33,112 - root - INFO - ** Kedro project kedro-tutorial
2019-08-19 10:44:33,123 - kedro.io.data_catalog - INFO - Loading data from `companies` (CSVDataSet)...
2019-08-19 10:44:33,161 - kedro.pipeline.node - INFO - Running node: preprocessing_companies: preprocess_companies([companies]) -> [preprocessed_companies]
2019-08-19 10:44:33,206 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_companies` (MemoryDataSet)...
2019-08-19 10:44:33,471 - kedro.runner.sequential_runner - INFO - Completed 1 out of 1 tasks
2019-08-19 10:44:33,471 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.

```

To test the entire data engineering pipeline:

```bash
kedro run
```

You should see output similar to the following

```bash
kedro run

2019-08-19 10:50:39,950 - root - INFO - ** Kedro project kedro-tutorial
2019-08-19 10:50:39,957 - kedro.io.data_catalog - INFO - Loading data from `shuttles` (ExcelDataSet)...
2019-08-19 10:50:48,521 - kedro.pipeline.node - INFO - Running node: preprocessing_shuttles: preprocess_shuttles([shuttles]) -> [preprocessed_shuttles]
2019-08-19 10:50:48,587 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_shuttles` (MemoryDataSet)...
2019-08-19 10:50:49,133 - kedro.runner.sequential_runner - INFO - Completed 1 out of 2 tasks
2019-08-19 10:50:49,133 - kedro.io.data_catalog - INFO - Loading data from `companies` (CSVDataSet)...
2019-08-19 10:50:49,168 - kedro.pipeline.node - INFO - Running node: preprocessing_companies: preprocess_companies([companies]) -> [preprocessed_companies]
2019-08-19 10:50:49,212 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_companies` (MemoryDataSet)...
2019-08-19 10:50:49,458 - kedro.runner.sequential_runner - INFO - Completed 2 out of 2 tasks
2019-08-19 10:50:49,459 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.

```


### Persist pre-processed data

The nodes above each output a new dataset (`preprocessed_companies` and `preprocessed_shuttles`). When Kedro ran the pipeline, it determined that neither datasets had been registered in the data catalog (`conf/base/catalog.yml`). If a dataset is not registered, Kedro stores it in memory as a Python object using the [MemoryDataSet](/kedro.io.MemoryDataSet) class. Once all nodes depending on it have been executed, the `MemoryDataSet` is cleared and its memory released by the Python garbage collector.

You can persist the preprocessed data by adding the following to `conf/base/catalog.yml`:

```yaml
preprocessed_companies:
  type: pandas.CSVDataSet
  filepath: data/02_intermediate/preprocessed_companies.csv

preprocessed_shuttles:
  type: pandas.CSVDataSet
  filepath: data/02_intermediate/preprocessed_shuttles.csv
```

The code above declares explicitly that [pandas.CSVDataSet](/kedro.extras.datasets.pandas.CSVDataSet) should be used instead of [`MemoryDataSet`](/kedro.io.MemoryDataSet).


The [Data Catalog](../13_resources/02_glossary.md#data-catalog) will take care of saving the datasets automatically (in this case as CSV data) to the path specified next time the pipeline is run. There is no need to change any code in your preprocessing functions to accommodate this change.

In this tutorial, we chose `pandas.CSVDataSet` for its simplicity, but you can use any other available dataset implementation class, for example, a database table, cloud storage (like [AWS S3](https://aws.amazon.com/s3/), [Azure Blob Storage](https://azure.microsoft.com/en-gb/services/storage/blobs/), etc.) or others. If you cannot find the dataset implementation you need, you can implement your own [custom dataset](../07_extend_kedro/03_custom_datasets.md).

### Extend the data engineering pipeline

The next step in the tutorial is to add another node for a function to join together the three dataframes into a single master table. First, add the `create_master_table()` function from the snippet above to `src/kedro_tutorial/pipelines/data_engineering/nodes.py`.

<details>
<summary><b>Click to expand</b></summary>

```python

def create_master_table(
    shuttles: pd.DataFrame, companies: pd.DataFrame, reviews: pd.DataFrame
) -> pd.DataFrame:
    """Combines all data to create a master table.

        Args:
            shuttles: Preprocessed data for shuttles.
            companies: Preprocessed data for companies.
            reviews: Source data for reviews.
        Returns:
            Master table.

    """
    rated_shuttles = shuttles.merge(reviews, left_on="id", right_on="shuttle_id")

    with_companies = rated_shuttles.merge(
        companies, left_on="company_id", right_on="id"
    )

    master_table = with_companies.drop(["shuttle_id", "company_id"], axis=1)
    master_table = master_table.dropna()
    return master_table
```
</details>


Add the function to the data engineering pipeline in `src/kedro_tutorial/pipelines/data_engineering/pipeline.py` as a node:

```python
node(
    func=create_master_table,
    inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
    outputs="master_table",
    name="master_table",
),
```

The code above informs Kedro that the function `create_master_table` should be called with the data loaded from datasets `preprocessed_shuttles`, `preprocessed_companies`, and `reviews` and the output should be saved to dataset `master_table`.

Add an import statement for `create_master_table` at the top of the file:

```python
from kedro_tutorial.pipelines.data_engineering.nodes import (
    preprocess_companies,
    preprocess_shuttles,
    create_master_table,
)
```

If you want the master table data to be saved to file rather than used in-memory, add an entry to `conf/base/catalog.yml`:

```yaml
master_table:
  type: pandas.CSVDataSet
  filepath: data/03_primary/master_table.csv
```

### Test the example

To test the progress of the example:

```bash
kedro run
```

You should see output similar to the following:

```bash
2019-08-19 10:55:47,534 - root - INFO - ** Kedro project kedro-tutorial
2019-08-19 10:55:47,541 - kedro.io.data_catalog - INFO - Loading data from `shuttles` (ExcelDataSet)...
2019-08-19 10:55:55,670 - kedro.pipeline.node - INFO - Running node: preprocessing_shuttles: preprocess_shuttles([shuttles]) -> [preprocessed_shuttles]
2019-08-19 10:55:55,736 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_shuttles` (CSVDataSet)...
2019-08-19 10:55:56,284 - kedro.runner.sequential_runner - INFO - Completed 1 out of 3 tasks
2019-08-19 10:55:56,284 - kedro.io.data_catalog - INFO - Loading data from `companies` (CSVDataSet)...
2019-08-19 10:55:56,318 - kedro.pipeline.node - INFO - Running node: preprocessing_companies: preprocess_companies([companies]) -> [preprocessed_companies]
2019-08-19 10:55:56,361 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_companies` (CSVDataSet)...
2019-08-19 10:55:56,610 - kedro.runner.sequential_runner - INFO - Completed 2 out of 3 tasks
2019-08-19 10:55:56,610 - kedro.io.data_catalog - INFO - Loading data from `preprocessed_shuttles` (CSVDataSet)...
2019-08-19 10:55:56,715 - kedro.io.data_catalog - INFO - Loading data from `preprocessed_companies` (CSVDataSet)...
2019-08-19 10:55:56,750 - kedro.io.data_catalog - INFO - Loading data from `reviews` (CSVDataSet)...
2019-08-19 10:55:56,812 - kedro.pipeline.node - INFO - Running node: create_master_table([preprocessed_companies,preprocessed_shuttles,reviews]) -> [master_table]
2019-08-19 10:55:58,679 - kedro.io.data_catalog - INFO - Saving data to `master_table` (CSVDataSet)...
2019-08-19 10:56:09,991 - kedro.runner.sequential_runner - INFO - Completed 3 out of 3 tasks
2019-08-19 10:56:09,991 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```


## Data science pipeline

We have created a modular pipeline for data engineering, which merges three input datasets to create a master table. Now we will create the data science pipeline for price prediction, which uses a [`LinearRegression`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) implementation from the [scikit-learn](https://scikit-learn.org/stable/) library.

### Update dependencies
We now need to add `scikit-learn` to the project's dependencies. This is a slightly different process from the initial change we made early in the tutorial.

To **update** the project's dependencies, you should modify `src/requirements.in` to add the following. Note that you do not need to update `src/requirements.txt` as you did previously in the tutorial before you built the project's requirements with `kedro build-reqs`:


```text
scikit-learn==0.23.1
```

Then, re-run `kedro install` with a flag telling Kedro to recompile the requirements:

```bash
kedro install --build-reqs
```

You can find out more about [how to work with project dependencies](../04_kedro_project_setup/01_dependencies) in the Kedro project documentation.

### Create a data science node

Create a file in the following location, adding the subfolders too if necessary `src/kedro_tutorial/pipelines/data_science/nodes.py`. Add the following code to the file:

<details>
<summary><b>Click to expand</b></summary>

```python
import logging
from typing import Dict, List

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression
from sklearn.metrics import r2_score
from sklearn.model_selection import train_test_split


def split_data(data: pd.DataFrame, parameters: Dict) -> List:
    """Splits data into training and test sets.

        Args:
            data: Source data.
            parameters: Parameters defined in parameters.yml.

        Returns:
            A list containing split data.

    """
    X = data[
        [
            "engines",
            "passenger_capacity",
            "crew",
            "d_check_complete",
            "moon_clearance_complete",
        ]
    ].values
    y = data["price"].values
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=parameters["test_size"], random_state=parameters["random_state"]
    )

    return [X_train, X_test, y_train, y_test]


def train_model(X_train: np.ndarray, y_train: np.ndarray) -> LinearRegression:
    """Train the linear regression model.

        Args:
            X_train: Training data of independent features.
            y_train: Training data for price.

        Returns:
            Trained model.

    """
    regressor = LinearRegression()
    regressor.fit(X_train, y_train)
    return regressor


def evaluate_model(regressor: LinearRegression, X_test: np.ndarray, y_test: np.ndarray):
    """Calculate the coefficient of determination and log the result.

        Args:
            regressor: Trained model.
            X_test: Testing data of independent features.
            y_test: Testing data for price.

    """
    y_pred = regressor.predict(X_test)
    score = r2_score(y_test, y_pred)
    logger = logging.getLogger(__name__)
    logger.info("Model has a coefficient R^2 of %.3f.", score)
```

</details>


### Configure the input parameters

Add the following to `conf/base/parameters.yml`:

```yaml
test_size: 0.2
random_state: 3
```

These are the parameters fed into the `DataCatalog` when the pipeline is executed. More information about [parameters](../04_kedro_project_setup/02_configuration.md#Parameters) is available in later documentation for advanced usage.

### Register the dataset
The next step is to register the dataset that will save the trained model, by adding the following definition to `conf/base/catalog.yml`:

```yaml
regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor.pickle
  versioned: true
```

> *Note:* Versioning is enabled for `regressor`, which means that the pickled output of the `regressor` will be
> versioned and saved every time the pipeline is run. This allows us to keep the history of the models built using
> this pipeline. Further details can be found in the [Versioning](../05_data/02_kedro_io.md#versioning) section.

### Assemble the data science pipeline
To create a modular pipeline for the price prediction model, add the following to the top of `src/kedro_tutorial/pipelines/data_science/pipeline.py`:

```python
from kedro.pipeline import Pipeline, node

from kedro_tutorial.pipelines.data_science.nodes import (
    evaluate_model,
    split_data,
    train_model,
)
```

And add the following pipeline definition to the same file:

```python
def create_pipeline(**kwargs):
    return Pipeline(
        [
            node(
                func=split_data,
                inputs=["master_table", "parameters"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
            ),
            node(func=train_model, inputs=["X_train", "y_train"], outputs="regressor"),
            node(
                func=evaluate_model,
                inputs=["regressor", "X_test", "y_test"],
                outputs=None,
            ),
        ]
    )
```


### Update the project pipeline

Add the data science pipeline to the project by replacing the code in `register_pipelines` in `src/kedro_tutorial/hooks.py` with the following:

```python
def register_pipelines(self) -> Dict[str, Pipeline]:
    """Register the project's pipeline.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """
    de_pipeline = de.create_pipeline()
    ds_pipeline = ds.create_pipeline()

    return {
        "de": de_pipeline,
        "ds": ds_pipeline,
        "__default__": de_pipeline + ds_pipeline,
    }
```

Include the import at the top of the file:

```python
from kedro_tutorial.pipelines.data_science import pipeline as ds
```
The two modular pipelines are merged together into a project default pipeline by the `__default__` key used in `"__default__": de_pipeline + ds_pipeline`.
The `de_pipeline` will preprocess the data, and `ds_pipeline` will create features, train and evaluate the model.

> *Note:* The order in which you add the pipelines together is not significant and `ds_pipeline + de_pipeline` will result in the same pipeline, since Kedro automatically detects the correct execution order for all the nodes in the resulting pipeline.


### Test the pipelines
Execute the default pipeline:

```bash
kedro run
```
You should see output similar to the following:

<details>
<summary><b>Click to expand</b></summary>

```bash
kedro run

2019-08-19 10:51:46,501 - root - INFO - ** Kedro project kedro-tutorial
2019-08-19 10:51:46,510 - kedro.io.data_catalog - INFO - Loading data from `companies` (CSVDataSet)...
2019-08-19 10:51:46,547 - kedro.pipeline.node - INFO - Running node: preprocessing_companies: preprocess_companies([companies]) -> [preprocessed_companies]
2019-08-19 10:51:46,597 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_companies` (CSVDataSet)...
2019-08-19 10:51:46,906 - kedro.runner.sequential_runner - INFO - Completed 1 out of 6 tasks
2019-08-19 10:51:46,906 - kedro.io.data_catalog - INFO - Loading data from `shuttles` (ExcelDataSet)...
2019-08-19 10:51:55,324 - kedro.pipeline.node - INFO - Running node: preprocessing_shuttles: preprocess_shuttles([shuttles]) -> [preprocessed_shuttles]
2019-08-19 10:51:55,389 - kedro.io.data_catalog - INFO - Saving data to `preprocessed_shuttles` (CSVDataSet)...
2019-08-19 10:51:55,932 - kedro.runner.sequential_runner - INFO - Completed 2 out of 6 tasks
2019-08-19 10:51:55,932 - kedro.io.data_catalog - INFO - Loading data from `preprocessed_shuttles` (CSVDataSet)...
2019-08-19 10:51:56,042 - kedro.io.data_catalog - INFO - Loading data from `preprocessed_companies` (CSVDataSet)...
2019-08-19 10:51:56,078 - kedro.io.data_catalog - INFO - Loading data from `reviews` (CSVDataSet)...
2019-08-19 10:51:56,139 - kedro.pipeline.node - INFO - Running node: create_master_table([preprocessed_companies,preprocessed_shuttles,reviews]) -> [master_table]
2019-08-19 10:51:58,037 - kedro.io.data_catalog - INFO - Saving data to `master_table` (CSVDataSet)...
2019-08-19 10:52:09,133 - kedro.runner.sequential_runner - INFO - Completed 3 out of 6 tasks
2019-08-19 10:52:09,133 - kedro.io.data_catalog - INFO - Loading data from `master_table` (CSVDataSet)...
2019-08-19 10:52:10,941 - kedro.io.data_catalog - INFO - Loading data from `parameters` (MemoryDataSet)...
2019-08-19 10:52:10,941 - kedro.pipeline.node - INFO - Running node: split_data([master_table,parameters]) -> [X_test,X_train,y_test,y_train]
2019-08-19 10:52:11,343 - kedro.io.data_catalog - INFO - Saving data to `X_train` (MemoryDataSet)...
2019-08-19 10:52:11,372 - kedro.io.data_catalog - INFO - Saving data to `X_test` (MemoryDataSet)...
2019-08-19 10:52:11,380 - kedro.io.data_catalog - INFO - Saving data to `y_train` (MemoryDataSet)...
2019-08-19 10:52:11,381 - kedro.io.data_catalog - INFO - Saving data to `y_test` (MemoryDataSet)...
2019-08-19 10:52:11,443 - kedro.runner.sequential_runner - INFO - Completed 4 out of 6 tasks
2019-08-19 10:52:11,443 - kedro.io.data_catalog - INFO - Loading data from `X_train` (MemoryDataSet)...
2019-08-19 10:52:11,472 - kedro.io.data_catalog - INFO - Loading data from `y_train` (MemoryDataSet)...
2019-08-19 10:52:11,474 - kedro.pipeline.node - INFO - Running node: train_model([X_train,y_train]) -> [regressor]
2019-08-19 10:52:11,704 - kedro.io.data_catalog - INFO - Saving data to `regressor` (PickleDataSet)...
2019-08-19 10:52:11,776 - kedro.runner.sequential_runner - INFO - Completed 5 out of 6 tasks
2019-08-19 10:52:11,776 - kedro.io.data_catalog - INFO - Loading data from `regressor` (PickleDataSet)...
2019-08-19 10:52:11,776 - kedro.io.data_catalog - INFO - Loading data from `X_test` (MemoryDataSet)...
2019-08-19 10:52:11,784 - kedro.io.data_catalog - INFO - Loading data from `y_test` (MemoryDataSet)...
2019-08-19 10:52:11,785 - kedro.pipeline.node - INFO - Running node: evaluate_model([X_test,regressor,y_test]) -> None
2019-08-19 10:52:11,830 - kedro_tutorial.nodes.price_prediction - INFO - Model has a coefficient R^2 of 0.456.
2019-08-19 10:52:11,869 - kedro.runner.sequential_runner - INFO - Completed 6 out of 6 tasks
2019-08-19 10:52:11,869 - kedro.runner.sequential_runner - INFO - Pipeline execution completed successfully.
```
</details>

## Kedro runners

There are two different Kedro runners that can run the pipeline:

* `SequentialRunner` - runs your nodes sequentially; once a node has completed its task then the next one starts.
* `ParallelRunner` - runs your nodes in parallel; independent nodes are able to run at the same time, which is more efficient when there are independent branches in your pipeline and allows you to take advantage of multiple CPU cores.

By default, Kedro uses a `SequentialRunner`, which is instantiated when you execute `kedro run` from the command line. If you decide to use `ParallelRunner`, provide an additional flag when running the pipeline from the command line:

```bash
kedro run --parallel
```

> *Note:* `ParallelRunner` performs task parallelisation, which is different from data parallelisation as seen in PySpark.

You can find out more about the runners Kedro provides, and how to create your own, in the [pipeline documentation about runners](../06_nodes_and_pipelines/04_run_a_pipeline.md).

## Slice a pipeline

In some cases you may want to run just part of a pipeline. For example, you may need to only run the `ds_pipeline` to tune the hyperparameters of the price prediction model and skip `de_pipeline` execution. You can 'slice' the pipeline and specify just the portion you want to run by using the `--pipeline` command line option. For example, to only run `ds_pipeline`, execute the following command:

```bash
kedro run --pipeline=ds
```

See the [pipeline slicing documentation](../06_nodes_and_pipelines/05_slice_a_pipeline.md) for other ways to run sections of your pipeline.

> *Note:* To successfully run the pipeline, you need to make sure that all required input datasets already exist, otherwise you may get an error similar to this:

```bash
kedro run --pipeline=ds

2019-10-04 12:36:12,135 - root - INFO - ** Kedro project kedro-tutorial
2019-10-04 12:36:12,158 - kedro.io.data_catalog - INFO - Loading data from `master_table` (CSVDataSet)...
2019-10-04 12:36:12,158 - kedro.runner.sequential_runner - WARNING - There are 3 nodes that have not run.
You can resume the pipeline run with the following command:
kedro run
Traceback (most recent call last):
  ...
  File "pandas/_libs/parsers.pyx", line 382, in pandas._libs.parsers.TextReader.__cinit__
  File "pandas/_libs/parsers.pyx", line 689, in pandas._libs.parsers.TextReader._setup_parser_source
FileNotFoundError: [Errno 2] File b'data/03_primary/master_table.csv' does not exist: b'data/03_primary/master_table.csv'

The above exception was the direct cause of the following exception:

Traceback (most recent call last):
  ...
    raise DataSetError(message) from exc
kedro.io.core.DataSetError: Failed while loading data from data set CSVDataSet(filepath=data/03_primary/master_table.csv, save_args={'index': False}).
[Errno 2] File b'data/03_primary/master_table.csv' does not exist: b'data/03_primary/master_table.csv'
```
