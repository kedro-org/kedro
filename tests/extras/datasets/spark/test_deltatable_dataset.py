import pytest

from kedro.extras.datasets.spark import DeltaTableDataset


@pytest.fixture(autouse=True)
def spark_session_autouse(spark_session):
    # all the tests in this file require Spark
    return spark_session


class TestDeltaTableDataSet:
    def test_load(self, tmp_path):
        temp_path = (tmp_path / "data").as_posix()
        DeltaTableDataset(filepath=temp_path)
