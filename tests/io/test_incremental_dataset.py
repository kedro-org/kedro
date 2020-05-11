# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
import re
from pathlib import Path
from typing import Any, Dict

import pandas as pd
import pytest
import s3fs
from moto import mock_s3
from pandas.util.testing import assert_frame_equal

from kedro.extras.datasets.pickle import PickleDataSet
from kedro.extras.datasets.text import TextDataSet
from kedro.io import AbstractDataSet, DataSetError, IncrementalDataSet
from kedro.io.data_catalog import CREDENTIALS_KEY

DATASET = "kedro.extras.datasets.pandas.CSVDataSet"


@pytest.fixture
def partitioned_data_pandas():
    return {
        "p{:02d}/data.csv".format(counter): pd.DataFrame(
            {"part": counter, "col": list(range(counter + 1))}
        )
        for counter in range(5)
    }


@pytest.fixture
def local_csvs(tmp_path, partitioned_data_pandas):
    local_dir = Path(tmp_path / "csvs")
    local_dir.mkdir()

    for k, data in partitioned_data_pandas.items():
        path = local_dir / k
        path.parent.mkdir(parents=True)
        data.to_csv(str(path), index=False)
    return local_dir


class DummyDataSet(AbstractDataSet):  # pragma: no cover
    def __init__(self, filepath):
        pass

    def _describe(self) -> Dict[str, Any]:
        return {"dummy": True}

    def _load(self) -> Any:
        pass

    def _save(self, data: Any) -> None:
        pass


def dummy_gt_func(value1: str, value2: str):
    return value1 > value2


def dummy_lt_func(value1: str, value2: str):
    return value1 < value2


