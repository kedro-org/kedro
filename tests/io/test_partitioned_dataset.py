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
import logging
import re
from pathlib import Path

import pandas as pd
import pytest
import s3fs
from moto import mock_s3
from pandas.util.testing import assert_frame_equal

from kedro.io import (
    CSVLocalDataSet,
    CSVS3DataSet,
    DataSetError,
    ParquetLocalDataSet,
    PartitionedDataSet,
)
from kedro.io.data_catalog import CREDENTIALS_KEY


@pytest.fixture
def partitioned_data_pandas():
    keys = ("p1/data1.csv", "p2.csv", "p1/data2.csv", "p3", "_p4")
    return {
        k: pd.DataFrame({"part": k, "counter": list(range(counter))})
        for counter, k in enumerate(keys, 1)
    }


@pytest.fixture
def local_csvs(tmp_path, partitioned_data_pandas):
    local_dir = Path(str(tmp_path / "csvs"))
    local_dir.mkdir()

    for k, data in partitioned_data_pandas.items():
        path = local_dir / k
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(str(path), index=False)
    return local_dir


LOCAL_DATASET_DEFINITION = [
    "CSVLocalDataSet",
    "kedro.io.csv_local.CSVLocalDataSet",
    CSVLocalDataSet,
    {"type": "CSVLocalDataSet", "save_args": {"index": False}},
    {"type": CSVLocalDataSet},
]


class FakeDataSet:  # pylint: disable=too-few-public-methods
    pass


