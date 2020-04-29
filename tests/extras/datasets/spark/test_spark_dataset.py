# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=import-error
import tempfile
from pathlib import Path, PurePosixPath, PureWindowsPath

import pandas as pd
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col  # pylint: disable=no-name-in-module
from pyspark.sql.types import IntegerType, StringType, StructField, StructType
from pyspark.sql.utils import AnalysisException

from kedro.extras.datasets.pandas import CSVDataSet, ParquetDataSet
from kedro.extras.datasets.pickle import PickleDataSet
from kedro.extras.datasets.spark import SparkDataSet
from kedro.extras.datasets.spark.spark_dataset import _dbfs_glob, _get_dbutils
from kedro.io import DataCatalog, DataSetError, Version
from kedro.io.core import generate_timestamp
from kedro.pipeline import Pipeline, node
from kedro.runner import ParallelRunner, SequentialRunner

FOLDER_NAME = "fake_folder"
FILENAME = "test.parquet"
BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)

HDFS_PREFIX = "{}/{}".format(FOLDER_NAME, FILENAME)
HDFS_FOLDER_STRUCTURE = [
    (
        HDFS_PREFIX,
        [
            "2019-01-01T23.59.59.999Z",
            "2019-01-02T00.00.00.000Z",
            "2019-01-02T00.00.00.001Z",
            "2019-01-02T01.00.00.000Z",
            "2019-02-01T00.00.00.000Z",
        ],
        [],
    ),
    (HDFS_PREFIX + "/2019-01-01T23.59.59.999Z", [FILENAME], []),
    (HDFS_PREFIX + "/2019-01-01T23.59.59.999Z/" + FILENAME, [], ["part1", "part2"]),
    (HDFS_PREFIX + "/2019-01-02T00.00.00.000Z", [], ["other_file"]),
    (HDFS_PREFIX + "/2019-01-02T00.00.00.001Z", [], []),
    (HDFS_PREFIX + "/2019-01-02T01.00.00.000Z", [FILENAME], []),
    (HDFS_PREFIX + "/2019-01-02T01.00.00.000Z/" + FILENAME, [], ["part1"]),
    (HDFS_PREFIX + "/2019-02-01T00.00.00.000Z", [], ["other_file"]),
]


@pytest.fixture(autouse=True)
def spark_session_autouse(spark_session):
    # all the tests in this file require Spark
    return spark_session


@pytest.fixture
def sample_pandas_df() -> pd.DataFrame:
    return pd.DataFrame(
        {"Name": ["Alex", "Bob", "Clarke", "Dave"], "Age": [31, 12, 65, 29]}
    )


@pytest.fixture
def version():
    load_version = None  # use latest
    save_version = generate_timestamp()  # freeze save version
    return Version(load_version, save_version)


@pytest.fixture
def versioned_dataset_local(tmp_path, version):
    return SparkDataSet(filepath=str(tmp_path / FILENAME), version=version)


@pytest.fixture
def versioned_dataset_dbfs(tmp_path, version):
    return SparkDataSet(filepath="/dbfs" + str(tmp_path / FILENAME), version=version)


@pytest.fixture
def versioned_dataset_s3(version):
    return SparkDataSet(
        filepath="s3a://{}/{}".format(BUCKET_NAME, FILENAME),
        version=version,
        credentials=AWS_CREDENTIALS,
    )


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


def identity(arg):
    return arg  # pragma: no cover


@pytest.fixture
def spark_in(tmp_path, sample_spark_df):
    spark_in = SparkDataSet(filepath=str(tmp_path / "input"))
    spark_in.save(sample_spark_df)
    return spark_in


class FileInfo:
    def __init__(self, path):
        self.path = "dbfs:" + path

    def isDir(self):
        return "." not in self.path.split("/")[-1]


