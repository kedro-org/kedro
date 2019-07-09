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

# pylint: disable=protected-access,no-member
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest
import s3fs
from botocore.exceptions import PartialCredentialsError
from moto import mock_s3
from pandas.util.testing import assert_frame_equal

from kedro.contrib.io.parquet import ParquetS3DataSet
from kedro.io import DataSetError

FILENAME = "test.parquet"
BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(
    aws_access_key_id="FAKE_ACCESS_KEY", aws_secret_access_key="FAKE_SECRET_KEY"
)


@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(params=[None])
def save_args(request):
    return request.param


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def dummy_dataframe() -> pd.DataFrame:
    return pd.DataFrame(
        {"Name": ["Alex", "Bob", "Clarke", "Dave"], "Age": [31, 12, 65, 29]}
    )


@pytest.fixture
def mocked_s3_object(mocked_s3_bucket, dummy_dataframe: pd.DataFrame):
    """Creates test data and adds it to mocked S3 bucket."""
    table = pa.Table.from_pandas(dummy_dataframe)
    pq.write_table(table, FILENAME)

    with open(FILENAME, 'rb') as f:
        object_data = f.read()
        mocked_s3_bucket.put_object(
            Bucket=BUCKET_NAME, Key=FILENAME, Body=object_data
        )
    return mocked_s3_bucket


@pytest.fixture
def s3_data_set(load_args, save_args):
    return ParquetS3DataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials={'aws_access_key_id': 'YOUR_KEY', 'aws_secret_access_key': 'YOUR SECRET'},
        load_args=load_args,
        save_args=save_args,
    )


class TestParquetS3DataSet:
    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_secret_access_key": "SECRET"}, {"aws_access_key_id": "KEY"}],
    )
    def test_incomplete_credentials_load(self, bad_credentials):
        """Test that incomplete credentials passed in credentials.yml raises exception."""
        with pytest.raises(PartialCredentialsError):
            ParquetS3DataSet(
                filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=bad_credentials
            )

    def test_incorrect_credentials_load(self):
        """Test that incorrect credential keys won't instantiate dataset."""
        pattern = "unexpected keyword argument"
        with pytest.raises(TypeError, match=pattern):
            ParquetS3DataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME,
                credentials={"access_token": "TOKEN", "access_key": "KEY"},
            )

    @pytest.mark.parametrize(
        "bad_credentials",
        [{"aws_access_key_id": None, "aws_secret_access_key": None}, {}, None],
    )
    def test_empty_credentials_load(self, bad_credentials):
        parquet_data_set = ParquetS3DataSet(
            filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=bad_credentials
        )
        pattern = r"Failed while loading data from data set ParquetS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            parquet_data_set.load()

    def test_pass_credentials(self, mocker):
        """Test that AWS credentials are passed successfully into boto3
        client instantiation on creating S3 connection."""
        mocker.patch("s3fs.core.boto3.Session.client")
        s3_data_set = ParquetS3DataSet(
            filepath=FILENAME, bucket_name=BUCKET_NAME, credentials=AWS_CREDENTIALS
        )
        pattern = r"Failed while loading data from data set ParquetS3DataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            s3_data_set.load()

        assert s3fs.core.boto3.Session.client.call_count == 1
        args, kwargs = s3fs.core.boto3.Session.client.call_args_list[0]
        assert args == ("s3",)
        for k, v in AWS_CREDENTIALS.items():
            assert kwargs[k] == v

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_load_data(self, s3_data_set, dummy_dataframe):
        """Test loading the data from S3."""
        loaded_data = s3_data_set.load()
        assert_frame_equal(loaded_data, dummy_dataframe)

    @pytest.mark.usefixtures("mocked_s3_object")
    def test_save_data(self, s3_data_set):
        """Test saving the data to S3."""
        new_data = pd.DataFrame(
            {"col1": ["a", "b"], "col2": ["c", "d"], "col3": ["e", "f"]}
        )
        s3_data_set.save(new_data)
        loaded_data = s3_data_set.load()
        assert_frame_equal(loaded_data, new_data)

    @pytest.mark.usefixtures("mocked_s3_bucket")
    def test_exists(self, s3_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not s3_data_set.exists()
        s3_data_set.save(dummy_dataframe)
        assert s3_data_set.exists()

    @mock_s3
    def test_exists_raises_error(self, s3_data_set):
        """Check the error if the given S3 bucket doesn't exist."""
        with pytest.raises(DataSetError, match="NoSuchBucket"):
            s3_data_set.exists()
