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

# pylint: disable=no-member

import pickle
from multiprocessing.reduction import ForkingPickler

import pytest
import s3fs
from botocore.exceptions import PartialCredentialsError
from moto import mock_s3
from s3fs import S3FileSystem

from kedro.io import DataSetError, PickleS3DataSet, Version

FILENAME = "test.csv"
BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)
DUMMY_PICKABLE_OBJECT = {"key": "value"}


@pytest.fixture
def s3_data_set():
    return PickleS3DataSet(
        filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=AWS_CREDENTIALS
    )


@pytest.fixture
def s3_data_set_with_args():
    return PickleS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=AWS_CREDENTIALS,
        load_args={"fix_imports": False},
        save_args={"fix_imports": False},
    )


@pytest.fixture
def versioned_s3_data_set(load_version, save_version):
    return PickleS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=AWS_CREDENTIALS,
        version=Version(load_version, save_version),
    )


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def mocked_s3_object(mocked_s3_bucket):
    """Creates test data and adds it to mocked S3 bucket."""
    mocked_s3_bucket.put_object(
        Bucket=BUCKET_NAME, Key=FILENAME, Body=pickle.dumps(DUMMY_PICKABLE_OBJECT)
    )
    return mocked_s3_bucket


@pytest.fixture
def mocked_s3_object_versioned(mocked_s3_bucket, save_version):
    """Create versioned test data and add it to mocked S3 bucket."""
    mocked_s3_bucket.put_object(
        Bucket=BUCKET_NAME,
        Key="{0}/{1}/{0}".format(FILENAME, save_version),
        Body=pickle.dumps(DUMMY_PICKABLE_OBJECT),
    )
    return mocked_s3_bucket


@pytest.fixture()
def s3fs_cleanup():
    # clear cache so we get a clean slate every time we instantiate a S3FileSystem
    yield
    S3FileSystem.cachable = False


@pytest.mark.usefixtures("s3fs_cleanup")
class TestPickleS3DataSet:
    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_exists(self, s3_data_set):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not s3_data_set.exists()
        s3_data_set.save(DUMMY_PICKABLE_OBJECT)
        assert s3_data_set.exists()

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_load(self, s3_data_set):
        """Test loading the data from S3."""
        loaded_data = s3_data_set.load()
        assert loaded_data == DUMMY_PICKABLE_OBJECT

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_load_args(self, s3_data_set_with_args):
        """Test loading the data from S3 with options."""
        loaded_data = s3_data_set_with_args.load()
        assert loaded_data == DUMMY_PICKABLE_OBJECT

    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_secret_access_key": "SECRET"}, {"aws_access_key_id": "KEY"}],
    )
    def test_incomplete_credentials_load(self, bad_credentials):
        """Test that incomplete credentials passed in credentials.yml raises exception."""
        with pytest.raises(PartialCredentialsError):
            PickleS3DataSet(
                filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=bad_credentials
            )

    def test_incorrect_credentials_load(self):
        """Test that incorrect credential keys won't instantiate dataset."""
        pattern = "unexpected keyword argument"
        with pytest.raises(TypeError, match=pattern):
            PickleS3DataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME,
                credentials={"access_token": "TOKEN", "access_key": "KEY"},
            )

    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_access_key_id": None, "aws_secret_access_key": None}, {}, None],
    )
    def test_empty_credentials_load(self, bad_credentials):
        s3_data_set = PickleS3DataSet(
            filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=bad_credentials
        )
        pattern = r"Failed while loading data from data set PickleS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            s3_data_set.load()

    def test_pass_credentials(self, mocker):
        """Test that AWS credentials are passed successfully into boto3
        client instantiation on creating S3 connection."""
        mocker.patch("s3fs.core.boto3.Session.client")
        s3_data_set = PickleS3DataSet(
            filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=AWS_CREDENTIALS
        )
        pattern = r"Failed while loading data from data set PickleS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            s3_data_set.load()

        assert s3fs.core.boto3.Session.client.call_count == 1
        args, kwargs = s3fs.core.boto3.Session.client.call_args_list[0]
        assert args == ("s3",)
        for k, v in AWS_CREDENTIALS.items():
            assert kwargs[k] == v

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save(self, s3_data_set):
        """Test saving the data to S3."""
        new_data = {"x": "y"}
        s3_data_set.save(new_data)
        loaded_data = s3_data_set.load()
        assert loaded_data == new_data

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save_args(self, s3_data_set_with_args):
        """Test saving the data to S3 with options."""
        new_data = {"x": "y"}
        s3_data_set_with_args.save(new_data)
        loaded_data = s3_data_set_with_args.load()
        assert loaded_data == new_data

    def test_serializable(self, s3_data_set):
        ForkingPickler.dumps(s3_data_set)


@pytest.mark.usefixtures("s3fs_cleanup", "mocked_s3_bucket")
class TestPickleS3DataSetVersioned:
    def test_exists(self, versioned_s3_data_set):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_s3_data_set.exists()

        versioned_s3_data_set.save(DUMMY_PICKABLE_OBJECT)
        assert versioned_s3_data_set.exists()

    def test_no_versions(self, versioned_s3_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for PickleS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_s3_data_set.load()

    @pytest.mark.usefixtures("mocked_s3_object_versioned")
    def test_prevent_override(self, versioned_s3_data_set):
        """Check the error when attempting to override the data set if the
        corresponding pickled object for a given save version already exists in S3."""
        pattern = (
            r"Save path \`.+\` for PickleS3DataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_s3_data_set.save(DUMMY_PICKABLE_OBJECT)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_s3_data_set, load_version, save_version
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save path `{b}/{f}/{sv}/{f}` did not match load path "
            r"`{b}/{f}/{lv}/{f}` for PickleS3DataSet\(.+\)".format(
                b=BUCKET_NAME, f=FILENAME, sv=save_version, lv=load_version
            )
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_s3_data_set.save(DUMMY_PICKABLE_OBJECT)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        ds = PickleS3DataSet(filepath=FILENAME, bucket_name=BUCKET_NAME)
        ds_versioned = PickleS3DataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            version=Version(load_version, save_version),
        )
        assert FILENAME in str(ds)
        assert "version" not in str(ds)

        assert FILENAME in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