class TestSparkDataSet:
    def test_load_parquet(self, tmp_path, sample_pandas_df):
        temp_path = str(tmp_path / "data")
        local_parquet_set = ParquetDataSet(filepath=temp_path)
        local_parquet_set.save(sample_pandas_df)
        spark_data_set = SparkDataSet(filepath=temp_path)
        spark_df = spark_data_set.load()
        assert spark_df.count() == 4

    def test_save_parquet(self, tmp_path, sample_spark_df):
        # To cross check the correct Spark save operation we save to
        # a single spark partition and retrieve it with Kedro
        # ParquetDataSet
        temp_dir = Path(str(tmp_path / "test_data"))
        spark_data_set = SparkDataSet(
            filepath=str(temp_dir), save_args={"compression": "none"}
        )
        spark_df = sample_spark_df.coalesce(1)
        spark_data_set.save(spark_df)

        single_parquet = [
            f for f in temp_dir.iterdir() if f.is_file() and f.name.startswith("part")
        ][0]

        local_parquet_data_set = ParquetDataSet(filepath=str(single_parquet))

        pandas_df = local_parquet_data_set.load()

        assert pandas_df[pandas_df["name"] == "Bob"]["age"].iloc[0] == 12

    def test_load_options_csv(self, tmp_path, sample_pandas_df):
        filepath = str(tmp_path / "data")
        local_csv_data_set = CSVDataSet(filepath=filepath)
        local_csv_data_set.save(sample_pandas_df)
        spark_data_set = SparkDataSet(
            filepath=filepath, file_format="csv", load_args={"header": True}
        )
        spark_df = spark_data_set.load()
        assert spark_df.filter(col("Name") == "Alex").count() == 1

    def test_save_options_csv(self, tmp_path, sample_spark_df):
        # To cross check the correct Spark save operation we save to
        # a single spark partition with csv format and retrieve it with Kedro
        # CSVDataSet
        temp_dir = Path(str(tmp_path / "test_data"))
        spark_data_set = SparkDataSet(
            filepath=str(temp_dir),
            file_format="csv",
            save_args={"sep": "|", "header": True},
        )
        spark_df = sample_spark_df.coalesce(1)
        spark_data_set.save(spark_df)

        single_csv_file = [
            f for f in temp_dir.iterdir() if f.is_file() and f.suffix == ".csv"
        ][0]

        csv_local_data_set = CSVDataSet(
            filepath=str(single_csv_file), load_args={"sep": "|"}
        )
        pandas_df = csv_local_data_set.load()

        assert pandas_df[pandas_df["name"] == "Alex"]["age"][0] == 31

    def test_str_representation(self):
        with tempfile.NamedTemporaryFile() as temp_data_file:
            spark_data_set = SparkDataSet(
                filepath=temp_data_file.name,
                file_format="csv",
                load_args={"header": True},
            )
            assert "SparkDataSet" in str(spark_data_set)
            assert "filepath={}".format(temp_data_file.name) in str(spark_data_set)

    def test_save_overwrite_fail(self, tmp_path, sample_spark_df):
        # Writes a data frame twice and expects it to fail.
        filepath = str(tmp_path / "test_data")
        spark_data_set = SparkDataSet(filepath=filepath)
        spark_data_set.save(sample_spark_df)

        with pytest.raises(DataSetError):
            spark_data_set.save(sample_spark_df)

    def test_save_overwrite_mode(self, tmp_path, sample_spark_df):
        # Writes a data frame in overwrite mode.
        filepath = str(tmp_path / "test_data")
        spark_data_set = SparkDataSet(
            filepath=filepath, save_args={"mode": "overwrite"}
        )

        spark_data_set.save(sample_spark_df)
        spark_data_set.save(sample_spark_df)

    def test_save_partition(self, tmp_path, sample_spark_df):
        # To verify partitioning this test will partition the data by one
        # of the columns and then check whether partitioned column is added
        # to the save path

        filepath = Path(str(tmp_path / "test_data"))
        spark_data_set = SparkDataSet(
            filepath=str(filepath),
            save_args={"mode": "overwrite", "partitionBy": ["name"]},
        )

        spark_data_set.save(sample_spark_df)

        expected_path = filepath / "name=Alex"

        assert expected_path.exists()

    @pytest.mark.parametrize("file_format", ["csv", "parquet"])
    def test_exists(self, file_format, tmp_path, sample_spark_df):
        filepath = str(tmp_path / "test_data")
        spark_data_set = SparkDataSet(filepath=filepath, file_format=file_format)

        assert not spark_data_set.exists()

        spark_data_set.save(sample_spark_df)
        assert spark_data_set.exists()

    def test_exists_raises_error(self, mocker):
        # exists should raise all errors except for
        # AnalysisExceptions clearly indicating a missing file
        spark_data_set = SparkDataSet(filepath="")
        mocker.patch.object(
            spark_data_set,
            "_get_spark",
            side_effect=AnalysisException("Other Exception", []),
        )

        with pytest.raises(DataSetError, match="Other Exception"):
            spark_data_set.exists()

    @pytest.mark.parametrize("is_async", [False, True])
    def test_parallel_runner(self, is_async, spark_in):
        """Test ParallelRunner with SparkDataSet fails.
        """
        catalog = DataCatalog(data_sets={"spark_in": spark_in})
        pipeline = Pipeline([node(identity, "spark_in", "spark_out")])
        pattern = r"The following data_sets cannot be serialized: \['spark_in'\]"
        with pytest.raises(AttributeError, match=pattern):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)


