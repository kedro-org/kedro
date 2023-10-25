# Create a data processing pipeline

This section explains the following:

* How to create a Kedro node from a Python function
* How to construct a Kedro pipeline from a set of nodes
* How to persist, or save, datasets output from the pipeline by registering them in the data catalog
* How to run the pipeline

## Introduction

The data processing pipeline prepares the data for model building by combining the datasets to create a model input table. The data processing pipeline is made up of the following:

* Two python files within `src/spaceflights/pipelines/data_processing`
    * `nodes.py` (for the node functions that form the data processing)
    * `pipeline.py` (to build the pipeline)
* A yaml file: `conf/base/parameters_data_processing.yml` to define the parameters used when running the pipeline
* `__init__.py` files in the required folders to ensure that Python can import the pipeline

```{note}
Kedro provides the `kedro pipeline create` command to add the skeleton code for a new pipeline. If you are writing a project from scratch and want to add a new pipeline, run the following from the terminal: `kedro pipeline create <pipeline_name>`. You do **not** need to do this in the spaceflights example as it is already supplied by the starter project.
```

## Data preprocessing node functions

The first step is to preprocess two of the datasets, `companies.csv`, and `shuttles.xlsx`. The preprocessing code for the nodes is in `src/spaceflights/pipelines/data_processing/nodes.py` as a pair of functions (`preprocess_companies` and `preprocess_shuttles`). Each takes a raw DataFrame as input, converts the data in several columns to different types, and outputs a DataFrame containing the preprocessed data:

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

## The data processing pipeline

Next, take a look at `src/spaceflights/pipelines/data_processing/pipeline.py` which constructs a [node](../resources/glossary.md#node) for each function defined above and creates a [modular pipeline](../resources/glossary.md#modular-pipeline) for data processing:


<details>
<summary><b>Click to expand</b></summary>

```python
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import preprocess_companies, preprocess_shuttles

...


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
            ...,
        ]
    )
```

</details>


Note that the `inputs` statements for `companies` and `shuttles` refer to the datasets defined in `conf/base/catalog.yml`. They are inputs to the `preprocess_companies` and `preprocess_shuttles` functions. Kedro uses the named node inputs (and outputs) to determine interdependencies between the nodes, and their execution order.


## Test the example

Run the following command in your terminal window to test the node named `preprocess_companies_node`:

```bash
kedro run --nodes=preprocess_companies_node
```

You should see output similar to the below:

<details>
<summary><b>Click to expand</b></summary>

```bash
[08/09/22 16:43:11] INFO     Loading data from 'companies' (CSVDataset)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataset)...      data_catalog.py:382
                    INFO     Completed 1 out of 1 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataset)...   data_catalog.py:343

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
                    INFO     Loading data from 'companies' (CSVDataset)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataset)...      data_catalog.py:382
                    INFO     Completed 1 out of 2 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'shuttles' (ExcelDataset)...                  data_catalog.py:343
[08/09/22 16:46:08] INFO     Running node: preprocess_shuttles_node: preprocess_shuttles([shuttles]) node.py:327
                             -> [preprocessed_shuttles]
                    INFO     Saving data to 'preprocessed_shuttles' (MemoryDataset)...       data_catalog.py:382
                    INFO     Completed 2 out of 2 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataset)...   data_catalog.py:343
                    INFO     Loading data from 'preprocessed_shuttles' (MemoryDataset)...    data_catalog.py:343

```
</details>

## Preprocessed data registration

Each of the nodes outputs a new dataset (`preprocessed_companies` and `preprocessed_shuttles`). Kedro saves these outputs in Parquet format [pandas.ParquetDataset](/kedro_datasets.pandas.ParquetDataset) because they are registered within the [Data Catalog](../resources/glossary.md#data-catalog) as you can see in `conf/base/catalog.yml`:

<details>
<summary><b>Click to expand</b></summary>

```yaml
preprocessed_companies:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/preprocessed_companies.pq

preprocessed_shuttles:
  type: pandas.ParquetDataset
  filepath: data/02_intermediate/preprocessed_shuttles.pq
```
</details>

If you remove these lines from `catalog.yml`, Kedro still runs the pipeline successfully and automatically stores the preprocessed data, in memory, as temporary Python objects of the [MemoryDataset](/kedro.io.MemoryDataset) class. Once all nodes that depend on a temporary dataset have executed, Kedro clears the dataset and the Python garbage collector releases the memory.


## Create a table for model input

The next step adds another node that joins together three datasets (`preprocessed_shuttles`, `preprocessed_companies`, and `reviews`) into a single model input table which is saved as `model_input_table`.

The code for the `create_model_input_table()` function is in `src/spaceflights/pipelines/data_processing/nodes.py`:

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
    rated_shuttles = rated_shuttles.drop("id", axis=1)
    companies = companies.drop_duplicates()
    model_input_table = rated_shuttles.merge(
        companies, left_on="company_id", right_on="id"
    )
    model_input_table = model_input_table.dropna()
    return model_input_table
```

</details>


The node is created in `src/kedro_tutorial/pipelines/data_processing/pipeline.py`:

<details>
<summary><b>Click to expand</b></summary>

```python
from kedro.pipeline import Pipeline, node, pipeline

from .nodes import create_model_input_table, preprocess_companies, preprocess_shuttles


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
            node(
                func=create_model_input_table,
                inputs=["preprocessed_shuttles", "preprocessed_companies", "reviews"],
                outputs="model_input_table",
                name="create_model_input_table_node",
            ),
        ]
    )
