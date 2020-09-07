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

from email.message import EmailMessage
from email.policy import default
from pathlib import PurePosixPath

import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.email import EmailMessageDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_message(tmp_path):
    return (tmp_path / "test").as_posix()


@pytest.fixture
def message_data_set(filepath_message, load_args, save_args, fs_args):
    return EmailMessageDataSet(
        filepath=filepath_message,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_message_data_set(filepath_message, load_version, save_version):
    return EmailMessageDataSet(
        filepath=filepath_message, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_msg():
    string_to_write = "what would you do if you were invisable for one day????"

    # Create a text/plain message
    msg = EmailMessage()
    msg.set_content(string_to_write)
    msg["Subject"] = "invisibility"
    msg["From"] = '"sin studly17"'
    msg["To"] = '"strong bad"'

    return msg


class TestEmailMessageDataSet:
    def test_save_and_load(self, message_data_set, dummy_msg):
        """Test saving and reloading the data set."""
        message_data_set.save(dummy_msg)
        reloaded = message_data_set.load()
        assert dummy_msg.__dict__ == reloaded.__dict__
        assert message_data_set._fs_open_args_load == {"mode": "r"}
        assert message_data_set._fs_open_args_save == {"mode": "w"}

    def test_exists(self, message_data_set, dummy_msg):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not message_data_set.exists()
        message_data_set.save(dummy_msg)
        assert message_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, message_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert message_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, message_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert message_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, message_data_set, fs_args):
        assert message_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert message_data_set._fs_open_args_save == {"mode": "w"}  # default unchanged

    def test_load_missing_file(self, message_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set EmailMessageDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            message_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file", S3FileSystem),
            ("file:///tmp/test", LocalFileSystem),
            ("/tmp/test", LocalFileSystem),
            ("gcs://bucket/file", GCSFileSystem),
            ("https://example.com/file", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = EmailMessageDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test"
        data_set = EmailMessageDataSet(filepath=filepath)
        assert data_set._version_cache.currsize == 0  # no cache if unversioned
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
        assert data_set._version_cache.currsize == 0


class TestEmailMessageDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test"
        ds = EmailMessageDataSet(filepath=filepath)
        ds_versioned = EmailMessageDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "EmailMessageDataSet" in str(ds_versioned)
        assert "EmailMessageDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        # Default parser_args
        assert f"parser_args={{'policy': {default}}}" in str(ds)
        assert f"parser_args={{'policy': {default}}}" in str(ds_versioned)

    def test_save_and_load(self, versioned_message_data_set, dummy_msg):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_message_data_set.save(dummy_msg)
        reloaded = versioned_message_data_set.load()
        assert dummy_msg.__dict__ == reloaded.__dict__

    def test_no_versions(self, versioned_message_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for EmailMessageDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_message_data_set.load()

    def test_exists(self, versioned_message_data_set, dummy_msg):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_message_data_set.exists()
        versioned_message_data_set.save(dummy_msg)
        assert versioned_message_data_set.exists()

    def test_prevent_overwrite(self, versioned_message_data_set, dummy_msg):
        """Check the error when attempting to override the data set if the
        corresponding text file for a given save version already exists."""
        versioned_message_data_set.save(dummy_msg)
        pattern = (
            r"Save path \`.+\` for EmailMessageDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_message_data_set.save(dummy_msg)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_message_data_set, load_version, save_version, dummy_msg
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            f"Save version `{save_version}` did not match "
            f"load version `{load_version}` for "
            r"EmailMessageDataSet\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_message_data_set.save(dummy_msg)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            EmailMessageDataSet(
                filepath="https://example.com/file", version=Version(None, None)
            )
