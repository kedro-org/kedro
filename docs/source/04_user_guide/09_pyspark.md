# Working with PySpark

> *Note:* This documentation is based on `Kedro 0.16.1`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

In this tutorial we explain how to work with `PySpark` in a Kedro pipeline.

Relevant API documentation: [SparkDataSet](/kedro.extras.datasets.spark.SparkDataSet), [SparkJDBCDataSet](/kedro.extras.datasets.spark.SparkJDBCDataSet) and [SparkHiveDataSet](/kedro.extras.datasets.spark.SparkHiveDataSet)

## Initialising a `SparkSession`

Before any `PySpark` operations are performed, you should initialise your `SparkSession`, typically in your application's entry point before running the pipeline.

For example, if you are using Kedro's project template, then you could add `init_spark_session()` method to the `ProjectContext` class in `src/<your_project_name>/run.py` as follows:

```python
import getpass
from typing import Any, Dict, Union

from pyspark import SparkConf
from pyspark.sql import SparkSession

# ...


class ProjectContext(KedroContext):
    # ...
    def __init__(
        self,
        project_path: Union[Path, str],
        env: str = None,
        extra_params: Dict[str, Any] = None,
    ):
        super().__init__(project_path, env, extra_params)
        self.init_spark_session()

    def init_spark_session(self, yarn=True) -> None:
        """Initialises a SparkSession using the config defined in project's conf folder."""

        parameters = self.config_loader.get("spark*", "spark*/**")
        spark_conf = SparkConf().setAll(parameters.items())

        spark_session_conf = (
            SparkSession.builder.appName(
                "{}_{}".format(self.project_name, getpass.getuser())
            )
            .enableHiveSupport()
            .config(conf=spark_conf)
        )
        if yarn:
            _spark_session = spark_session_conf.master("yarn").getOrCreate()
        else:
            _spark_session = spark_session_conf.getOrCreate()

        _spark_session.sparkContext.setLogLevel("WARN")

    project_name = "kedro"
    project_version = "0.16.1"


# ...
```

Create `conf/base/spark.yml` and specify the parameters as follows:

```yaml
spark.driver.maxResultSize: 3g
spark.hadoop.fs.s3a.impl: org.apache.hadoop.fs.s3a.S3AFileSystem
spark.sql.execution.arrow.enabled: true
spark.jars.packages: org.apache.hadoop:hadoop-aws:2.7.5
spark.jars.excludes: joda-time:joda-time
```


Since `SparkSession` is a [singleton](https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html), the next time you call `SparkSession.builder.getOrCreate()` you will be provided with the same `SparkSession` you initialised at your app's entry point. We don't recommend storing the session on the context object, as it cannot be deep-copied and therefore prevents the context from being initialised for some plugins.

## Creating a `SparkDataSet`

Having created a `SparkSession`, you can load your data using `PySpark`'s [DataFrameReader](https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrameReader).

To do so, please use the provided [SparkDataSet](/kedro.extras.datasets.spark.SparkDataSet):

### Code API

```python
import pyspark.sql
from kedro.io import DataCatalog
from kedro.extras.datasets.spark import SparkDataSet

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
  type: spark.SparkDataSet
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
from kedro.pipeline import Pipeline, node

def my_node(weather):
    weather.show()  # weather is a pyspark.sql.DataFrame

class ProjectContext(KedroContext):

    # ...

    @property
    def pipeline(self) -> Pipeline:  # requires import from user code
        return Pipeline([node(my_node, "weather", None)])
# ...
```

## Tips for maximising concurrency using `ThreadRunner`

Under the hood, every Kedro node that performs a Spark action (e.g. `save`, `collect`) is submitted to the Spark cluster as a Spark job through the same `SparkSession` instance. These jobs may be running concurrently if they were submitted by different threads. In order to do that, you will need to run your Kedro pipeline with the [ThreadRunner](/kedro.runner.ThreadRunner):

```bash
kedro run --runner=ThreadRunner
```

To further increase the concurrency level, if you are using Spark >= 0.8, you can also give each node a roughly equal share of the Spark cluster by turning on fair sharing and therefore giving them a roughly equal chance of being executed concurrently. By default, they are executed in a FIFO manner, which means if a job takes up too much resources, it could hold up the execution of other jobs. In order to turn on fair sharing, put the following in your `conf/base/spark.yml` file, which was created in the [Initialising a `SparkSession`](#initialising-a-sparksession) section:

```yaml
spark.scheduler.mode: FAIR
```

For more information, please visit Spark documentation on [jobs scheduling within an application](https://spark.apache.org/docs/latest/job-scheduling.html#scheduling-within-an-application).