```
</details>

## Model input table registration

The following entry in `conf/base/catalog.yml` saves the model input table dataset to file (in `data/03_primary`):

```yaml
model_input_table:
  type: pandas.ParquetDataset
  filepath: data/03_primary/model_input_table.pq
```

## Test the example again

To test the progress of the example:

```bash
kedro run
```

You should see output similar to the following:

<details>
<summary><b>Click to expand</b></summary>

```bash
[08/09/22 17:01:10] INFO     Reached after_catalog_created hook                                     plugin.py:17
                    INFO     Loading data from 'companies' (CSVDataset)...                   data_catalog.py:343
                    INFO     Running node: preprocess_companies_node:                                node.py:327
                             preprocess_companies([companies]) -> [preprocessed_companies]
                    INFO     Saving data to 'preprocessed_companies' (MemoryDataset)...      data_catalog.py:382
                    INFO     Completed 1 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'shuttles' (ExcelDataset)...                  data_catalog.py:343
[08/09/22 17:01:25] INFO     Running node: preprocess_shuttles_node: preprocess_shuttles([shuttles]) node.py:327
                             -> [preprocessed_shuttles]

                    INFO     Saving data to 'preprocessed_shuttles' (MemoryDataset)...       data_catalog.py:382
                    INFO     Completed 2 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Loading data from 'preprocessed_shuttles' (MemoryDataset)...    data_catalog.py:343
                    INFO     Loading data from 'preprocessed_companies' (MemoryDataset)...   data_catalog.py:343
                    INFO     Loading data from 'reviews' (CSVDataset)...                     data_catalog.py:343
                    INFO     Running node: create_model_input_table_node:                            node.py:327
                             create_model_input_table([preprocessed_shuttles,preprocessed_companies,
                             reviews]) -> [model_input_table]
[08/09/22 17:01:28] INFO     Saving data to 'model_input_table' (MemoryDataset)...           data_catalog.py:382
[08/09/22 17:01:29] INFO     Completed 3 out of 3 tasks                                  sequential_runner.py:85
                    INFO     Pipeline execution completed successfully.                             runner.py:89
                    INFO     Loading data from 'model_input_table' (MemoryDataset)...        data_catalog.py:343
```
</details>

## Visualise the project

This section introduces project visualisation using Kedro-Viz, which is a separate package from the standard Kedro installation. To install it your virtual environment:

```bash
pip install kedro-viz
```

To start Kedro-Viz, enter the following in your terminal:

```bash
kedro viz
```

This command automatically opens a browser tab to serve the visualisation at `http://127.0.0.1:4141/`. Explore the visualisation at leisure, and consult the [visualisation documentation](../visualisation/kedro-viz_visualisation) for more detail.

To exit, close the browser tab. To regain control of the terminal, enter `^+c` on Mac or `Ctrl+c` on Windows or Linux machines.

## Checkpoint

This is an excellent place to take a breath and summarise what you have seen in the example so far.

![](../meta/images/coffee-cup.png)

Photo by <a href="https://unsplash.com/@maltehelmhold">Malte Helmhold</a> on <a href="https://unsplash.com">Unsplash</a>


* How to create a new Kedro project from a starter and install its dependencies
* How to add three datasets to the project and set up the Kedro Data Catalog
* How to create a data processing pipeline with three nodes to transform and merge the input datasets and create a model input table
* How to persist the output from a pipeline by registering those datasets to the Data Catalog
* How to visualise the project

The next step is to create the data science pipeline for spaceflight price prediction.
