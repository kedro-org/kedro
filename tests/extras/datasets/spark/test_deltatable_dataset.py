import gc

import pytest
from delta import DeltaTable, configure_spark_with_delta_pip
from psutil import Popen
from pyspark import SparkContext
from pyspark.sql import SparkSession
from pyspark.sql.types import IntegerType, StringType, StructField, StructType
from pyspark.sql.utils import AnalysisException

from kedro.extras.datasets.spark import DeltaTableDataSet, SparkDataSet
from kedro.io import DataCatalog, DataSetError
from kedro.pipeline import Pipeline, node
from kedro.runner import ParallelRunner
from tests.extras.datasets.spark.conftest import UseTheSparkSessionFixtureOrMock


# clean up pyspark after the test module finishes
@pytest.fixture(scope="module", autouse=True)
def delta_spark_session(replace_spark_default_getorcreate):
    SparkSession.builder.getOrCreate = replace_spark_default_getorcreate

    try:
        # As recommended in https://docs.delta.io/latest/quick-start.html#python
        builder = (
            SparkSession.builder.appName("MyApp")
            .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension")
            .config(
                "spark.sql.catalog.spark_catalog",
                "org.apache.spark.sql.delta.catalog.DeltaCatalog",
            )
        )

        spark = configure_spark_with_delta_pip(builder).getOrCreate()

        yield spark

        # This fixture should be a dependency of other fixtures dealing with spark delta data
        # in this module so that it always exits last and stops the spark session
        # after tests are finished.
        spark.stop()
    except PermissionError:  # pragma: no cover
        # On Windows machine TemporaryDirectory can't be removed because some
        # files are still used by Java process.
        pass

    SparkSession.builder.getOrCreate = UseTheSparkSessionFixtureOrMock

    # remove the cached JVM vars
    SparkContext._jvm = None  # pylint: disable=protected-access
    SparkContext._gateway = None  # pylint: disable=protected-access

    # py4j doesn't shutdown properly so kill the actual JVM process
    for obj in gc.get_objects():
        try:
            if isinstance(obj, Popen) and "pyspark" in obj.args[0]:
                obj.terminate()  # pragma: no cover
        except ReferenceError:  # pragma: no cover
            # gc.get_objects may return dead weak proxy objects that will raise
            # ReferenceError when you isinstance them
            pass


@pytest.fixture
def sample_spark_df(delta_spark_session):
    schema = StructType(
        [
            StructField("name", StringType(), True),
            StructField("age", IntegerType(), True),
        ]
    )

    data = [("Alex", 31), ("Bob", 12), ("Clarke", 65), ("Dave", 29)]

    return delta_spark_session.createDataFrame(data, schema)


class TestDeltaTableDataSet:
    def test_load(self, tmp_path, sample_spark_df):
        filepath = (tmp_path / "test_data").as_posix()
        spark_delta_ds = SparkDataSet(filepath=filepath, file_format="delta")
        spark_delta_ds.save(sample_spark_df)
        loaded_with_spark = spark_delta_ds.load()
        assert loaded_with_spark.exceptAll(sample_spark_df).count() == 0

        delta_ds = DeltaTableDataSet(filepath=filepath)
        delta_table = delta_ds.load()

        assert isinstance(delta_table, DeltaTable)
        loaded_with_deltalake = delta_table.toDF()
        assert loaded_with_deltalake.exceptAll(loaded_with_spark).count() == 0

    def test_save(self, tmp_path, sample_spark_df, caplog):
        filepath = (tmp_path / "test_data").as_posix()
        delta_ds = DeltaTableDataSet(filepath=filepath)
        assert not delta_ds.exists()

        delta_ds.save(sample_spark_df)
        # save is a dummy operation, check that indeed nothing is written
        assert not delta_ds.exists()

        log_messages = [r.getMessage() for r in caplog.records]
        expected_log_message = (
            "Saving was performed on `DeltaTable` object "
            "within the context of the node function"
        )
        assert expected_log_message in log_messages

    def test_exists(self, tmp_path, sample_spark_df):
        filepath = (tmp_path / "test_data").as_posix()
        delta_ds = DeltaTableDataSet(filepath=filepath)

        assert not delta_ds.exists()

        spark_delta_ds = SparkDataSet(filepath=filepath, file_format="delta")
        spark_delta_ds.save(sample_spark_df)

        assert delta_ds.exists()

    def test_exists_raises_error(self, mocker):
        delta_ds = DeltaTableDataSet(filepath="")
        mocker.patch.object(
            delta_ds, "_get_spark", side_effect=AnalysisException("Other Exception", [])
        )

        with pytest.raises(DataSetError, match="Other Exception"):
            delta_ds.exists()

    @pytest.mark.parametrize("is_async", [False, True])
    def test_parallel_runner(self, is_async):
        """Test ParallelRunner with SparkDataSet fails."""

        def no_output(x):
            _ = x + 1  # pragma: no cover

        delta_ds = DeltaTableDataSet(filepath="")
        catalog = DataCatalog(data_sets={"delta_in": delta_ds})
        pipeline = Pipeline([node(no_output, "delta_in", None)])
        pattern = (
            r"The following data sets cannot be used with "
            r"multiprocessing: \['delta_in'\]"
        )
        with pytest.raises(AttributeError, match=pattern):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)


class TestSparkDataSetWithDeltaFormat:
    def test_exists(self, tmp_path, sample_spark_df):
        # testing SparkDataSet with delta here as we have a
        # properly set-up SparkSession to work with Delta Lake
        filepath = (tmp_path / "test_data").as_posix()
        spark_data_set = SparkDataSet(filepath=filepath, file_format="delta")

        assert not spark_data_set.exists()

        spark_data_set.save(sample_spark_df)
        assert spark_data_set.exists()
