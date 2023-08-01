"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""
import pytest
from delta import configure_spark_with_delta_pip
from filelock import FileLock

try:
    from pyspark.sql import SparkSession
except ImportError:  # pragma: no cover
    pass  # this is only for test discovery to succeed on Python 3.8, 3.9


def _setup_spark_session():
    return configure_spark_with_delta_pip(
        SparkSession.builder.appName("MyApp")
        .master("local[*]")
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
        .config(
            "spark.sql.catalog.spark_catalog",
            "org.apache.spark.sql.delta.catalog.DeltaCatalog",
        )
    ).getOrCreate()


@pytest.fixture(scope="module", autouse=True)
def spark_session(tmp_path_factory):
    # When running these spark tests with pytest-xdist, we need to make sure
    # that the spark session setup on each test process don't interfere with each other.
    # Therefore, we block the process during the spark session setup.
    # Locking procedure comes from pytest-xdist's own recommendation:
    # https://github.com/pytest-dev/pytest-xdist#making-session-scoped-fixtures-execute-only-once
    root_tmp_dir = tmp_path_factory.getbasetemp().parent
    lock = root_tmp_dir / "semaphore.lock"
    with FileLock(lock):
        spark = _setup_spark_session()
    yield spark
    spark.stop()
