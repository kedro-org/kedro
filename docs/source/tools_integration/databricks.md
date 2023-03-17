# Build a Kedro pipeline to run on Databricks

This page outlines some best practices when building a Kedro pipeline to run on [`Databricks`](https://docs.databricks.com/workspace-index.html). It assumes a basic understanding of both Kedro and `Databricks`. Follow the [PySpark guide](./pyspark.md#centralise-spark-configuration-in-confbasesparkyml) for how to instantiate your project to run on PySpark and where to store your spark config.

## Use Kedro's built-in Databricks datasets to load and save data

We recommend using Kedro's built-in Databricks datasets to load data into [Spark](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/dataframe.html) or [Pandas](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.html) DataFrames, as well as to write them back to managed Delta tables or MLFlow experiments. Some of our built-in Databricks datasets include:

* [databricks.ManagedTableDataSet](/kedro.datasets.databricks.ManagedTableDataSet)

The example below illustrates how to use `databricks.ManagedTableDataSet` to read a managed table in Databricks into a `DataFrame` in `conf/base/catalog.yml`:

```yaml
weather:
  type: databricks.ManagedTableDataSet
  table: raw_data
  database: weather_bronze
```

Or using the Python API:

```python
import pyspark.sql
from kedro.io import DataCatalog
from kedro_datasets.databricks import ManagedTableDataSet

databricks_ds = ManageTableDataSet(
    table="raw_data",
    database="weather_bronze",
)
catalog = DataCatalog({"weather": databricks_ds})

df = catalog.load("weather")
assert isinstance(df, pyspark.sql.DataFrame)
```

## Unity Catalog integration

[Unity Catalog](https://www.databricks.com/product/unity-catalog) is an offering by Databricks that enables governing access to resources and data through Databricks itself. This also allows for creating global metastores that can span multiple workspaces allowing your teams to securely share data internally and externally.

We recommend the following workflow, which makes use of the [transcoding feature in Kedro](../data/data_catalog.md):

* To create a managed Delta table, use a `ManagedTableDataSet` and define the `table`, `database` and `catalog` properties to point to the desired location you want to save the data within your unity catalog. Make sure you (or the service principal running) have the appropriate permissions to load/save data. You can also use this type of dataset to read from a managed Delta table and/or overwrite, upsert to it.
* The available write modes are overwrite, append and upsert. Upserts require the definition of primary key, or a list of primary keys for the join condition. The default mode is overwrite if not specified.

As a result, we end up with a Kedro catalog that looks like this:

```yaml
temperature:
  type: databricks.ManagedTableDataSet
  table: temperature
  database: bronze
  catalog: weather_analytics_dev

weather:
  type: databricks.ManagedTableDataSet
  table: weather
  database: silver
  catalog: weather_analytics_dev

weather@pandas:
  type: databricks.ManagedTableDataSet
  table: weather
  database: silver
  catalog: weather_analytics_dev
  dataframe_type: pandas
```

```python
pipeline(
    [
        node(
            func=process_barometer_data, inputs="temperature", outputs="weather"
        ),
        node(
            func=update_meterological_state,
            inputs="weather@pandas",
            outputs="first_operation_complete",
        ),
        node(
            func=estimate_weather_trend,
            inputs=["first_operation_complete", "weather"],
            outputs="second_operation_complete",
        ),
    ]
)
```

`first_operation_complete` is a `MemoryDataSet` and it signals that any Delta operations which occur "outside" the Kedro DAG are complete. This can be used as input to a downstream node, to preserve the shape of the DAG. Otherwise, if no downstream nodes need to run after this, the node can simply not return anything:

```python
pipeline(
    [
        node(func=..., inputs="temperature", outputs="weather"),
        node(func=..., inputs="weather@pandas", outputs=None),
    ]
)
```

The following diagram is the visual representation of the workflow explained above:

```{note}
This pattern of creating "dummy" datasets to preserve the data flow also applies to other "out of DAG" execution operations such as SQL operations within a node.
```

## Use `MemoryDataSet` for intermediary `DataFrame`

For nodes operating on `DataFrame` that doesn't need to perform Spark actions such as writing the `DataFrame` to storage, we recommend using the default `MemoryDataSet` to hold the `DataFrame`. In other words, there is no need to specify it in the `DataCatalog` or `catalog.yml`. This allows you to take advantage of Spark's optimiser and lazy evaluation.

## Use `MemoryDataSet` with `copy_mode="assign"` for non-`DataFrame` Spark objects

Sometimes, you might want to use Spark objects that aren't `DataFrame` as inputs and outputs in your pipeline. For example, suppose you have a `train_model` node to train a classifier using Spark ML's [`RandomForrestClassifier`](https://spark.apache.org/docs/latest/ml-classification-regression.html#random-forest-classifier) and a `predict` node to make predictions using this classifier. In this scenario, the `train_model` node will output a `RandomForestClassifier` object, which then becomes the input for the `predict` node. Below is the code for this pipeline:

```python
from typing import Any, Dict

from kedro.pipeline import node, pipeline
from pyspark.ml.classification import RandomForestClassifier
from pyspark.sql import DataFrame


def train_model(training_data: DataFrame) -> RandomForestClassifier:
    """Node for training a random forest model to classify the data."""
    classifier = RandomForestClassifier(numTrees=10)
    return classifier.fit(training_data)


def predict(model: RandomForestClassifier, testing_data: DataFrame) -> DataFrame:
    """Node for making predictions given a pre-trained model and a testing dataset."""
    predictions = model.transform(testing_data)
    return predictions


def create_pipeline(**kwargs) -> Pipeline:
    return pipeline(
        [
            node(train_model, inputs=["training_data"], outputs="example_classifier"),
            node(
                predict,
                inputs=dict(model="example_classifier", testing_data="testing_data"),
                outputs="example_predictions",
            ),
        ]
    )
```

To make the pipeline work, you will need to specify `example_classifier` as follows in the `catalog.yml`:

```yaml
example_classifier:
  type: MemoryDataSet
  copy_mode: assign
```

The `assign` copy mode ensures that the `MemoryDataSet` will be assigned the Spark object itself, not a [deep copy](https://docs.python.org/3/library/copy.html) version of it, since deep copy doesn't work with Spark object generally.

## Tips for maximising concurrency using `ThreadRunner`

Under the hood, every Kedro node that performs a Spark action (e.g. `save`, `collect`) is submitted to the Spark cluster as a Spark job through the same `SparkSession` instance. These jobs may be running concurrently if they were submitted by different threads. In order to do that, you will need to run your Kedro pipeline with the [ThreadRunner](/kedro.runner.ThreadRunner):

```bash
kedro run --runner=ThreadRunner
```

To further increase the concurrency level, if you are using Spark >= 0.8, you can also give each node a roughly equal share of the Spark cluster by turning on fair sharing and therefore giving them a roughly equal chance of being executed concurrently. By default, they are executed in a FIFO manner, which means if a job takes up too much resources, it could hold up the execution of other jobs. In order to turn on fair sharing, put the following in your `conf/base/spark.yml` file, which was created in the [Initialise a `SparkSession`](#initialise-a-sparksession-using-a-hook) section:

```yaml
spark.scheduler.mode: FAIR
```

For more information, please visit Spark documentation on [jobs scheduling within an application](https://spark.apache.org/docs/latest/job-scheduling.html#scheduling-within-an-application).