class TestIncrementalDataSetLocal:
    def test_load_and_confirm(self, local_csvs, partitioned_data_pandas):
        """Test the standard flow for loading, confirming and reloading
        an IncrementalDataSet"""
        pds = IncrementalDataSet(str(local_csvs), DATASET)
        loaded = pds.load()
        assert loaded.keys() == partitioned_data_pandas.keys()
        for partition_id, data in loaded.items():
            assert_frame_equal(data, partitioned_data_pandas[partition_id])

        checkpoint_path = local_csvs / pds.DEFAULT_CHECKPOINT_FILENAME
        assert not checkpoint_path.exists()
        pds.confirm()
        assert checkpoint_path.is_file()
        assert checkpoint_path.read_text() == pds._read_checkpoint() == "p04/data.csv"

        reloaded = pds.load()
        assert reloaded.keys() == loaded.keys()

        pds.release()
        reloaded_after_release = pds.load()
        assert reloaded_after_release == {}

    def test_save(self, local_csvs):
        """Test saving a new partition into an IncrementalDataSet"""
        df = pd.DataFrame({"dummy": [1, 2, 3]})
        new_partition_key = "p05/data.csv"
        new_partition_path = local_csvs / new_partition_key
        pds = IncrementalDataSet(str(local_csvs), DATASET)

        assert not new_partition_path.exists()
        assert new_partition_key not in pds.load()

        pds.save({new_partition_key: df})
        assert new_partition_path.exists()
        loaded = pds.load()
        assert_frame_equal(loaded[new_partition_key], df)

    @pytest.mark.parametrize(
        "filename_suffix,expected_partitions",
        [
            (
                "",
                {
                    "p00/data.csv",
                    "p01/data.csv",
                    "p02/data.csv",
                    "p03/data.csv",
                    "p04/data.csv",
                },
            ),
            (".csv", {"p00/data", "p01/data", "p02/data", "p03/data", "p04/data"}),
            (".fake", set()),
        ],
    )
    def test_filename_suffix(self, filename_suffix, expected_partitions, local_csvs):
        """Test how specifying filename_suffix affects the available
        partitions and their names"""
        pds = IncrementalDataSet(
            str(local_csvs), DATASET, filename_suffix=filename_suffix
        )
        loaded = pds.load()
        assert loaded.keys() == expected_partitions

    @pytest.mark.parametrize(
        "forced_checkpoint,expected_partitions",
        [
            (
                "",
                {
                    "p00/data.csv",
                    "p01/data.csv",
                    "p02/data.csv",
                    "p03/data.csv",
                    "p04/data.csv",
                },
            ),
            (
                "p00/data.csv",
                {"p01/data.csv", "p02/data.csv", "p03/data.csv", "p04/data.csv"},
            ),
            ("p03/data.csv", {"p04/data.csv"}),
        ],
    )
    def test_force_checkpoint_no_checkpoint_file(
        self, forced_checkpoint, expected_partitions, local_csvs
    ):
        """Test how forcing checkpoint value affects the available partitions
        if the checkpoint file does not exist"""
        pds = IncrementalDataSet(str(local_csvs), DATASET, checkpoint=forced_checkpoint)
        loaded = pds.load()
        assert loaded.keys() == expected_partitions

        confirm_path = local_csvs / pds.DEFAULT_CHECKPOINT_FILENAME
        assert not confirm_path.exists()
        pds.confirm()
        assert confirm_path.is_file()
        assert confirm_path.read_text() == max(expected_partitions)

    @pytest.mark.parametrize(
        "forced_checkpoint,expected_partitions",
        [
            (
                "",
                {
                    "p00/data.csv",
                    "p01/data.csv",
                    "p02/data.csv",
                    "p03/data.csv",
                    "p04/data.csv",
                },
            ),
            (
                "p00/data.csv",
                {"p01/data.csv", "p02/data.csv", "p03/data.csv", "p04/data.csv"},
            ),
            ("p03/data.csv", {"p04/data.csv"}),
        ],
    )
    def test_force_checkpoint_checkpoint_file_exists(
        self, forced_checkpoint, expected_partitions, local_csvs
    ):
        """Test how forcing checkpoint value affects the available partitions
        if the checkpoint file exists"""
        IncrementalDataSet(str(local_csvs), DATASET).confirm()
        checkpoint = local_csvs / IncrementalDataSet.DEFAULT_CHECKPOINT_FILENAME
        assert checkpoint.read_text() == "p04/data.csv"

        pds = IncrementalDataSet(str(local_csvs), DATASET, checkpoint=forced_checkpoint)
        assert pds._checkpoint.exists()
        loaded = pds.load()
        assert loaded.keys() == expected_partitions

    @pytest.mark.parametrize(
        "forced_checkpoint", ["p04/data.csv", "p10/data.csv", "p100/data.csv"]
    )
    def test_force_checkpoint_no_partitions(self, forced_checkpoint, local_csvs):
        """Test that forcing the checkpoint to certain values results in no
        partitions being returned"""
        pds = IncrementalDataSet(str(local_csvs), DATASET, checkpoint=forced_checkpoint)
        loaded = pds.load()
        assert loaded == {}

        confirm_path = local_csvs / pds.DEFAULT_CHECKPOINT_FILENAME
        assert not confirm_path.exists()
        pds.confirm()
        # confirming with no partitions available must have no effect
        assert not confirm_path.exists()

    def test_checkpoint_path(self, local_csvs, partitioned_data_pandas):
        """Test configuring a different checkpoint path"""
        checkpoint_path = local_csvs / "checkpoint_folder" / "checkpoint_file"
        assert not checkpoint_path.exists()

        IncrementalDataSet(
            str(local_csvs), DATASET, checkpoint={"filepath": str(checkpoint_path)}
        ).confirm()
        assert checkpoint_path.is_file()
        assert checkpoint_path.read_text() == max(partitioned_data_pandas)

    @pytest.mark.parametrize(
        "checkpoint_config,expected_checkpoint_class",
        [
            (None, TextDataSet),
            ({"type": "kedro.extras.datasets.pickle.PickleDataSet"}, PickleDataSet),
            ({"type": "tests.io.test_incremental_dataset.DummyDataSet"}, DummyDataSet),
        ],
    )
    def test_checkpoint_type(
        self, tmp_path, checkpoint_config, expected_checkpoint_class
    ):
        """Test configuring a different checkpoint dataset type"""
        pds = IncrementalDataSet(str(tmp_path), DATASET, checkpoint=checkpoint_config)
        assert isinstance(pds._checkpoint, expected_checkpoint_class)

    @pytest.mark.parametrize(
        "checkpoint_config,error_pattern",
        [
            (
                {"versioned": True},
                "`IncrementalDataSet` does not support versioning "
                "of the checkpoint. Please remove `versioned` key from the "
                "checkpoint definition.",
            ),
            (
                {"version": None},
                "`IncrementalDataSet` does not support versioning "
                "of the checkpoint. Please remove `version` key from the "
                "checkpoint definition.",
            ),
        ],
    )
    def test_version_not_allowed(self, tmp_path, checkpoint_config, error_pattern):
        """Test that invalid checkpoint configurations raise expected errors"""
        with pytest.raises(DataSetError, match=re.escape(error_pattern)):
            IncrementalDataSet(str(tmp_path), DATASET, checkpoint=checkpoint_config)

    @pytest.mark.parametrize(
        "pds_config,fs_creds,dataset_creds,checkpoint_creds",
        [
            (
                {"dataset": DATASET, "credentials": {"cred": "common"}},
                {"cred": "common"},
                {"cred": "common"},
                {"cred": "common"},
            ),
            (
                {
                    "dataset": DATASET,
                    "credentials": {
                        "cred": "common",
                        "dataset_credentials": {"ds": "only"},
                    },
                },
                {"cred": "common"},
                {"ds": "only"},
                {"cred": "common"},
            ),
            (
                {
                    "dataset": DATASET,
                    "credentials": {"cred": "common"},
                    "checkpoint": {"credentials": {"cp": "only"}},
                },
                {"cred": "common"},
                {"cred": "common"},
                {"cp": "only"},
            ),
            (
                {
                    "dataset": DATASET,
                    "credentials": {"dataset_credentials": {"ds": "only"}},
                    "checkpoint": {"credentials": {"cp": "only"}},
                },
                {},
                {"ds": "only"},
                {"cp": "only"},
            ),
            (
                {
                    "dataset": {"type": DATASET, "credentials": None},
                    "credentials": {"cred": "common"},
                    "checkpoint": {"credentials": None},
                },
                {"cred": "common"},
                None,
                None,
            ),
        ],
    )
    def test_credentials(self, pds_config, fs_creds, dataset_creds, checkpoint_creds):
        """Test correctness of credentials propagation into the dataset and
        checkpoint constructors"""
        pds = IncrementalDataSet(str(Path.cwd()), **pds_config)
        assert pds._credentials == fs_creds
        assert pds._dataset_config[CREDENTIALS_KEY] == dataset_creds
        assert pds._checkpoint_config[CREDENTIALS_KEY] == checkpoint_creds

    @pytest.mark.parametrize(
        "comparison_func,expected_partitions",
        [
            (
                "tests.io.test_incremental_dataset.dummy_gt_func",
                {"p03/data.csv", "p04/data.csv"},
            ),
            (dummy_gt_func, {"p03/data.csv", "p04/data.csv"}),
            (
                "tests.io.test_incremental_dataset.dummy_lt_func",
                {"p00/data.csv", "p01/data.csv"},
            ),
            (dummy_lt_func, {"p00/data.csv", "p01/data.csv"}),
        ],
    )
    def test_comparison_func(self, comparison_func, expected_partitions, local_csvs):
        """Test that specifying a custom function for comparing the checkpoint value
        to a partition id results in expected partitions being returned on load"""
        checkpoint_config = {
            "force_checkpoint": "p02/data.csv",
            "comparison_func": comparison_func,
        }
        pds = IncrementalDataSet(str(local_csvs), DATASET, checkpoint=checkpoint_config)
        assert pds.load().keys() == expected_partitions


