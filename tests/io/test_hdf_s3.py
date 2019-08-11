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
from multiprocessing.reduction import ForkingPickler

import pandas as pd
import pytest
import s3fs
from botocore.exceptions import PartialCredentialsError
from moto import mock_s3
from pandas.util.testing import assert_frame_equal
from s3fs import S3FileSystem

from kedro.io import DataSetError, HDFS3DataSet
from kedro.io.core import Version

BUCKET_NAME = "test_bucket"
FILENAME = "test.hdf"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def hdf_data_set():
    return HDFS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=AWS_CREDENTIALS,
        key="test_hdf",
    )


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def mocked_s3_object(mocked_s3_bucket, dummy_dataframe):
    """Creates test data and adds it to mocked S3 bucket."""
    mocked_s3_bucket.put_object(
        Bucket=BUCKET_NAME, Key="test_hdf", Body=dummy_dataframe.to_csv(index=False)
    )
    return mocked_s3_bucket


@pytest.fixture
def hdf_data_set_with_args():
    return HDFS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=AWS_CREDENTIALS,
        key="test_hdf",
        load_args={"title": "test_hdf"},
        save_args={"title": "test_hdf"},
    )


@pytest.fixture
def versioned_hdf_data_set(load_version, save_version):
    return HDFS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=AWS_CREDENTIALS,
        key="test_hdf",
        version=Version(load_version, save_version),
    )


@pytest.fixture()
def s3fs_cleanup():
    # clear cache so we get a clean slate every time we instantiate a S3FileSystem
    yield
    S3FileSystem.cachable = False


@pytest.mark.usefixtures("s3fs_cleanup")
class TestHDFS3DataSet:
    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_secret_access_key": "SECRET"}, {"aws_access_key_id": "KEY"}],
    )
    def test_incomplete_credentials_load(self, bad_credentials):
        """Test that incomplete credentials passed in credentials.yml raises exception."""
        with pytest.raises(PartialCredentialsError):
            HDFS3DataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME,
                key="test_hdf",
                credentials=bad_credentials,
            )

    def test_incorrect_credentials_load(self):
        """Test that incorrect credential keys won't instantiate dataset."""
        pattern = "unexpected keyword argument"
        with pytest.raises(TypeError, match=pattern):
            HDFS3DataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME,
                key="test_hdf",
                credentials={"access_token": "TOKEN", "access_key": "KEY"},
            )

    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_access_key_id": None, "aws_secret_access_key": None}, {}, None],
    )
    def test_empty_credentials_load(self, bad_credentials):
        s3_data_set = HDFS3DataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            key="test_hdf",
            credentials=bad_credentials,
        )
        pattern = r"Failed while loading data from data set HDFS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            s3_data_set.load()

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save_and_load(self, hdf_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        hdf_data_set.save(dummy_dataframe)
        reloaded_df = hdf_data_set.load()

        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_load_missing(self, hdf_data_set):
        """Check the error when trying to load missing hdf file."""
        pattern = r"Failed while loading data from data set HDFS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            hdf_data_set.load()

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_exists(self, hdf_data_set, dummy_dataframe):
        """Test `exists` method invocation."""
        # file does not exist
        assert not hdf_data_set.exists()

        # file and key exist
        hdf_data_set.save(dummy_dataframe)
        assert hdf_data_set.exists()

        # file exists but the key does not
        data_set2 = HDFS3DataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            key="test_hdf_different_key",
            credentials=AWS_CREDENTIALS,
        )
        assert not data_set2.exists()

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_overwrite_if_exists(self, hdf_data_set, dummy_dataframe):
        """Test overriding existing hdf file."""
        hdf_data_set.save(dummy_dataframe)
        assert hdf_data_set.exists()

        hdf_data_set.save(dummy_dataframe.T)
        reloaded_df = hdf_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe.T)

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save_and_load_args(self, hdf_data_set_with_args, dummy_dataframe):
        """Test saving and reloading the data set."""
        hdf_data_set_with_args.save(dummy_dataframe)
        reloaded_df = hdf_data_set_with_args.load()

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_serializable(self, hdf_data_set):
        ForkingPickler.dumps(hdf_data_set)


@pytest.mark.usefixtures("s3fs_cleanup")
class TestHDFS3DataSetVersioned:
    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save_and_load(self, versioned_hdf_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_hdf_data_set.save(dummy_dataframe)
        reloaded_df = versioned_hdf_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_no_versions(self, versioned_hdf_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for HDFS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdf_data_set.load()

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_exists(self, versioned_hdf_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_hdf_data_set.exists()

        versioned_hdf_data_set.save(dummy_dataframe)
        assert versioned_hdf_data_set.exists()

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_prevent_overwrite(self, versioned_hdf_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_hdf_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for HDFS3DataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdf_data_set.save(dummy_dataframe)

    @pytest.mark.usefixtures("mocked_s3_bucket")
    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_hdf_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save path `.*/{}/test\.hdf` did not match load path "
            r"`.*/{}/test\.hdf` for HDFS3DataSet\(.+\)".format(
                save_version, load_version
            )
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_hdf_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        ds = HDFS3DataSet(filepath=FILENAME, bucket_name=BUCKET_NAME, key="test_hdf")
        ds_versioned = HDFS3DataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=AWS_CREDENTIALS,
            key="test_hdf",
            version=Version(load_version, save_version),
        )

        assert FILENAME in str(ds)
        assert "version" not in str(ds)

        assert FILENAME in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
