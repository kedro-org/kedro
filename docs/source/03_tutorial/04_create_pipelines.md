# Creating a pipeline

This section covers how to create a pipeline from a set of `node`s, which are Python functions, as described in more detail in the [nodes user guide](../04_user_guide/05_nodes.md#nodes) documentation.

1. As you draft experimental code, you can use a [Jupyter Notebook](../04_user_guide/11_ipython.md#working-from-jupyter) or [IPython session](../04_user_guide/11_ipython.md). If you include [`docstrings`](https://google.github.io/styleguide/pyguide.html#38-comments-and-docstrings) to explain what your functions do, you can take advantage of [auto-generated Sphinx documentation](http://www.sphinx-doc.org/en/master/) later on. Once you are happy with how you have written your `node` functions, you will run `kedro jupyter convert --all` (or `kedro jupyter convert <filepath_to_my_notebook>`) to export the code cells [tagged](https://jupyter-notebook.readthedocs.io/en/stable/changelog.html#cell-tags) as `node` into the `src/kedro_tutorial/nodes/` folder as a `.py` file.
2. When you are ready with a node you should add it to the pipeline in `src/kedro_tutorial/pipeline.py`, specifying its inputs and outputs.


## Node basics

You previously registered the raw datasets for your Kedro project, so you can now start processing the data and preparing it for model building. Let’s pre-process two of the datasets ([companies.csv](https://github.com/quantumblacklabs/kedro/tree/develop/docs/source/03_tutorial/data/companies.csv) and [shuttles.xlsx](https://github.com/quantumblacklabs/kedro/tree/develop/docs/source/03_tutorial/data/shuttles.xlsx)) by creating Python functions for each.

Create a file `src/kedro_tutorial/pipelines/data_engineering/nodes.py` (and any missing directories) and add the following functions:

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


## Assemble nodes into a pipeline

Now you have functions which take one dataframe and output a pre-processed version of that dataframe. Next you should add these functions as nodes into the pipeline in `src/kedro_tutorial/pipelines/data_engineering/pipeline.py`, so the `create_pipeline()` function looks as follows:

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

It's important to note that here `companies` and `shuttles` refer to the datasets defined in `conf/base/catalog.yml`. Their contents will be loaded and served as inputs to the `preprocess_companies` and `preprocess_shuttles` functions.

You will also need to import `node`, and your functions by adding them to the beginning of the `pipeline.py` file:

```python
from kedro.pipeline import node, Pipeline
from kedro_tutorial.pipelines.data_engineering.nodes import (
    preprocess_companies,
    preprocess_shuttles,
)
```

As well as this, you should update the project's pipelines in `src/kedro_tutorial/pipeline.py`:
```python
from typing import Dict

from kedro.pipeline import Pipeline

from kedro_tutorial.pipelines.data_engineering import pipeline as de


def create_pipelines(**kwargs) -> Dict[str, Pipeline]:
    """Create the project's pipeline.

    Args:
        kwargs: Ignore any additional arguments added in the future.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """
    de_pipeline = de.create_pipeline()

    return {
        "de": de_pipeline,
        "__default__": de_pipeline,
    }
```

As you develop your nodes, you can test too see if they work as expected. As an example, run the following command in your terminal window:

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


Now check if the entire pipeline is running without any errors by typing this in your terminal window:

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


## Persisting pre-processed data

Now each of our 2 newly added data preprocessing nodes outputs a new dataset: `preprocessed_companies` and `preprocessed_shuttles` respectively. Node inputs and outputs are used by the pipeline to determine interdependencies between the nodes, and hence, their execution order.

When Kedro ran the pipeline, it determined that those datasets were not registered in the data catalog (`conf/base/catalog.yml`). If a dataset is not registered, Kedro stores it in memory as a Python object using the [MemoryDataSet](/kedro.io.MemoryDataSet) class. Once all nodes depending on it have been executed, a `MemoryDataSet` is cleared and its memory released by the Python garbage collector.

If you prefer, you can persist any preprocessed data by adding the following to the `conf/base/catalog.yml` file:

```yaml
preprocessed_companies:
  type: pandas.CSVDataSet
  filepath: data/02_intermediate/preprocessed_companies.csv

preprocessed_shuttles:
  type: pandas.CSVDataSet
  filepath: data/02_intermediate/preprocessed_shuttles.csv
```

By doing so you explicitly declare that [pandas.CSVDataSet](/kedro.extras.datasets.pandas.CSVDataSet) should be used instead of [`MemoryDataSet`](/kedro.io.MemoryDataSet). This will save the data as a CSV file to the `filepath` specified. There is no need to change any code in your preprocessing functions to accommodate this change. `DataCatalog` will take care of saving those datasets automatically the next time you run the pipeline:

```bash
kedro run
```

`pandas.CSVDataSet` is chosen for its simplicity, but you can choose any other available dataset implementation class to save the data, for example, to a database table, cloud storage (like [AWS S3](https://aws.amazon.com/s3/), [Azure Blob Storage](https://azure.microsoft.com/en-gb/services/storage/blobs/), etc.) and others. If you cannot find the dataset implementation you need, you can easily implement your own as [you already did earlier](./03_set_up_data.md#creating-custom-datasets) and share it with the world by contributing back to Kedro!

## Creating a master table

We need to add a function to join together the three dataframes into a single master table in a cell in the notebook as follows:

```python
import pandas as pd


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

### Working in a Jupyter notebook

To create a new node to join all tables to form a master table, you need to add the three dataframes to a cell in the Jupyter notebook:

```python
preprocessed_shuttles = catalog.load("preprocessed_shuttles")
preprocessed_companies = catalog.load("preprocessed_companies")
reviews = catalog.load("reviews")

master = create_master_table(preprocessed_shuttles, preprocessed_companies, reviews)
master.head()
```

### Extending the project's code

Having tested that all is working with the master table, it is now time to add the code you've worked on to the Spaceflights project code. First, add the `create_master_table()` function from the snippet above to `src/kedro_tutorial/pipelines/data_engineering/nodes.py` - you do not need to copy the import statement `import pandas as pd` as it has already been imported at the top of the file.

Then you should add it to the pipeline in `src/kedro_tutorial/pipelines/data_engineering/pipeline.py` by adding the node as follows:

```python
node(
    func=create_master_table,
    inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
    outputs="master_table",
    name="master_table",
),
```
By adding this code to the project, you are telling Kedro that the function `create_master_table` should be called with the data loaded from datasets `preprocessed_shuttles`, `preprocessed_companies`, and `reviews` and the output should be saved to dataset `master_table`.

You will also need to add an import statement for `create_master_table` at the top of the file:

```python
from kedro_tutorial.pipelines.data_engineering.nodes import (
    preprocess_companies,
    preprocess_shuttles,
    create_master_table,
)
```

If you want your data to be saved to file rather than used in-memory, you also need to add an entry to the `conf/base/catalog.yml` file like this:

```yaml
master_table:
  type: pandas.CSVDataSet
  filepath: data/03_primary/master_table.csv
```

You may want to test that all is working with your code at this point:

```bash
kedro run

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


## Working with multiple pipelines

Having merged three input datasets to create a master table, you are now ready to make another pipeline for a price prediction model. It will be called the data science pipeline.

For this example, we will use a [`LinearRegression`](https://scikit-learn.org/stable/modules/generated/sklearn.linear_model.LinearRegression.html) implementation from the [scikit-learn](https://scikit-learn.org/stable/) library.

You can start by updating the dependencies in `src/requirements.txt` with the following:

```text
scikit-learn==0.20.2
```

You can find out more about requirements files [here](https://pip.pypa.io/en/stable/user_guide/#requirements-files).

Then, from within the project directory, run:

```bash
kedro install
```

Next, create a file `src/kedro_tutorial/pipelines/data_science/nodes.py` (along with any missing directories) and add the following code to it:

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
Add the following to `conf/base/parameters.yml`:

```yaml
test_size: 0.2
random_state: 3
```

These are the parameters fed into the `DataCatalog` when the pipeline is executed. You can learn more about parameters in our [user guide](../04_user_guide/03_configuration.md#parameters), where we give a full explanation on how they work.

Alternatively, the parameters specified in `parameters.yml` can also be referenced using `params:` prefix in the nodes. For example, you could pass `test_size` and `random_state` parameters as follows:

```python
# in src/kedro_tutorial/pipelines/data_science/nodes.py:


def split_data(data: pd.DataFrame, test_size: str, random_state: str) -> List:
    """
    Arguments now accepts `test_size` and `random_state` rather than `parameters: Dict`.
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
        X, y, test_size=test_size, random_state=random_state
    )

    return [X_train, X_test, y_train, y_test]


# in src/kedro_tutorial/pipelines/data_science/pipeline.py:


def create_pipeline(**kwargs) -> Dict[str, Pipeline]:
    return Pipeline(
        [
            node(
                func=split_data,
                inputs=["master_table", "params:test_size", "params:random_state"],
                outputs=["X_train", "X_test", "y_train", "y_test"],
            )
        ]
    )
```

Next, register the dataset, which will save the trained model, by adding the following definition to `conf/base/catalog.yml`:

```yaml
regressor:
  type: pickle.PickleDataSet
  filepath: data/06_models/regressor.pickle
  versioned: true
```

> *Note:* Versioning is enabled for `regressor`, which means that the pickled output of the `regressor` will be versioned and saved every time the pipeline is run. This allows us to keep the history of the models built using this pipeline. See the details in the [Versioning](../04_user_guide/08_advanced_io.md#versioning) section of the User Guide.

Now to create a pipeline for the price prediction model. In `src/kedro_tutorial/pipelines/data_science/pipeline.py`, add an extra import statement near the top of the file as follows:

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

Finally, add a separate Data Science pipeline, by replacing the code in `create_pipelines` in `src/kedro_tutorial/pipeline.py` as follows:
```python
def create_pipelines(**kwargs) -> Dict[str, Pipeline]:
    """Create the project's pipeline.

    Args:
        kwargs: Ignore any additional arguments added in the future.

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

Make sure to include the import at the top of the file:
```python
from kedro_tutorial.pipelines.data_science import pipeline as ds
```

The first node of the `ds_pipeline` outputs 4 objects: `X_train`, `X_test`, `y_train`, `y_test`, which are not registered in `conf/base/catalog.yml`. (If you recall, if a dataset is not specified in the catalog, Kedro will automatically save it in memory using the `MemoryDataSet`). Normally you would add dataset definitions of your model features into `conf/base/catalog.yml` with the save location in `data/04_features/`.

The two pipelines are merged together in `de_pipeline + ds_pipeline` into a project default pipeline using `__default__` key. Default pipeline containing all nodes from both original pipelines will be executed when you invoke the following:

```bash
kedro run
```
You should see output similar to the following:

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

The `de_pipeline` will preprocess the data, and `ds_pipeline` will then create features, train and evaluate the model.

> *Note:* The order in which you add the pipelines together is not significant and `ds_pipeline + de_pipeline` will result in the same pipeline, since Kedro automatically detects the correct execution order for all the nodes in the resulting pipeline.


## Partial pipeline runs

In some cases, you may want to partially run the pipeline. For example, you may need to only run the `ds_pipeline` to tune the hyperparameters of the price prediction model and skip `de_pipeline` execution. The most obvious way of doing this is by modifying your Python code for pipeline definition. However, we strongly advise against it, since this approach is very error-prone and unsustainable in the long-term.

### Using pipeline name

The recommended, and arguably the easiest, way is to specify the pipeline you want to run by its name using `--pipeline` command line option. For example, to only run `ds_pipeline`, execute the following command:

```bash
kedro run --pipeline=ds
```

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

### Using tags

Another way to run partial pipelines without changing your code is to use tags. Each node within the pipeline can be tagged by passing **`tags`** into the `Pipeline()`. Update the `create_pipeline()` code in `src/kedro_tutorial/pipelines/data_engineering/pipeline.py` and `src/kedro_tutorial/pipelines/data_science/pipeline.py` one more time:

```python
# src/kedro_tutorial/pipelines/data_engineering/pipeline.py
def create_pipeline(**kwargs) -> Dict[str, Pipeline]:
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
            node(
                func=create_master_table,
                inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
                outputs="master_table",
                name="master_table",
            ),
        ],
        tags=["de_tag"],
    )


# src/kedro_tutorial/pipelines/data_science/pipeline.py
def create_pipeline(**kwargs) -> Dict[str, Pipeline]:
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
        ],
        tags=["ds_tag"],
    )
```

If the pipeline definition contains `tags=` argument, Kedro will attach the corresponding tags (`de_tag` and `ds_tag` in the example above) to every node within that pipeline.

To run a partial pipeline using a tag:

```bash
kedro run --tag=ds_tag
```

This will skip the execution of the pipeline with tag `de_tag` and only run the `ds_tag` nodes (found within the `ds_pipeline`). If you want to run the whole pipeline:

```bash
kedro run
```

or:

```bash
kedro run --tag=ds_tag,de_tag
```

> *Note:* You can also attach tags to the individual nodes by passing the `tags` keyword to the `node()` function, and these are used in addition to any tags specified at the pipeline level. To tag a node as `my-regressor-node`:

```python
node(
    train_model, ["X_train", "y_train"], "regressor", tags=["my-regressor-node"],
)
```

## Using decorators for nodes and pipelines

In this section, you will learn about Kedro's built-in decorators as well as how to create your own node and pipeline decorators.

[Python decorators](https://wiki.python.org/moin/PythonDecorators) can be applied to Kedro nodes. Let's walk through an example of building our own decorator for logging the execution time of each node.

### Decorating the nodes

Logging the execution time for each node can be performed by creating a function and adding it to each node as a decorator.

In `src/kedro_tutorial/pipelines/data_engineering/nodes.py`, add the following decorator function near the top of the file:

```python
from functools import wraps
from typing import Callable
import time
import logging


def log_running_time(func: Callable) -> Callable:
    """Decorator for logging node execution time.

        Args:
            func: Function to be executed.

        Returns:
            Decorator for logging the running time.

    """

    @wraps(func)
    def with_time(*args, **kwargs):
        log = logging.getLogger(__name__)
        t_start = time.time()
        result = func(*args, **kwargs)
        t_end = time.time()
        elapsed = t_end - t_start
        log.info("Running %r took %.2f seconds", func.__name__, elapsed)
        return result

    return with_time
```

And apply it to each data engineering function by prepending `@log_running_time` to the definition:

```python
@log_running_time
def preprocess_companies(companies: pd.DataFrame) -> pd.DataFrame:
    ...


@log_running_time
def preprocess_shuttles(shuttles: pd.DataFrame) -> pd.DataFrame:
    ...
```

Then, if you run your pipeline from the command line, you should see a similar output:

```bash
kedro run

...
kedro_tutorial.nodes.data_engineering - INFO - Running 'preprocess_companies' took XXX seconds
...
kedro_tutorial.nodes.data_engineering - INFO - Running 'preprocess_shuttles' took XXX seconds
```

### Decorating the pipeline

A decorator can also be applied to the pipeline rather than each node. In `src/kedro_tutorial/pipeline.py`, update the imports from `src/kedro_tutorial/pipelines/data_engineering/nodes.py` as follows:

```python
from kedro_tutorial.pipelines.data_engineering.nodes import (
    create_master_table,
    log_running_time,
    preprocess_companies,
    preprocess_shuttles,
)
```

Then add the decorators to the pipeline:

```python
def create_pipelines(**kwargs) -> Dict[str, Pipeline]:
    """Create the project's pipeline.

    Args:
        kwargs: Ignore any additional arguments added in the future.

    Returns:
        A mapping from a pipeline name to a ``Pipeline`` object.

    """
    de_pipeline = de.create_pipeline().decorate(log_running_time)
    ds_pipeline = ds.create_pipeline().decorate(log_running_time)

    return {
        "de": de_pipeline,
        "ds": ds_pipeline,
        "__default__": de_pipeline + ds_pipeline,
    }
```

This decorator is commonly used and Kedro already includes it as a built-in decorator called `kedro.pipeline.decorators.log_time`.

Another built-in decorator is `kedro.pipeline.decorators.mem_profile`, which will log the maximum memory usage of your node.


## Kedro runners

Having specified the data catalog and the pipeline, you are now ready to run the pipeline. There are two different runners you can specify:

* `SequentialRunner` - runs your nodes sequentially; once a node has completed its task then the next one starts.
* `ParallelRunner` - runs your nodes in parallel; independent nodes are able to run at the same time, allowing you to take advantage of multiple CPU cores.

By default, Kedro uses a `SequentialRunner`, which is instantiated when you execute `kedro run` from the command line. Switching to use `ParallelRunner` is as simple as providing an additional flag when running the pipeline from the command line as follows:

```bash
kedro run --parallel
```

`ParallelRunner` executes the pipeline nodes in parallel, and is more efficient when there are independent branches in your pipeline.

> *Note:* `ParallelRunner` performs task parallelisation, which is different from data parallelisation as seen in PySpark.
