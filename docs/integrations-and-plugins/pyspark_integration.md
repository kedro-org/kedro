# PySpark integration

This page outlines some best practices when building a Kedro pipeline with [`PySpark`](https://spark.apache.org/docs/latest/api/python/index.html). It assumes a basic understanding of both Kedro and `PySpark`.

## Get started with the PySpark starter

You can use the built-in PySpark starter with the `kedro new` command to create a working Spark-based project:

```bash
uvx kedro new --name=spaceflights-databricks --tools=pyspark --example=y
```

This starter is designed specifically for Spark. It replaces pandas-based datasets with `SparkDatasetV2` in the Data Catalog and implements data transformations using Spark.

The starter supports multiple execution modes, including running [Kedro directly on Databricks](../deploy/supported-platforms/databricks.md#run-kedro-within-databricks-git-folders) and [using a remote Spark cluster from your local machine with Databricks Connect](../deploy/supported-platforms/databricks.md#local-development-remote-databricks-cluster-databricks-connect).

If you want to run the project locally, install PySpark first. It is not included in the starter dependencies by default. You can install it with `kedro-datasets`:

```bash
uv pip install kedro-datasets[spark-local]
```

## Use Kedro’s built-in Spark datasets to load and save raw data

We recommend using Kedro’s built-in Spark datasets to load raw data into Spark [DataFrames](https://spark.apache.org/docs/latest/api/python/reference/pyspark.sql/dataframe.html) and to write the results back to storage.

You can find full documentation for the main Spark dataset, including examples for both Data Catalog configuration and Python API usage, here:

- [`spark.SparkDatasetV2`](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets/spark.SparkDatasetV2/)

Kedro also provides several platform-specific Spark datasets:

- [`spark.DeltaTableDataset`](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets/spark.DeltaTableDataset/)
- [`spark.SparkJDBCDataset`](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets/spark.SparkJDBCDataset/)
- [`spark.SparkHiveDataset`](https://docs.kedro.org/projects/kedro-datasets/en/kedro-datasets-9.1.1/api/kedro_datasets/spark.SparkHiveDataset/)


## Spark and Delta Lake interaction

[Delta Lake](https://delta.io/) is an open-source project that enables building a lake house architecture on top of data lakes. It provides ACID transactions and unifies streaming and batch data processing on top of existing data lakes, such as S3, ADLS, GCS, and HDFS.
To set up PySpark with Delta Lake, review [the recommendations in Delta Lake's documentation](https://docs.delta.io/latest/quick-start.html#python). You may have to update the `SparkHooks` in your `src/<package_name>/hooks.py` to set up the `SparkSession` with Delta Lake support:

```diff
from kedro.framework.hooks import hook_impl
from pyspark import SparkConf
from pyspark.sql import SparkSession
+ from delta import configure_spark_with_delta_pip

class SparkHooks:
    @hook_impl
    def after_context_created(self, context) -> None:
        """Initialises a SparkSession using the config
        defined in project's conf folder.
        """

        # Load the spark configuration in spark.yaml using the config loader
        parameters = context.config_loader["spark"]
        spark_conf = SparkConf().setAll(parameters.items())

        # Initialise the spark session
        spark_session_conf = (
            SparkSession.builder.appName(context.project_path.name)
            .enableHiveSupport()
            .config(conf=spark_conf)
        )
-       _spark_session = spark_session_conf.getOrCreate()
+       _spark_session = configure_spark_with_delta_pip(spark_session_conf).getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")
```

Refer to the more detailed section on Kedro and Delta Lake integration in the [Delta Lake integration guide](./deltalake_versioning.md).

## Use `MemoryDataset` for intermediary `DataFrame`

For nodes operating on `DataFrame` that doesn't need to perform Spark actions such as writing the `DataFrame` to storage, we recommend using the default `MemoryDataset` to hold the `DataFrame`. In other words, there is no need to specify it in the `DataCatalog` or `catalog.yml`. This allows you to take advantage of Spark's optimiser and lazy evaluation.

## Use `MemoryDataset` with `copy_mode="assign"` for non-`DataFrame` Spark objects

Sometimes, you might want to use Spark objects that aren't `DataFrame` as inputs and outputs in your pipeline. For example, suppose you have a `train_model` node to train a classifier using the Spark ML [`RandomForestClassifier`](https://spark.apache.org/docs/latest/ml-classification-regression.html#random-forest-classifier) and a `predict` node to make predictions using this classifier. In this scenario, the `train_model` node will output a `RandomForestClassifier` object, which then becomes the input for the `predict` node. Below is the code for this pipeline:

```python
from typing import Any, Dict

from kedro.pipeline import Node, Pipeline
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
    return Pipeline(
        [
            Node(train_model, inputs=["training_data"], outputs="example_classifier"),
            Node(
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
  type: MemoryDataset
  copy_mode: assign
```

The `assign` copy mode ensures that the `MemoryDataset` will be assigned the Spark object itself, not a [deep copy](https://docs.python.org/3/library/copy.html) version of it, since deep copy doesn't work with Spark object generally.

## Tips for maximising concurrency using `ThreadRunner`

Under the hood, every Kedro node that performs a Spark action (for example, `save`, `collect`) is submitted to the Spark cluster as a Spark job through the same `SparkSession` instance. These jobs may be running concurrently if they were submitted by different threads. To do that, you will need to run your Kedro pipeline with the [kedro.runner.ThreadRunner][]:

```bash
kedro run --runner=ThreadRunner
```

To further increase the concurrency level, if you are using Spark >= 0.8, you can also give each node an equal share of the Spark cluster by turning on fair sharing. This setting gives nodes a better chance of being executed concurrently.

By default, Spark uses FIFO scheduling, so a job that consumes excessive resources can block other jobs. To enable fair scheduling, configure the `spark.scheduler.mode` option in your local PySpark settings file.

For more information, see the Spark documentation on [jobs scheduling within an application](https://spark.apache.org/docs/latest/job-scheduling.html#scheduling-within-an-application).