class TestPartitionedDataSetLocal:
    @pytest.mark.parametrize("dataset", LOCAL_DATASET_DEFINITION)
    @pytest.mark.parametrize(
        "suffix,expected_num_parts", [("", 5), (".csv", 3), ("p4", 1)]
    )
    def test_load(
        self, dataset, local_csvs, partitioned_data_pandas, suffix, expected_num_parts
    ):
        pds = PartitionedDataSet(str(local_csvs), dataset, filename_suffix=suffix)
        loaded_partitions = pds.load()

        assert len(loaded_partitions.keys()) == expected_num_parts
        for partition_id, load_func in loaded_partitions.items():
            df = load_func()
            assert_frame_equal(df, partitioned_data_pandas[partition_id + suffix])
            if suffix:
                assert not partition_id.endswith(suffix)

    @pytest.mark.parametrize("dataset", LOCAL_DATASET_DEFINITION)
    @pytest.mark.parametrize("suffix", ["", ".csv"])
    def test_save(self, dataset, local_csvs, suffix):
        pds = PartitionedDataSet(str(local_csvs), dataset, filename_suffix=suffix)
        original_data = pd.DataFrame({"foo": 42, "bar": ["a", "b", None]})
        part_id = "new/data"
        pds.save({part_id: original_data})

        assert (local_csvs / "new" / ("data" + suffix)).is_file()
        loaded_partitions = pds.load()
        assert part_id in loaded_partitions
        reloaded_data = loaded_partitions[part_id]()
        assert_frame_equal(reloaded_data, original_data)

    @pytest.mark.parametrize("dataset", LOCAL_DATASET_DEFINITION)
    def test_save_invalidates_cache(self, dataset, local_csvs):
        pds = PartitionedDataSet(str(local_csvs), dataset)
        first_load = pds.load()

        data = pd.DataFrame({"foo": 42, "bar": ["a", "b", None]})
        part_id = "new/data.csv"
        pds.save({part_id: data})
        assert part_id not in first_load
        assert part_id in pds.load()

    @pytest.mark.parametrize("dataset", ["CSVLocalDataSet", "ParquetLocalDataSet"])
    def test_exists(self, local_csvs, dataset):
        assert PartitionedDataSet(str(local_csvs), dataset).exists()

        empty_folder = local_csvs / "empty" / "folder"
        assert not PartitionedDataSet(str(empty_folder), dataset).exists()
        empty_folder.mkdir(parents=True)
        assert not PartitionedDataSet(str(empty_folder), dataset).exists()

    @pytest.mark.parametrize("dataset", LOCAL_DATASET_DEFINITION)
    def test_release(self, dataset, local_csvs):
        partition_to_remove = "p2.csv"
        pds = PartitionedDataSet(str(local_csvs), dataset)
        initial_load = pds.load()
        assert partition_to_remove in initial_load

        (local_csvs / partition_to_remove).unlink()
        cached_load = pds.load()
        assert initial_load.keys() == cached_load.keys()

        pds.release()
        load_after_release = pds.load()
        assert initial_load.keys() ^ load_after_release.keys() == {partition_to_remove}

    @pytest.mark.parametrize("dataset", LOCAL_DATASET_DEFINITION)
    def test_describe(self, dataset):
        path = str(Path.cwd())
        pds = PartitionedDataSet(path, dataset)

        assert "path={}".format(path) in str(pds)
        assert "dataset_type=CSVLocalDataSet" in str(pds)
        if isinstance(dataset, dict) and dataset.keys() - {"type"}:
            assert "dataset_config" in str(pds)
        else:
            assert "dataset_config" not in str(pds)

    def test_load_args(self, mocker):
        fake_partition_name = "fake_partition"
        mocked_filesystem = mocker.patch("fsspec.filesystem")
        mocked_find = mocked_filesystem.return_value.find
        mocked_find.return_value = [fake_partition_name]

        path = str(Path.cwd())
        load_args = {"maxdepth": 42, "withdirs": True}
        pds = PartitionedDataSet(path, "CSVLocalDataSet", load_args=load_args)
        mocker.patch.object(pds, "_path_to_partition", return_value=fake_partition_name)

        assert pds.load().keys() == {fake_partition_name}
        mocked_find.assert_called_once_with(path, **load_args)

    @pytest.mark.parametrize(
        "credentials,expected_pds_creds,expected_dataset_creds",
        [
            ({"cred": "common"}, {"cred": "common"}, {"cred": "common"}),
            (
                {"cred": "common", "dataset_credentials": {"ds": "only"}},
                {"cred": "common"},
                {"ds": "only"},
            ),
            ({"dataset_credentials": {"ds": "only"}}, {}, {"ds": "only"}),
            (
                {"cred_key1": "cred_value1", "dataset_credentials": None},
                {"cred_key1": "cred_value1"},
                None,
            ),
        ],
    )
    def test_credentials(
        self, mocker, credentials, expected_pds_creds, expected_dataset_creds
    ):
        mocked_filesystem = mocker.patch("fsspec.filesystem")
        path = str(Path.cwd())
        pds = PartitionedDataSet(path, "CSVLocalDataSet", credentials=credentials)

        assert mocked_filesystem.call_count == 2
        mocked_filesystem.assert_called_with("file", **expected_pds_creds)
        if expected_dataset_creds:
            assert pds._dataset_config[CREDENTIALS_KEY] == expected_dataset_creds
        else:
            assert CREDENTIALS_KEY not in pds._dataset_config

        str_repr = str(pds)

        def _assert_not_in_repr(value):
            if isinstance(value, dict):
                for k_, v_ in value.items():
                    _assert_not_in_repr(k_)
                    _assert_not_in_repr(v_)
            if value is not None:
                assert str(value) not in str_repr

        _assert_not_in_repr(credentials)

    @pytest.mark.parametrize("dataset", ["ParquetLocalDataSet", ParquetLocalDataSet])
    def test_invalid_dataset(self, dataset, local_csvs):
        pds = PartitionedDataSet(str(local_csvs), dataset)
        loaded_partitions = pds.load()

        for partition, df_loader in loaded_partitions.items():
            pattern = r"Failed while loading data from data set ParquetLocalDataSet(.*)"
            with pytest.raises(DataSetError, match=pattern) as exc_info:
                df_loader()
            error_message = str(exc_info.value)
            assert (
                "Either the file is corrupted or this is not a parquet file"
                in error_message
            )
            assert str(partition) in error_message

    @pytest.mark.parametrize(
        "dataset_config,error_pattern",
        [
            ("UndefinedDatasetType", "Class `UndefinedDatasetType` not found"),
            (
                "missing.module.UndefinedDatasetType",
                r"Class `missing\.module\.UndefinedDatasetType` not found",
            ),
            (
                FakeDataSet,
                r"DataSet type `tests\.io\.test_partitioned_dataset\.FakeDataSet` "
                r"is invalid\: all data set types must extend `AbstractDataSet`",
            ),
            ({}, "`type` is missing from DataSet catalog configuration"),
        ],
    )
    def test_invalid_dataset_config(self, dataset_config, error_pattern):
        with pytest.raises(DataSetError, match=error_pattern):
            PartitionedDataSet(str(Path.cwd()), dataset_config)

    @pytest.mark.parametrize(
        "dataset_config",
        [
            {"type": CSVLocalDataSet, "versioned": True},
            {"type": "CSVLocalDataSet", "versioned": True},
        ],
    )
    def test_versioned_dataset_not_allowed(self, dataset_config):
        pattern = (
            "`PartitionedDataSet` does not support versioning of the underlying "
            "dataset. Please remove `versioned` flag from the dataset definition."
        )
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            PartitionedDataSet(str(Path.cwd()), dataset_config)

    def test_no_partitions(self, tmpdir):
        pds = PartitionedDataSet(str(tmpdir), "CSVLocalDataSet")

        pattern = "No partitions found in `{}`".format(str(tmpdir))
        with pytest.raises(DataSetError, match=pattern):
            pds.load()

    @pytest.mark.parametrize(
        "pds_config,filepath_arg",
        [
            (
                {
                    "path": str(Path.cwd()),
                    "dataset": {"type": CSVLocalDataSet, "filepath": "fake_path"},
                },
                "filepath",
            ),
            (
                {
                    "path": str(Path.cwd()),
                    "dataset": {"type": CSVLocalDataSet, "other_arg": "fake_path"},
                    "filepath_arg": "other_arg",
                },
                "other_arg",
            ),
        ],
    )
    def test_filepath_arg_warning(self, pds_config, filepath_arg):
        pattern = (
            "`{}` key must not be specified in the dataset definition as it "
            "will be overwritten by partition path".format(filepath_arg)
        )
        with pytest.warns(UserWarning, match=re.escape(pattern)):
            PartitionedDataSet(**pds_config)

    def test_credentials_log_warning(self, caplog):
        """Check that the warning is logged if the dataset credentials will overwrite
        the top-level ones"""
        pds = PartitionedDataSet(
            path=str(Path.cwd()),
            dataset={"type": CSVLocalDataSet, "credentials": {"secret": "dataset"}},
            credentials={"secret": "global"},
        )
        log_message = (
            "Top-level credentials will not propagate into the underlying dataset "
            "since credentials were explicitly defined in the dataset config."
        )
        assert caplog.record_tuples == [("kedro.io.core", logging.WARNING, log_message)]
        assert pds._dataset_config["credentials"] == {"secret": "dataset"}

    @pytest.mark.parametrize(
        "pds_config,expected_dataset_creds",
        [
            (
                {
                    "dataset": "CSVLocalDataSet",
                    "credentials": {
                        "secret": "global",
                        "dataset_credentials": {"secret": "dataset"},
                    },
                },
                {"secret": "dataset"},
            ),
            (
                {
                    "dataset": {
                        "type": CSVLocalDataSet,
                        "credentials": {"secret": "expected"},
                    },
                    "credentials": {
                        "secret": "global",
                        "dataset_credentials": {"secret": "other"},
                    },
                },
                {"secret": "expected"},
            ),
            (
                {
                    "dataset": {"type": CSVLocalDataSet, "credentials": None},
                    "credentials": {
                        "secret": "global",
                        "dataset_credentials": {"secret": "other"},
                    },
                },
                None,
            ),
        ],
    )
    def test_dataset_creds_deprecated(self, pds_config, expected_dataset_creds):
        """Check that the deprecation warning is emitted if dataset credentials
        were specified the old way (using `dataset_credentials` key)"""
        pattern = (
            "Support for `dataset_credentials` key in the credentials is now "
            "deprecated and will be removed in the next version. Please specify "
            "the dataset credentials explicitly inside the dataset config."
        )
        with pytest.warns(DeprecationWarning, match=re.escape(pattern)):
            pds = PartitionedDataSet(path=str(Path.cwd()), **pds_config)
        assert pds._dataset_config["credentials"] == expected_dataset_creds


