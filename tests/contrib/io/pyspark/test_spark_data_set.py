# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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

import tempfile
from pathlib import Path

import pandas as pd
import pytest
from pyspark.sql import SparkSession
from pyspark.sql.functions import col  # pylint: disable=no-name-in-module
from pyspark.sql.types import IntegerType, StringType, StructField, StructType
from pyspark.sql.utils import AnalysisException

from kedro.contrib.io.pyspark import SparkDataSet
from kedro.io import CSVLocalDataSet, DataSetError, ParquetLocalDataSet, Version
from kedro.io.core import generate_timestamp

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


class TestSparkDataSet:
    def test_load_parquet(self, tmp_path, sample_pandas_df):
        temp_path = str(tmp_path / "data")
        local_parquet_set = ParquetLocalDataSet(filepath=temp_path)
        local_parquet_set.save(sample_pandas_df)
        spark_data_set = SparkDataSet(filepath=temp_path)
        spark_df = spark_data_set.load()
        assert spark_df.count() == 4

    def test_save_parquet(self, tmp_path, sample_spark_df):
        # To cross check the correct Spark save operation we save to
        # a single spark partition and retrieve it with Kedro
        # ParquetLocalDataSet
        temp_dir = Path(str(tmp_path / "test_data"))
        spark_data_set = SparkDataSet(
            filepath=str(temp_dir), save_args={"compression": "none"}
        )
        spark_df = sample_spark_df.coalesce(1)
        spark_data_set.save(spark_df)

        single_parquet = [
            f for f in temp_dir.iterdir() if f.is_file() and f.name.startswith("part")
        ][0]

        local_parquet_data_set = ParquetLocalDataSet(filepath=str(single_parquet))

        pandas_df = local_parquet_data_set.load()

        assert pandas_df[pandas_df["name"] == "Bob"]["age"].iloc[0] == 12

    def test_load_options_csv(self, tmp_path, sample_pandas_df):
        filepath = str(tmp_path / "data")
        local_csv_data_set = CSVLocalDataSet(filepath=filepath)
        local_csv_data_set.save(sample_pandas_df)
        spark_data_set = SparkDataSet(
            filepath=filepath, file_format="csv", load_args={"header": True}
        )
        spark_df = spark_data_set.load()
        assert spark_df.filter(col("Name") == "Alex").count() == 1

    def test_save_options_csv(self, tmp_path, sample_spark_df):
        # To cross check the correct Spark save operation we save to
        # a single spark partition with csv format and retrieve it with Kedro
        # CSVLocalDataSet
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

        csv_local_data_set = CSVLocalDataSet(
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

    def test_cant_pickle(self):
        import pickle

        with pytest.raises(pickle.PicklingError):
            pickle.dumps(SparkDataSet("bob"))


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
            r"Save path `{save}` did not match load path "
            r"`{load}` for SparkDataSet\(.+\)".format(
                save=str(tmp_path / FILENAME / exact_version.save / FILENAME),
                load=str(tmp_path / FILENAME / exact_version.load / FILENAME),
            )
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

        mocked_load_version = mocker.MagicMock()
        mocked_load_version.__eq__.return_value = True

        # need to mock _get_load_path() call inside _save()
        # also need _get_load_path() to return a load version that
        # _check_paths_consistency() will be happy with (hence mocking __eq__)
        mocker.patch.object(
            versioned_dataset_s3, "_get_load_path", return_value=mocked_load_version
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
            r"Save path `{b}/{f}/{sv}/{f}` did not match load path "
            r"`{b}/{f}/{lv}/{f}` for SparkDataSet\(.+\)".format(
                b=BUCKET_NAME, f=FILENAME, sv=exact_version.save, lv=exact_version.load
            )
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
            "kedro.contrib.io.pyspark.spark_data_set.InsecureClient.walk"
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
            "kedro.contrib.io.pyspark.spark_data_set.InsecureClient.status",
            return_value=True,
        )
        hdfs_walk = mocker.patch(
            "kedro.contrib.io.pyspark.spark_data_set.InsecureClient.walk"
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
            "kedro.contrib.io.pyspark.spark_data_set.InsecureClient.status"
        )
        hdfs_status.return_value = None

        versioned_hdfs = SparkDataSet(
            filepath="hdfs://{}".format(HDFS_PREFIX), version=version
        )

        mocked_load_version = mocker.MagicMock()
        mocked_load_version.__eq__.return_value = True
        # need to mock _get_load_path() call inside _save()
        # also need _get_load_path() to return a load version that
        # _check_paths_consistency() will be happy with (hence mocking __eq__)
        mocker.patch.object(
            versioned_hdfs, "_get_load_path", return_value=mocked_load_version
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
            r"Save path `{fn}/{f}/{sv}/{f}` did not match load path "
            r"`{fn}/{f}/{lv}/{f}` for SparkDataSet\(.+\)".format(
                fn=FOLDER_NAME, f=FILENAME, sv=exact_version.save, lv=exact_version.load
            )
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
            "kedro.contrib.io.pyspark.spark_data_set.InsecureClient.status"
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
