"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""
import gc
from subprocess import Popen

import pytest

try:
    from pyspark import SparkContext
    from pyspark.sql import SparkSession
except ImportError:  # pragma: no cover
    pass  # this is only for test discovery to succeed on Python 3.8

the_real_getOrCreate = None


class UseTheSparkSessionFixtureOrMock:  # pylint: disable=too-few-public-methods
    pass


# prevent using spark without going through the spark_session fixture
@pytest.fixture(scope="session", autouse=True)
def replace_spark_default_getorcreate():
    global the_real_getOrCreate  # pylint: disable=global-statement
    the_real_getOrCreate = SparkSession.builder.getOrCreate
    SparkSession.builder.getOrCreate = UseTheSparkSessionFixtureOrMock
    return the_real_getOrCreate


# clean up pyspark after the test module finishes
@pytest.fixture(scope="module")
def spark_session():  # SKIP_IF_NO_SPARK
    SparkSession.builder.getOrCreate = the_real_getOrCreate
    spark = (
        SparkSession.builder.config(
            "spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension"
        )
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
        .config(
            "spark.jars.packages",
            "io.delta:delta-core_2.12:1.0.0",
        )
        .getOrCreate()
    )
    yield spark
    spark.stop()
    SparkSession.builder.getOrCreate = UseTheSparkSessionFixtureOrMock

    # remove the cached JVM vars
    SparkContext._jvm = None  # pylint: disable=protected-access
    SparkContext._gateway = None  # pylint: disable=protected-access

    # py4j doesn't shutdown properly so kill the actual JVM process
    for obj in gc.get_objects():
        try:
            if isinstance(obj, Popen) and "pyspark" in obj.args[0]:
                obj.terminate()
        except ReferenceError:  # pragma: no cover
            # gc.get_objects may return dead weak proxy objects that will raise
            # ReferenceError when you isinstance them
            pass
