# Working with PySpark

> *Note:* This documentation is based on `Kedro 0.14.2`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

In this tutorial we explain how to work with `PySpark` in a Kedro pipeline.

Relevant API documentation: [SparkDataSet](/kedro.contrib.io.pyspark.SparkDataSet), [SparkJDBCDataSet](/kedro.contrib.io.pyspark.SparkJDBCDataSet)

## Initialising a `SparkSession`

Before any `PySpark` operations are performed, you should initialise your `SparkSession`, typically in your application's entry point before running the pipeline.

For example, if you are using Kedro's project template, then you could create a function `init_spark_session()` in `src/<your_project_name>/run.py` as follows:

```python
from pyspark.sql import SparkSession
from kedro.config import ConfigLoader
from kedro.runner import SequentialRunner

# ...

def init_spark_session(aws_access_key, aws_secret_key):
    # select only/add more config options as per your needs
    return (
        SparkSession.builder.master("local[*]")
        .appName("kedro")
        .config("spark.driver.memory", "4g")
        .config("spark.driver.maxResultSize", "3g")
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
        .config("spark.sql.execution.arrow.enabled", "true")
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:2.7.5")
        .config("spark.jars.excludes", "joda-time:joda-time")
        .config("fs.s3a.access.key", aws_access_key)
        .config("fs.s3a.secret.key", aws_secret_key)
        .getOrCreate()
    )

def main():

    # ...

    config = ConfigLoader(["conf/base", "conf/local"])
    credentials = config.get("credentials*", "credentials*/**")
    
    # Initialise SparkSession
    spark = init_spark_session(credentials["aws"]["access_key"],
                               credentials["aws"]["secret_key"])

    # Run the pipeline
    io.add_feed_dict({'parameters': parameters}, replace=True)
    SequentialRunner().run(pipeline, io)
```

Since `SparkSession` is a [singleton](https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html), the next time you call `SparkSession.builder.getOrCreate()` you will be provided with the same `SparkSession` you initialised at your app's entry point.


## Creating a `SparkDataSet`

Having created a `SparkSession`, you can load your data using `PySpark`'s [DataFrameReader](https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrameReader). 

To do so, please use the provided [SparkDataSet](/kedro.contrib.io.pyspark.SparkDataSet):

### Code API

```python
import pyspark.sql
from kedro.io import DataCatalog
from kedro.contrib.io.pyspark import SparkDataSet

spark_ds = SparkDataSet(
    filepath="s3a://your_bucket/data/01_raw/weather*",
    file_format="csv",
    load_args={"header": True, "inferSchema": True},
    save_args={"sep": "|", "header": True},
    
)
catalog = DataCatalog({"weather": spark_ds})

df = catalog.load("weather")
assert isinstance(df, pyspark.sql.DataFrame)
```

### YAML API

In `catalog.yml`:
```yaml
weather:
  type: kedro.contrib.io.pyspark.SparkDataSet
  filepath: s3a://your_bucket/data/01_raw/weather*
  file_format: csv
  load_args:
    header: True
    inferSchema: True
  save_args:
    sep: '|'
    header: True
```

In `run.py`:

```python
import pyspark.sql
from kedro.io import DataCatalog
from kedro.config import ConfigLoader

config = ConfigLoader(["conf/base", "conf/local"])
catalog = DataCatalog.from_config(
    config.get("catalog*", "catalog*/**"),
    config.get("credentials*", "credentials*/**"),
)
df = catalog.load("weather")
assert isinstance(df, pyspark.sql.DataFrame)
```

## Working with PySpark and Kedro pipelines

Continuing from the example of the previous section, since `catalog.load("weather")` returns a `pyspark.sql.DataFrame`, any Kedro pipeline nodes which have `weather` as an input will be provided with a `PySpark` dataframe:

```python
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node
from kedro.config import ConfigLoader
from kedro.runner import SequentialRunner


def my_node(weather):
   weather.show()  # weather is a pyspark.sql.DataFrame

def main():
    config = ConfigLoader(["conf/base", "conf/local"])
    io = DataCatalog.from_config(
        config.get("catalog*", "catalog*/**"),
        config.get("credentials*", "credentials*/**"),
    )
    pipeline = Pipeline([node(my_node, "weather", None)])
    SequentialRunner().run(pipeline, io)
```
