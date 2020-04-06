# Working with PySpark

> *Note:* This documentation is based on `Kedro 0.15.9`, if you spot anything that is incorrect then please create an [issue](https://github.com/quantumblacklabs/kedro/issues) or pull request.

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
        self._spark_session = None
        self.init_spark_session()

    def init_spark_session(self, yarn=True) -> None:
        """Initialises a SparkSession using the config defined in project's conf folder."""

        if self._spark_session:
            return self._spark_session
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
            self._spark_session = spark_session_conf.master("yarn").getOrCreate()
        else:
            self._spark_session = spark_session_conf.getOrCreate()

        self._spark_session.sparkContext.setLogLevel("WARN")

    project_name = "kedro"
    project_version = "0.15.9"


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


Since `SparkSession` is a [singleton](https://python-3-patterns-idioms-test.readthedocs.io/en/latest/Singleton.html), the next time you call `SparkSession.builder.getOrCreate()` you will be provided with the same `SparkSession` you initialised at your app's entry point.

## Creating a `SparkDataSet`

Having created a `SparkSession`, you can load your data using `PySpark`'s [DataFrameReader](https://spark.apache.org/docs/latest/api/python/pyspark.sql.html#pyspark.sql.DataFrameReader).

To do so, please use the provided [SparkDataSet](/kedro.contrib.io.pyspark.SparkDataSet):

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
