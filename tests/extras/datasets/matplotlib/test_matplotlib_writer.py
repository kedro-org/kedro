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


import json
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import pytest
import s3fs
from moto import mock_s3
from s3fs import S3FileSystem

from kedro.extras.datasets.matplotlib import MatplotlibWriter
from kedro.io import DataSetError, Version

BUCKET_NAME = "test_bucket"
AWS_CREDENTIALS = dict(aws_access_key_id="testing", aws_secret_access_key="testing")
CREDENTIALS = {"client_kwargs": AWS_CREDENTIALS}
KEY_PATH = "matplotlib"
COLOUR_LIST = ["blue", "green", "red"]
FULL_PATH = "s3://{}/{}".format(BUCKET_NAME, KEY_PATH)

matplotlib.use("Agg")  # Disable interactive mode


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


@pytest.fixture()
def s3fs_cleanup():
    # clear cache for clean mocked s3 bucket each time
    yield
    S3FileSystem.cachable = False


@pytest.fixture
def plot_writer(
    mocked_s3_bucket, fs_args, save_args
):  # pylint: disable=unused-argument
    return MatplotlibWriter(
        filepath=FULL_PATH,
        credentials=CREDENTIALS,
        fs_args=fs_args,
        save_args=save_args,
    )


@pytest.fixture
def versioned_plot_writer(tmp_path, load_version, save_version):
    filepath = (tmp_path / "matplotlib.png").as_posix()
    return MatplotlibWriter(
        filepath=filepath, version=Version(load_version, save_version)
    )


class TestMatplotlibWriter:
    @pytest.mark.parametrize("save_args", [{"k1": "v1"}], indirect=True)
    def test_save_data(
        self, tmp_path, mock_single_plot, plot_writer, mocked_s3_bucket, save_args
    ):
        """Test saving single matplotlib plot to S3."""
        plot_writer.save(mock_single_plot)

        download_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        plt.savefig(str(actual_filepath))

        mocked_s3_bucket.download_file(BUCKET_NAME, KEY_PATH, str(download_path))

        assert actual_filepath.read_bytes() == download_path.read_bytes()
        assert plot_writer._fs_open_args_save == {"mode": "wb"}
        for key, value in save_args.items():
            assert plot_writer._save_args[key] == value

    def test_list_save(self, tmp_path, mock_list_plot, plot_writer, mocked_s3_bucket):
        """Test saving list of plots to S3."""

        plot_writer.save(mock_list_plot)

        for index in range(5):
            download_path = tmp_path / "downloaded_image.png"
            actual_filepath = tmp_path / "locally_saved.png"

            mock_list_plot[index].savefig(str(actual_filepath))
            _key_path = "{}/{}.png".format(KEY_PATH, index)
            mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(download_path))

            assert actual_filepath.read_bytes() == download_path.read_bytes()

    def test_dict_save(self, tmp_path, mock_dict_plot, plot_writer, mocked_s3_bucket):
        """Test saving dictionary of plots to S3."""

        plot_writer.save(mock_dict_plot)

        for colour in COLOUR_LIST:

            download_path = tmp_path / "downloaded_image.png"
            actual_filepath = tmp_path / "locally_saved.png"

            mock_dict_plot[colour].savefig(str(actual_filepath))

            _key_path = "{}/{}".format(KEY_PATH, colour)

            mocked_s3_bucket.download_file(BUCKET_NAME, _key_path, str(download_path))

            assert actual_filepath.read_bytes() == download_path.read_bytes()

    def test_fs_args(self, tmp_path, mock_single_plot, mocked_encrypted_s3_bucket):
        """Test writing to encrypted bucket"""
        normal_encryped_writer = MatplotlibWriter(
            fs_args={"s3_additional_kwargs": {"ServerSideEncryption": "AES256"}},
            filepath=FULL_PATH,
            credentials=CREDENTIALS,
        )

        normal_encryped_writer.save(mock_single_plot)

        download_path = tmp_path / "downloaded_image.png"
        actual_filepath = tmp_path / "locally_saved.png"

        mock_single_plot.savefig(str(actual_filepath))

        mocked_encrypted_s3_bucket.download_file(
            BUCKET_NAME, KEY_PATH, str(download_path)
        )

        assert actual_filepath.read_bytes() == download_path.read_bytes()

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_save": {"mode": "w", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, plot_writer, fs_args):
        assert plot_writer._fs_open_args_save == fs_args["open_args_save"]

    def test_load_fail(self, plot_writer):
        pattern = r"Loading not supported for `MatplotlibWriter`"
        with pytest.raises(DataSetError, match=pattern):
            plot_writer.load()

    @pytest.mark.usefixtures("s3fs_cleanup")
    def test_exists_single(self, mock_single_plot, plot_writer):
        assert not plot_writer.exists()
        plot_writer.save(mock_single_plot)
        assert plot_writer.exists()

    @pytest.mark.usefixtures("s3fs_cleanup")
    def test_exists_multiple(self, mock_dict_plot, plot_writer):
        assert not plot_writer.exists()
        plot_writer.save(mock_dict_plot)
        assert plot_writer.exists()

    def test_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        data_set = MatplotlibWriter(filepath=FULL_PATH)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(
            "{}/{}".format(BUCKET_NAME, KEY_PATH)
        )


class TestMatplotlibWriterVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "chart.png"
        chart = MatplotlibWriter(filepath=filepath)
        chart_versioned = MatplotlibWriter(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(chart)
        assert "version" not in str(chart)

        assert filepath in str(chart_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(chart_versioned)

    def test_prevent_overwrite(self, mock_single_plot, versioned_plot_writer):
        """Check the error when attempting to override the data set if the
        corresponding matplotlib file for a given save version already exists."""
        versioned_plot_writer.save(mock_single_plot)
        pattern = (
            r"Save path \`.+\` for MatplotlibWriter\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_plot_writer.save(mock_single_plot)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, load_version, save_version, mock_single_plot, versioned_plot_writer
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for MatplotlibWriter\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_plot_writer.save(mock_single_plot)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            MatplotlibWriter(
                filepath="https://example.com/file.png", version=Version(None, None)
            )

    def test_no_versions(self, versioned_plot_writer):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for MatplotlibWriter\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_plot_writer.load()

    def test_exists(self, versioned_plot_writer, mock_single_plot):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_plot_writer.exists()
        versioned_plot_writer.save(mock_single_plot)
        assert versioned_plot_writer.exists()

    def test_exists_multiple(self, versioned_plot_writer, mock_list_plot):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_plot_writer.exists()
        versioned_plot_writer.save(mock_list_plot)
        assert versioned_plot_writer.exists()

    def test_save_data(self, versioned_plot_writer, mock_single_plot, tmp_path):
        """Test saving dictionary of plots with enabled versioning."""
        versioned_plot_writer.save(mock_single_plot)

        test_path = tmp_path / "test_image.png"
        actual_filepath = Path(versioned_plot_writer._get_load_path().as_posix())

        plt.savefig(str(test_path))

        assert actual_filepath.read_bytes() == test_path.read_bytes()

    def test_list_save(self, tmp_path, mock_list_plot, versioned_plot_writer):
        """Test saving list of plots to with enabled versioning."""

        versioned_plot_writer.save(mock_list_plot)

        for index in range(5):

            test_path = tmp_path / "test_image.png"
            versioned_filepath = str(versioned_plot_writer._get_load_path())

            mock_list_plot[index].savefig(str(test_path))
            actual_filepath = Path("{}/{}.png".format(versioned_filepath, index))

            assert actual_filepath.read_bytes() == test_path.read_bytes()

    def test_dict_save(self, tmp_path, mock_dict_plot, versioned_plot_writer):
        """Test saving dictionary of plots with enabled versioning."""

        versioned_plot_writer.save(mock_dict_plot)

        for colour in COLOUR_LIST:
            test_path = tmp_path / "test_image.png"
            versioned_filepath = str(versioned_plot_writer._get_load_path())

            mock_dict_plot[colour].savefig(str(test_path))
            actual_filepath = Path("{}/{}".format(versioned_filepath, colour))

            assert actual_filepath.read_bytes() == test_path.read_bytes()