class TestSparkDataSetVersionedLocal:
    def test_no_version(self, versioned_dataset_local):
        pattern = r"Did not find any versions for SparkDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_dataset_local.load()

    def test_load_latest(self, versioned_dataset_local, sample_spark_df):
        versioned_dataset_local.save(sample_spark_df)
        reloaded = versioned_dataset_local.load()

        assert reloaded.exceptAll(sample_spark_df).count() == 0

    def test_load_exact(self, tmp_path, sample_spark_df):
        ts = generate_timestamp()
        ds_local = SparkDataSet(
            filepath=str(tmp_path / FILENAME), version=Version(ts, ts)
        )

        ds_local.save(sample_spark_df)
        reloaded = ds_local.load()

        assert reloaded.exceptAll(sample_spark_df).count() == 0

    def test_save(self, versioned_dataset_local, version, tmp_path, sample_spark_df):
        versioned_dataset_local.save(sample_spark_df)
        assert (tmp_path / FILENAME / version.save / FILENAME).exists()

    def test_repr(self, versioned_dataset_local, tmp_path, version):
        assert "version=Version(load=None, save='{}')".format(version.save) in str(
            versioned_dataset_local
        )

        dataset_local = SparkDataSet(filepath=str(tmp_path / FILENAME))
        assert "version=" not in str(dataset_local)

    def test_save_version_warning(self, tmp_path, sample_spark_df):
        exact_version = Version("2019-01-01T23.59.59.999Z", "2019-01-02T00.00.00.000Z")
        ds_local = SparkDataSet(
            filepath=str(tmp_path / FILENAME), version=exact_version
        )

        pattern = (
            r"Save version `{ev.save}` did not match load version "
            r"`{ev.load}` for SparkDataSet\(.+\)".format(ev=exact_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            ds_local.save(sample_spark_df)

    def test_prevent_overwrite(self, tmp_path, version, sample_spark_df):
        versioned_local = SparkDataSet(
            filepath=str(tmp_path / FILENAME),
            version=version,
            # second save should fail even in overwrite mode
            save_args={"mode": "overwrite"},
        )
        versioned_local.save(sample_spark_df)

        pattern = (
            r"Save path `.+` for SparkDataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_local.save(sample_spark_df)


class TestSparkDataSetVersionedDBFS:
    def test_load_latest(  # pylint: disable=too-many-arguments
        self, mocker, versioned_dataset_dbfs, version, tmp_path, sample_spark_df
    ):
        mocked_glob = mocker.patch.object(versioned_dataset_dbfs, "_glob_function")
        mocked_glob.return_value = [str(tmp_path / FILENAME / version.save / FILENAME)]

        versioned_dataset_dbfs.save(sample_spark_df)
        reloaded = versioned_dataset_dbfs.load()

        expected_calls = [
            mocker.call("/dbfs" + str(tmp_path / FILENAME / "*" / FILENAME))
        ]
        assert mocked_glob.call_args_list == expected_calls

        assert reloaded.exceptAll(sample_spark_df).count() == 0

    def test_load_exact(self, tmp_path, sample_spark_df):
        ts = generate_timestamp()
        ds_dbfs = SparkDataSet(
            filepath="/dbfs" + str(tmp_path / FILENAME), version=Version(ts, ts)
        )

        ds_dbfs.save(sample_spark_df)
        reloaded = ds_dbfs.load()

        assert reloaded.exceptAll(sample_spark_df).count() == 0

    def test_save(  # pylint: disable=too-many-arguments
        self, mocker, versioned_dataset_dbfs, version, tmp_path, sample_spark_df
    ):
        mocked_glob = mocker.patch.object(versioned_dataset_dbfs, "_glob_function")
        mocked_glob.return_value = [str(tmp_path / FILENAME / version.save / FILENAME)]

        versioned_dataset_dbfs.save(sample_spark_df)

        mocked_glob.assert_called_once_with(
            "/dbfs" + str(tmp_path / FILENAME / "*" / FILENAME)
        )
        assert (tmp_path / FILENAME / version.save / FILENAME).exists()

    def test_exists(  # pylint: disable=too-many-arguments
        self, mocker, versioned_dataset_dbfs, version, tmp_path, sample_spark_df
    ):
        mocked_glob = mocker.patch.object(versioned_dataset_dbfs, "_glob_function")
        mocked_glob.return_value = [str(tmp_path / FILENAME / version.save / FILENAME)]

        assert not versioned_dataset_dbfs.exists()

        versioned_dataset_dbfs.save(sample_spark_df)
        assert versioned_dataset_dbfs.exists()

        expected_calls = [
            mocker.call("/dbfs" + str(tmp_path / FILENAME / "*" / FILENAME))
        ] * 2
        assert mocked_glob.call_args_list == expected_calls

    def test_dbfs_glob(self, mocker):
        dbutils_mock = mocker.Mock()
        dbutils_mock.fs.ls.return_value = [
            FileInfo("/tmp/file/date1"),
            FileInfo("/tmp/file/date2"),
            FileInfo("/tmp/file/file.csv"),
            FileInfo("/tmp/file/"),
        ]
        pattern = "/tmp/file/*/file"
        expected = ["/dbfs/tmp/file/date1/file", "/dbfs/tmp/file/date2/file"]

        result = _dbfs_glob(pattern, dbutils_mock)
        assert result == expected
        dbutils_mock.fs.ls.assert_called_once_with("/tmp/file")

    def test_ds_init_no_dbutils(self, mocker):
        get_dbutils_mock = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset._get_dbutils", return_value=None
        )

        data_set = SparkDataSet(filepath="/dbfs/tmp/data")

        get_dbutils_mock.assert_called_once()
        assert data_set._glob_function.__name__ == "iglob"

    def test_ds_init_dbutils_available(self, mocker):
        get_dbutils_mock = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset._get_dbutils",
            return_value="mock",
        )

        data_set = SparkDataSet(filepath="/dbfs/tmp/data")

        get_dbutils_mock.assert_called_once()
        assert data_set._glob_function.__class__.__name__ == "partial"
        assert data_set._glob_function.func.__name__ == "_dbfs_glob"
        assert data_set._glob_function.keywords == {
            "dbutils": get_dbutils_mock.return_value
        }

    def test_get_dbutils_from_globals(self, mocker):
        mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.globals",
            return_value={"dbutils": "dbutils_from_globals"},
        )
        assert _get_dbutils("spark") == "dbutils_from_globals"

    def test_get_dbutils_from_pyspark(self, mocker):
        dbutils_mock = mocker.Mock()
        dbutils_mock.DBUtils.return_value = "dbutils_from_pyspark"
        mocker.patch.dict("sys.modules", {"pyspark.dbutils": dbutils_mock})
        assert _get_dbutils("spark") == "dbutils_from_pyspark"
        dbutils_mock.DBUtils.assert_called_once_with("spark")

    def test_get_dbutils_from_ipython(self, mocker):
        ipython_mock = mocker.Mock()
        ipython_mock.get_ipython.return_value.user_ns = {
            "dbutils": "dbutils_from_ipython"
        }
        mocker.patch.dict("sys.modules", {"IPython": ipython_mock})
        assert _get_dbutils("spark") == "dbutils_from_ipython"
        ipython_mock.get_ipython.assert_called_once_with()

    def test_get_dbutils_no_modules(self, mocker):
        mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.globals", return_value={}
        )
        mocker.patch.dict("sys.modules", {})
        assert _get_dbutils("spark") is None

    @pytest.mark.parametrize(
        "os_name,path_class", [("nt", PureWindowsPath), ("posix", PurePosixPath)]
    )
    def test_regular_path_in_different_os(self, os_name, path_class, mocker):
        """Check that class of filepath depends on OS for regular path."""
        mocker.patch("os.name", os_name)
        data_set = SparkDataSet(filepath="/some/path")
        assert isinstance(data_set._filepath, path_class)

    @pytest.mark.parametrize(
        "os_name,path_class", [("nt", PurePosixPath), ("posix", PurePosixPath)]
    )
    def test_dbfs_path_in_different_os(self, os_name, path_class, mocker):
        """Check that class of filepath doesn't depend on OS if it references DBFS."""
        mocker.patch("os.name", os_name)
        data_set = SparkDataSet(filepath="/dbfs/some/path")
        assert isinstance(data_set._filepath, path_class)


