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


import json

import matplotlib.pyplot as plt
import pytest
import s3fs
from moto import mock_s3

from kedro.contrib.io.matplotlib import MatplotlibS3Writer
from kedro.io import DataSetError

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(aws_access_key_id="testing", aws_secret_access_key="testing")
KEY_PATH = "matplotlib"
COLOUR_LIST = ["blue", "green", "red"]


@pytest.fixture
def mock_single_plot():
    plt.plot([1, 2, 3], [4, 5, 6])
    return plt


@pytest.fixture
def mock_list_plot():
    plots_list = []
    colour = "red"
    for index in range(5):  # pylint: disable=unused-variable
        plots_list.append(plt.figure())
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
    return plots_list


@pytest.fixture
def mock_dict_plot():
    plots_dict = {}
    for colour in COLOUR_LIST:
        plots_dict[colour] = plt.figure()
        plt.plot([1, 2, 3], [4, 5, 6], color=colour)
        plt.close()
    return plots_dict


@pytest.fixture
def mocked_s3_bucket():
    """Create a bucket for testing using moto."""
    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        yield conn


@pytest.fixture
def mocked_encrypted_s3_bucket():
    bucket_policy = {
        "Version": "2012-10-17",
        "Id": "PutObjPolicy",
        "Statement": [
            {
                "Sid": "DenyUnEncryptedObjectUploads",
                "Effect": "Deny",
                "Principal": "*",
                "Action": "s3:PutObject",
                "Resource": "arn:aws:s3:::{}/*".format(BUCKET_NAME),
                "Condition": {"Null": {"s3:x-amz-server-side-encryption": "aws:kms"}},
            }
        ],
    }
    bucket_policy = json.dumps(bucket_policy)

    with mock_s3():
        conn = s3fs.core.boto3.client("s3", **AWS_CREDENTIALS)
        conn.create_bucket(Bucket=BUCKET_NAME)
        conn.put_bucket_policy(Bucket=BUCKET_NAME, Policy=bucket_policy)
        yield conn


@pytest.fixture
def plot_writer(mocked_s3_bucket):  # pylint: disable=unused-argument
    def _matplotlibwriters3():
        return MatplotlibS3Writer(
            bucket_name=BUCKET_NAME, filepath=KEY_PATH, credentials=AWS_CREDENTIALS
        )

    return _matplotlibwriters3()


def test_save_data(tmp_path, mock_single_plot, plot_writer, mocked_s3_bucket):
    """Test saving single matplotlib plot to S3."""

    plot_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    plt.savefig(str(actual_filepath))

    mocked_s3_bucket.download_file(BUCKET_NAME, KEY_PATH, str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_list_save(tmp_path, mock_list_plot, plot_writer, mocked_s3_bucket):
    """Test saving list of plots to S3."""

    plot_writer.save(mock_list_plot)

    for index in range(5):

        expected_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        mock_list_plot[index].savefig(str(actual_filepath))

        _key_path = KEY_PATH + "/" + str(index) + ".png"

        mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(expected_path))

        assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_dict_save(tmp_path, mock_dict_plot, plot_writer, mocked_s3_bucket):
    """Test saving dictionary of plots to S3."""

    plot_writer.save(mock_dict_plot)

    for colour in COLOUR_LIST:

        expected_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        mock_dict_plot[colour].savefig(str(actual_filepath))

        _key_path = KEY_PATH + "/" + colour

        mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(expected_path))

        assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_bad_credentials(mock_dict_plot):
    """Test writing with bad credentials"""
    bad_writer = MatplotlibS3Writer(
        bucket_name=BUCKET_NAME,
        filepath=KEY_PATH,
        credentials={
            "aws_access_key_id": "not_for_testing",
            "aws_secret_access_key": "definitely_not_for_testing",
        },
    )
    pattern = "InvalidAccessKeyId"

    with pytest.raises(DataSetError, match=pattern):
        bad_writer.save(mock_dict_plot)


def test_credentials(tmp_path, mock_single_plot, mocked_s3_bucket):
    """Test entering credentials"""
    normal_writer = MatplotlibS3Writer(
        bucket_name=BUCKET_NAME, filepath=KEY_PATH, credentials=AWS_CREDENTIALS
    )

    normal_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    plt.savefig(str(actual_filepath))

    mocked_s3_bucket.download_file(BUCKET_NAME, KEY_PATH, str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_s3_encryption(tmp_path, mock_single_plot, mocked_encrypted_s3_bucket):
    """Test writing to encrypted bucket"""
    normal_encryped_writer = MatplotlibS3Writer(
        bucket_name=BUCKET_NAME,
        s3fs_args={"s3_additional_kwargs": {"ServerSideEncryption": "AES256"}},
        filepath=KEY_PATH,
        credentials=AWS_CREDENTIALS,
    )

    normal_encryped_writer.save(mock_single_plot)

    expected_path = tmp_path / "downloaded_image.png"
    actual_filepath = tmp_path / "locally_saved.png"

    mock_single_plot.savefig(str(actual_filepath))

    mocked_encrypted_s3_bucket.download_file(BUCKET_NAME, KEY_PATH, str(expected_path))

    assert actual_filepath.read_bytes() == expected_path.read_bytes()


def test_load_fail(plot_writer):
    pattern = r"Loading not supported for `MatplotlibS3Writer`"
    with pytest.raises(DataSetError, match=pattern):
        plot_writer.load()


def test_exists_single(mock_single_plot, plot_writer):
    plot_writer.save(mock_single_plot)
    plot_writer.exists()


def test_exists_multiple(mock_dict_plot, plot_writer):
    plot_writer.save(mock_dict_plot)
    assert plot_writer.exists()
