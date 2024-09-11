from time import sleep
from typing import Dict

from kedro.framework.hooks import hook_impl
from kedro.pipeline import Pipeline
from pyspark import SparkConf
from pyspark.sql import SparkSession


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
        sleep(context.params['hook_delay'])
        _spark_session = spark_session_conf.getOrCreate()
        _spark_session.sparkContext.setLogLevel("WARN")


def register_pipelines(self) -> Dict[str, Pipeline]:
    from performance_test.pipelines.expense_analysis import (
        pipeline as expense_analysis_pipeline,
    )

    return {
        "__default__": expense_analysis_pipeline.create_pipeline(),
        "expense_analysis": expense_analysis_pipeline.create_pipeline(),
    }