class TestSparkDataSetVersionedS3:
    def test_no_version(self, versioned_dataset_s3):
        pattern = r"Did not find any versions for SparkDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_dataset_s3.load()

    def test_load_latest(self, mocker, versioned_dataset_s3):
        get_spark = mocker.patch.object(versioned_dataset_s3, "_get_spark")
        mocked_glob = mocker.patch.object(versioned_dataset_s3, "_glob_function")
        mocked_glob.return_value = [
            "{b}/{f}/{v}/{f}".format(b=BUCKET_NAME, f=FILENAME, v="mocked_version")
        ]
        mocker.patch.object(versioned_dataset_s3, "_exists_function", return_value=True)

        versioned_dataset_s3.load()

        mocked_glob.assert_called_once_with(
            "{b}/{f}/*/{f}".format(b=BUCKET_NAME, f=FILENAME)
        )
        get_spark.return_value.read.load.assert_called_once_with(
            "s3a://{b}/{f}/{v}/{f}".format(
                b=BUCKET_NAME, f=FILENAME, v="mocked_version"
            ),
            "parquet",
        )

    def test_load_exact(self, mocker):
        ts = generate_timestamp()
        ds_s3 = SparkDataSet(
            filepath="s3a://{}/{}".format(BUCKET_NAME, FILENAME),
            version=Version(ts, None),
            credentials=AWS_CREDENTIALS,
        )
        get_spark = mocker.patch.object(ds_s3, "_get_spark")

        ds_s3.load()

        get_spark.return_value.read.load.assert_called_once_with(
            "s3a://{b}/{f}/{v}/{f}".format(b=BUCKET_NAME, f=FILENAME, v=ts), "parquet"
        )

    def test_save(self, versioned_dataset_s3, version, mocker):
        mocked_spark_df = mocker.Mock()

        # need resolve_load_version() call to return a load version that
        # matches save version due to consistency check in versioned_dataset_s3.save()
        mocker.patch.object(
            versioned_dataset_s3, "resolve_load_version", return_value=version.save
        )

        versioned_dataset_s3.save(mocked_spark_df)
        mocked_spark_df.write.save.assert_called_once_with(
            "s3a://{b}/{f}/{v}/{f}".format(b=BUCKET_NAME, f=FILENAME, v=version.save),
            "parquet",
        )

    def test_save_version_warning(self, mocker):
        exact_version = Version("2019-01-01T23.59.59.999Z", "2019-01-02T00.00.00.000Z")
        ds_s3 = SparkDataSet(
            filepath="s3a://{}/{}".format(BUCKET_NAME, FILENAME),
            version=exact_version,
            credentials=AWS_CREDENTIALS,
        )
        mocked_spark_df = mocker.Mock()

        pattern = (
            r"Save version `{ev.save}` did not match load version "
            r"`{ev.load}` for SparkDataSet\(.+\)".format(ev=exact_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            ds_s3.save(mocked_spark_df)
        mocked_spark_df.write.save.assert_called_once_with(
            "s3a://{b}/{f}/{v}/{f}".format(
                b=BUCKET_NAME, f=FILENAME, v=exact_version.save
            ),
            "parquet",
        )

    def test_prevent_overwrite(self, mocker, versioned_dataset_s3):
        mocked_spark_df = mocker.Mock()
        mocker.patch.object(versioned_dataset_s3, "_exists_function", return_value=True)

        pattern = (
            r"Save path `.+` for SparkDataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_dataset_s3.save(mocked_spark_df)

        mocked_spark_df.write.save.assert_not_called()

    def test_s3n_warning(self, version):
        pattern = (
            "`s3n` filesystem has now been deprecated by Spark, "
            "please consider switching to `s3a`"
        )
        with pytest.warns(DeprecationWarning, match=pattern):
            SparkDataSet(
                filepath="s3n://{}/{}".format(BUCKET_NAME, FILENAME), version=version
            )

    def test_repr(self, versioned_dataset_s3, version):
        assert "filepath=s3a://" in str(versioned_dataset_s3)
        assert "version=Version(load=None, save='{}')".format(version.save) in str(
            versioned_dataset_s3
        )

        dataset_s3 = SparkDataSet(filepath="s3a://{}/{}".format(BUCKET_NAME, FILENAME))
        assert "filepath=s3a://" in str(dataset_s3)
        assert "version=" not in str(dataset_s3)


class TestSparkDataSetVersionedHdfs:
    def test_no_version(self, mocker, version):
        hdfs_walk = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.InsecureClient.walk"
        )
        hdfs_walk.return_value = []

        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )

        pattern = r"Did not find any versions for SparkDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdfs.load()

        hdfs_walk.assert_called_once_with(HDFS_PREFIX)

    def test_load_latest(self, mocker, version):
        mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.InsecureClient.status",
            return_value=True,
        )
        hdfs_walk = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.InsecureClient.walk"
        )
        hdfs_walk.return_value = HDFS_FOLDER_STRUCTURE

        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )
        get_spark = mocker.patch.object(versioned_hdfs, "_get_spark")

        versioned_hdfs.load()

        hdfs_walk.assert_called_once_with(HDFS_PREFIX)
        get_spark.return_value.read.load.assert_called_once_with(
            "hdfs://{fn}/{f}/{v}/{f}".format(
                fn=FOLDER_NAME, v="2019-01-02T01.00.00.000Z", f=FILENAME
            ),
            "parquet",
        )

    def test_load_exact(self, mocker):
        ts = generate_timestamp()
        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=Version(ts, None)
        )
        get_spark = mocker.patch.object(versioned_hdfs, "_get_spark")

        versioned_hdfs.load()

        get_spark.return_value.read.load.assert_called_once_with(
            "hdfs://{fn}/{f}/{v}/{f}".format(fn=FOLDER_NAME, f=FILENAME, v=ts),
            "parquet",
        )

    def test_save(self, mocker, version):
        hdfs_status = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.InsecureClient.status"
        )
        hdfs_status.return_value = None

        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )

        # need resolve_load_version() call to return a load version that
        # matches save version due to consistency check in versioned_hdfs.save()
        mocker.patch.object(
            versioned_hdfs, "resolve_load_version", return_value=version.save
        )

        mocked_spark_df = mocker.Mock()
        versioned_hdfs.save(mocked_spark_df)

        hdfs_status.assert_called_once_with(
            "{fn}/{f}/{v}/{f}".format(fn=FOLDER_NAME, v=version.save, f=FILENAME),
            strict=False,
        )
        mocked_spark_df.write.save.assert_called_once_with(
            "hdfs://{fn}/{f}/{v}/{f}".format(
                fn=FOLDER_NAME, v=version.save, f=FILENAME
            ),
            "parquet",
        )

    def test_save_version_warning(self, mocker):
        exact_version = Version("2019-01-01T23.59.59.999Z", "2019-01-02T00.00.00.000Z")
        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=exact_version
        )
        mocker.patch.object(versioned_hdfs, "_exists_function", return_value=False)
        mocked_spark_df = mocker.Mock()

        pattern = (
            r"Save version `{ev.save}` did not match load version "
            r"`{ev.load}` for SparkDataSet\(.+\)".format(ev=exact_version)
        )

        with pytest.warns(UserWarning, match=pattern):
            versioned_hdfs.save(mocked_spark_df)
        mocked_spark_df.write.save.assert_called_once_with(
            "hdfs://{fn}/{f}/{sv}/{f}".format(
                fn=FOLDER_NAME, f=FILENAME, sv=exact_version.save
            ),
            "parquet",
        )

    def test_prevent_overwrite(self, mocker, version):
        hdfs_status = mocker.patch(
            "kedro.extras.datasets.spark.spark_dataset.InsecureClient.status"
        )
        hdfs_status.return_value = True

        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )

        mocked_spark_df = mocker.Mock()

        pattern = (
            r"Save path `.+` for SparkDataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdfs.save(mocked_spark_df)

        hdfs_status.assert_called_once_with(
            "{fn}/{f}/{v}/{f}".format(fn=FOLDER_NAME, v=version.save, f=FILENAME),
            strict=False,
        )
        mocked_spark_df.write.save.assert_not_called()

    def test_hdfs_warning(self, version):
        pattern = (
            "HDFS filesystem support for versioned SparkDataSet is in beta "
            "and uses `hdfs.client.InsecureClient`, please use with caution"
        )
        with pytest.warns(UserWarning, match=pattern):
            SparkDataSet(filepath="hdfs://{}".format(HDFS_PREFIX), version=version)

    def test_repr(self, version):
        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )
        assert "filepath=hdfs://" in str(versioned_hdfs)
        assert "version=Version(load=None, save='{}')".format(version.save) in str(
            versioned_hdfs
        )

        dataset_hdfs = SparkDataSet(filepath="hdfs://{}".format(HDFS_PREFIX))
        assert "filepath=hdfs://" in str(dataset_hdfs)
        assert "version=" not in str(dataset_hdfs)


