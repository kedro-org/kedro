# Create a data processing pipeline

```{note}
Don't forget to check the [tutorial FAQ](spaceflights_tutorial_faqs.md) if you run into problems, or [ask the community for help](spaceflights_tutorial.md#get-help) if you need it!
```

This section explains the following:

* How to create a Kedro node from a Python function
* How to construct a Kedro pipeline from a set of nodes
* How to run the pipeline

```{note}
If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste steps below, but it is worth reviewing the files described.
```

## Data processing pipeline

You will use the data to train a model to predict the price of shuttle hire, but before you get to train the model, you need to prepare the data for model building by combining the files to create a model input table.

You previously registered the raw datasets for your Kedro project, so you can now create nodes to preprocess two of the datasets, `companies.csv`, and `shuttles.xlsx`, to prepare the data for modelling.

### Generate a new pipeline template

In the terminal, run the following command to generate a new pipeline for data processing:

```bash
kedro pipeline create data_processing
```

This command generates all the files you need for the pipeline:

* Two python files within `src/kedro_tutorial/pipelines/data_processing`
    * `nodes.py` (for the node functions that form the data processing)
    * `pipeline.py` (to build the pipeline)
* A yaml file: `conf/base/parameters/data_processing.yml` to define the parameters used when running the pipeline
* A folder for test code: `src/tests/pipelines/data_processing`
* `__init__.py` files in the required folders to ensure that Python can import the pipeline


### Add node functions


Open `src/kedro_tutorial/pipelines/data_processing/nodes.py` and add the code below, which provides two functions (`preprocess_companies` and `preprocess_shuttles`) that each takes a raw DataFrame as input, convert the data in several columns to different types, and output a DataFrame containing the preprocessed data:

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

The next steps are to create a [node](../resources/glossary.md#node) for each function and to create a [modular pipeline](../resources/glossary.md#modular-pipeline) for data processing:

First, add import statements for your functions by adding them to the beginning of `pipeline.py`:

```python
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import preprocess_companies, preprocess_shuttles
```

Next, add the following to `src/kedro_tutorial/pipelines/data_processing/pipeline.py`, so the `create_pipeline()` function is as follows:

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

</details>


Note that the `inputs` statements for `companies` and `shuttles` refer to the datasets defined in `conf/base/catalog.yml`. They are inputs to the `preprocess_companies` and `preprocess_shuttles` functions. Kedro uses the named node inputs (and outputs) to determine interdependencies between the nodes, and their execution order.


### Test the example

Run the following command in your terminal window to test the node named `preprocess_companies_node`:

```bash
kedro run --nodes=preprocess_companies_node
```

You should see output similar to the below:

<details>
<summary><b>Click to expand</b></summary>

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
</details>

You can run the `preprocess_shuttles` node similarly. To test both nodes together as the complete data processing pipeline:

```bash
kedro run
```

You should see output similar to the following:

<details>
<summary><b>Click to expand</b></summary>

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
</details>

### Optional: save the preprocessed data

Each of the nodes outputs a new dataset (`preprocessed_companies` and `preprocessed_shuttles`).

When Kedro runs the pipeline, it determines that neither dataset is registered in the data catalog, so it stores these as temporary datasets in memory as Python objects using the [MemoryDataSet](/kedro.io.MemoryDataSet) class. Once all nodes that depend on an temporary dataset have executed, the dataset is cleared and the Python garbage collector releases the memory.

If you prefer to save the preprocessed data to file, add the following to the end of `conf/base/catalog.yml` (If you are using the tutorial created by the spaceflights starter, you can omit the copy/paste):

```yaml
preprocessed_companies:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/preprocessed_companies.pq

preprocessed_shuttles:
  type: pandas.ParquetDataSet
  filepath: data/02_intermediate/preprocessed_shuttles.pq
```

Adding the data to the catalog declares explicitly that Kedro should use [pandas.ParquetDataSet](/kedro.datasets.pandas.ParquetDataSet) instead of [`MemoryDataSet`](/kedro.io.MemoryDataSet). The [Data Catalog](../resources/glossary.md#data-catalog) automatically saves the datasets (in Parquet format) to the path specified next time the pipeline is run. There is no need to change any code in your preprocessing functions to accommodate this change.

We chose the [Apache Parquet](https://github.com/apache/parquet-format) format for working with processed and typed data, and we recommend getting your data out of CSV as soon as possible. Parquet supports things like compression, partitioning and types out of the box. While you lose the ability to view the file as text, the benefits greatly outweigh the drawbacks.

### Extend the data processing pipeline

The next step in the tutorial is to add another node for a function that joins together the three datasets into a single model input table. You'll add some code for a function and node called `create_model_input_table`, which Kedro processes as follows:

* Kedro uses the `preprocessed_shuttles`, `preprocessed_companies`, and `reviews` datasets as inputs
* Kedro saves the output as a dataset called `model_input_table`

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

Add an import statement for `create_model_input_table` at the top of `src/kedro_tutorial/pipelines/data_processing/pipeline.py`:

```python
from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles
```

Add the code below to include the new node in the pipeline:

```python
node(
    func=create_model_input_table,
    inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
    outputs="model_input_table",
    name="create_model_input_table_node",
),
```


### Optional: save the model input table

If you want the model input table data to be saved to file (in `data/03_primary`) rather than used in memory, add an entry to `conf/base/catalog.yml`:

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

<details>
<summary><b>Click to expand</b></summary>

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
</details>

## Checkpoint

This is an excellent place to take a breath and summarise what you have done so far.

![](../meta/images/coffee-cup.png)

Photo by <a href="https://unsplash.com/@maltehelmhold">Malte Helmhold</a> on <a href="https://unsplash.com">Unsplash</a>


* Created a new project and installed dependencies
* Added three datasets to the project and set up the Kedro Data Catalog
* Created a data processing pipeline with three nodes to transform and merge the input datasets and create a model input table

The next step is to create the data science pipeline for spaceflight price prediction.