BUCKET_NAME = "fake_bucket_name"
S3_DATASET_DEFINITION = [
    "CSVS3DataSet",
    "kedro.io.csv_s3.CSVS3DataSet",
    CSVS3DataSet,
    {"type": "CSVS3DataSet", "save_args": {"index": False}},
    {"type": CSVS3DataSet},
]


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3")
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def mocked_csvs_in_s3(mocked_s3_bucket, partitioned_data_pandas):
    prefix = "csvs"
    for key, data in partitioned_data_pandas.items():
        mocked_s3_bucket.put_object(
            Bucket=BUCKET_NAME,
            Key="{}/{}".format(prefix, key),
            Body=data.to_csv(index=False),
        )
    return "s3://{}/{}".format(BUCKET_NAME, prefix)


class TestPartitionedDataSetS3:
    @pytest.fixture(autouse=True)
    def fake_aws_creds(self, monkeypatch):
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "FAKE_ACCESS_KEY")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "FAKE_SECRET_KEY")

    @pytest.mark.parametrize("dataset", S3_DATASET_DEFINITION)
    def test_load(self, dataset, mocked_csvs_in_s3, partitioned_data_pandas):
        pds = PartitionedDataSet(mocked_csvs_in_s3, dataset)
        loaded_partitions = pds.load()

        assert loaded_partitions.keys() == partitioned_data_pandas.keys()
        for partition_id, load_func in loaded_partitions.items():
            df = load_func()
            assert_frame_equal(df, partitioned_data_pandas[partition_id])

    @pytest.mark.parametrize("dataset", S3_DATASET_DEFINITION)
    def test_save(self, dataset, mocked_csvs_in_s3):
        pds = PartitionedDataSet(mocked_csvs_in_s3, dataset)
        original_data = pd.DataFrame({"foo": 42, "bar": ["a", "b", None]})
        part_id = "new/data.csv"
        pds.save({part_id: original_data})

        s3 = s3fs.S3FileSystem()
        assert s3.exists("/".join([mocked_csvs_in_s3, part_id]))

        loaded_partitions = pds.load()
        assert part_id in loaded_partitions
        reloaded_data = loaded_partitions[part_id]()
        assert_frame_equal(reloaded_data, original_data)

    @pytest.mark.parametrize("dataset", ["CSVS3DataSet", "HDFS3DataSet"])
    def test_exists(self, dataset, mocked_csvs_in_s3):
        assert PartitionedDataSet(mocked_csvs_in_s3, dataset).exists()

        empty_folder = "/".join([mocked_csvs_in_s3, "empty", "folder"])
        assert not PartitionedDataSet(empty_folder, dataset).exists()

        s3fs.S3FileSystem().mkdir(empty_folder)
        assert not PartitionedDataSet(empty_folder, dataset).exists()

    @pytest.mark.parametrize("dataset", S3_DATASET_DEFINITION)
    def test_release(self, dataset, mocked_csvs_in_s3):
        partition_to_remove = "p2.csv"
        pds = PartitionedDataSet(mocked_csvs_in_s3, dataset)
        initial_load = pds.load()
        assert partition_to_remove in initial_load

        s3 = s3fs.S3FileSystem()
        s3.rm("/".join([mocked_csvs_in_s3, partition_to_remove]))
        cached_load = pds.load()
        assert initial_load.keys() == cached_load.keys()

        pds.release()
        load_after_release = pds.load()
        assert initial_load.keys() ^ load_after_release.keys() == {partition_to_remove}

    @pytest.mark.parametrize("dataset", S3_DATASET_DEFINITION)
    def test_describe(self, dataset):
        path = "s3://{}/foo/bar".format(BUCKET_NAME)
        pds = PartitionedDataSet(path, dataset)

        assert "path={}".format(path) in str(pds)
        assert "dataset_type=CSVS3DataSet" in str(pds)
        if isinstance(dataset, dict) and dataset.keys() - {"type"}:
            assert "dataset_config" in str(pds)
        else:
            assert "dataset_config" not in str(pds)
