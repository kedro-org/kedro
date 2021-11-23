import pytest
from delta import DeltaTable
from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, StringType, StructField, StructType

from kedro.extras.datasets.spark import DeltaTableDataset, SparkDataSet


@pytest.fixture(autouse=True)
def delta_spark_session(spark_session):
    return spark_session


@pytest.fixture
def sample_spark_df():
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )

    data = [("Alex", 31), ("Bob", 12), ("Clarke", 65), ("Dave", 29)]

    return SparkSession.builder.getOrCreate().createDataFrame(data, schema)


class TestDeltaTableDataSet:
    def test_load(self, tmp_path, sample_spark_df):
        filepath = (tmp_path / "data.csv").as_posix()
        spark_ds = SparkDataSet(filepath=filepath, file_format="csv")
        spark_ds.save(sample_spark_df)

        spark_delta_ds = SparkDataSet(
            filepath=filepath, file_format="delta", save_args={"mode": "overwrite"}
        )
        spark_delta_ds.save(sample_spark_df)

        # csv content == delta content

        delta_ds = DeltaTableDataset(filepath=filepath)
        delta_table = delta_ds.load()

        assert isinstance(delta_table, DeltaTable)
        loaded = delta_table.toDF()
        assert loaded.exceptAll(sample_spark_df).count() == 0