@pytest.fixture
def data_catalog(tmp_path):
    source_path = str(Path(__file__).parent / "data/test.parquet")
    spark_in = SparkDataSet(source_path)
    spark_out = SparkDataSet(str(tmp_path / "spark_data"))
    pickle_ds = PickleDataSet(str(tmp_path / "pickle/test.pkl"))

    return DataCatalog(
        {"spark_in": spark_in, "spark_out": spark_out, "pickle_ds": pickle_ds}
    )


@pytest.mark.parametrize("is_async", [False, True])
class TestDataFlowSequentialRunner:
    def test_spark_load_save(self, is_async, data_catalog):
        """SparkDataSet(load) -> node -> Spark (save)."""
        pipeline = Pipeline([node(identity, "spark_in", "spark_out")])
        SequentialRunner(is_async=is_async).run(pipeline, data_catalog)

        save_path = Path(data_catalog._data_sets["spark_out"]._filepath)
        files = list(save_path.glob("*.parquet"))
        assert len(files) > 0

    def test_spark_pickle(self, is_async, data_catalog):
        """SparkDataSet(load) -> node -> PickleDataSet (save)"""
        pipeline = Pipeline([node(identity, "spark_in", "pickle_ds")])
        pattern = ".* was not serialized due to.*"
        with pytest.raises(DataSetError, match=pattern):
            SequentialRunner(is_async=is_async).run(pipeline, data_catalog)

    def test_spark_memory_spark(self, is_async, data_catalog):
        """SparkDataSet(load) -> node -> MemoryDataSet (save and then load) ->
        node -> SparkDataSet (save)"""
        pipeline = Pipeline(
            [
                node(identity, "spark_in", "memory_ds"),
                node(identity, "memory_ds", "spark_out"),
            ]
        )
        SequentialRunner(is_async=is_async).run(pipeline, data_catalog)

        save_path = Path(data_catalog._data_sets["spark_out"]._filepath)
        files = list(save_path.glob("*.parquet"))
        assert len(files) > 0