BUCKET_NAME = "fake_bucket_name"


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

    def test_load_and_confirm(self, mocked_csvs_in_s3, partitioned_data_pandas):
        """Test the standard flow for loading, confirming and reloading
        a IncrementalDataSet in S3"""
        pds = IncrementalDataSet(mocked_csvs_in_s3, DATASET)
        assert pds._checkpoint._protocol == "s3"
        loaded = pds.load()
        assert loaded.keys() == partitioned_data_pandas.keys()
        for partition_id, data in loaded.items():
            assert_frame_equal(data, partitioned_data_pandas[partition_id])

        assert not pds._checkpoint.exists()
        assert pds._read_checkpoint() is None
        pds.confirm()
        assert pds._checkpoint.exists()
        assert pds._read_checkpoint() == max(partitioned_data_pandas)

    def test_load_and_confirm_s3a(
        self, mocked_csvs_in_s3, partitioned_data_pandas, mocker
    ):
        s3a_path = "s3a://{}".format(mocked_csvs_in_s3.split("://", 1)[1])
        pds = IncrementalDataSet(s3a_path, DATASET)
        assert pds._protocol == "s3a"
        assert pds._checkpoint._protocol == "s3"

        mocked_ds = mocker.patch.object(pds, "_dataset_type")
        mocked_ds.__name__ = "mocked"
        loaded = pds.load()

        assert loaded.keys() == partitioned_data_pandas.keys()
        assert not pds._checkpoint.exists()
        assert pds._read_checkpoint() is None
        pds.confirm()
        assert pds._checkpoint.exists()
        assert pds._read_checkpoint() == max(partitioned_data_pandas)

    @pytest.mark.parametrize(
        "forced_checkpoint,expected_partitions",
        [
            (
                "",
                {
                    "p00/data.csv",
                    "p01/data.csv",
                    "p02/data.csv",
                    "p03/data.csv",
                    "p04/data.csv",
                },
            ),
            (
                "p00/data.csv",
                {"p01/data.csv", "p02/data.csv", "p03/data.csv", "p04/data.csv"},
            ),
            ("p03/data.csv", {"p04/data.csv"}),
        ],
    )
    def test_force_checkpoint_no_checkpoint_file(
        self, forced_checkpoint, expected_partitions, mocked_csvs_in_s3
    ):
        """Test how forcing checkpoint value affects the available partitions
        in S3 if the checkpoint file does not exist"""
        pds = IncrementalDataSet(
            mocked_csvs_in_s3, DATASET, checkpoint=forced_checkpoint
        )
        loaded = pds.load()
        assert loaded.keys() == expected_partitions

        assert not pds._checkpoint.exists()
        pds.confirm()
        assert pds._checkpoint.exists()
        assert pds._checkpoint.load() == max(expected_partitions)

    @pytest.mark.parametrize(
        "forced_checkpoint,expected_partitions",
        [
            (
                "",
                {
                    "p00/data.csv",
                    "p01/data.csv",
                    "p02/data.csv",
                    "p03/data.csv",
                    "p04/data.csv",
                },
            ),
            (
                "p00/data.csv",
                {"p01/data.csv", "p02/data.csv", "p03/data.csv", "p04/data.csv"},
            ),
            ("p03/data.csv", {"p04/data.csv"}),
        ],
    )
    def test_force_checkpoint_checkpoint_file_exists(
        self, forced_checkpoint, expected_partitions, mocked_csvs_in_s3
    ):
        """Test how forcing checkpoint value affects the available partitions
        in S3 if the checkpoint file exists"""
        # create checkpoint and assert that it exists
        IncrementalDataSet(mocked_csvs_in_s3, DATASET).confirm()
        checkpoint_path = "{}/{}".format(
            mocked_csvs_in_s3, IncrementalDataSet.DEFAULT_CHECKPOINT_FILENAME
        )
        checkpoint_value = TextDataSet(checkpoint_path).load()
        assert checkpoint_value == "p04/data.csv"

        pds = IncrementalDataSet(
            mocked_csvs_in_s3, DATASET, checkpoint=forced_checkpoint
        )
        assert pds._checkpoint.exists()
        loaded = pds.load()
        assert loaded.keys() == expected_partitions

    @pytest.mark.parametrize(
        "forced_checkpoint", ["p04/data.csv", "p10/data.csv", "p100/data.csv"]
    )
    def test_force_checkpoint_no_partitions(self, forced_checkpoint, mocked_csvs_in_s3):
        """Test that forcing the checkpoint to certain values results in no
        partitions returned from S3"""
        pds = IncrementalDataSet(
            mocked_csvs_in_s3, DATASET, checkpoint=forced_checkpoint
        )
        loaded = pds.load()
        assert loaded == {}

        assert not pds._checkpoint.exists()
        pds.confirm()
        # confirming with no partitions available must have no effect
        assert not pds._checkpoint.exists()
