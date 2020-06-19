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

from pathlib import Path, PurePosixPath

import holoviews as hv
import pytest
from adlfs import AzureBlobFileSystem
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.holoviews import HoloviewsWriter
from kedro.io import DataSetError, Version
from kedro.io.core import PROTOCOL_DELIMITER


@pytest.fixture
def filepath_png(tmp_path):
    return str(tmp_path / "test.png")


@pytest.fixture(scope="module")
def dummy_hv_object():
    return hv.Curve(range(10))


@pytest.fixture
def hv_writer(filepath_png, save_args, fs_args):
    return HoloviewsWriter(filepath_png, save_args=save_args, fs_args=fs_args)


@pytest.fixture
def versioned_hv_writer(filepath_png, load_version, save_version):
    return HoloviewsWriter(filepath_png, version=Version(load_version, save_version))


class TestHoloviewsWriter:
    def test_save_data(self, tmp_path, dummy_hv_object, hv_writer):
        """Test saving Holoviews object."""
        hv_writer.save(dummy_hv_object)

        actual_filepath = Path(hv_writer._filepath)
        test_filepath = tmp_path / "locally_saved.png"
        hv.save(dummy_hv_object, test_filepath)

        assert actual_filepath.read_bytes() == test_filepath.read_bytes()
        assert hv_writer._fs_open_args_save == {"mode": "wb"}
        assert hv_writer._save_args == {"fmt": "png"}

    @pytest.mark.parametrize(
        "fs_args",
        [
            {
                "storage_option": "value",
                "open_args_save": {"mode": "w", "compression": "gzip"},
            }
        ],
    )
    def test_open_extra_args(self, tmp_path, fs_args, mocker):
        fs_mock = mocker.patch("fsspec.filesystem")
        writer = HoloviewsWriter(str(tmp_path), fs_args)

        fs_mock.assert_called_once_with("file", auto_mkdir=True, storage_option="value")
        assert writer._fs_open_args_save == fs_args["open_args_save"]

    def test_load_fail(self, hv_writer):
        pattern = r"Loading not supported for `HoloviewsWriter`"
        with pytest.raises(DataSetError, match=pattern):
            hv_writer.load()

    def test_exists(self, dummy_hv_object, hv_writer):
        assert not hv_writer.exists()
        hv_writer.save(dummy_hv_object)
        assert hv_writer.exists()

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.png"
        data_set = HoloviewsWriter(filepath=filepath)
        assert data_set._version_cache.currsize == 0  # no cache if unversioned
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)
        assert data_set._version_cache.currsize == 0

    @pytest.mark.parametrize("save_args", [{"k1": "v1", "fmt": "svg"}], indirect=True)
    def test_save_extra_params(self, hv_writer, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert hv_writer._save_args[key] == value

    @pytest.mark.parametrize(
        "filepath,instance_type,credentials",
        [
            ("s3://bucket/file.png", S3FileSystem, {}),
            ("file:///tmp/test.png", LocalFileSystem, {}),
            ("/tmp/test.png", LocalFileSystem, {}),
            ("gcs://bucket/file.png", GCSFileSystem, {}),
            ("https://example.com/file.png", HTTPFileSystem, {}),
            (
                "abfs://bucket/file.png",
                AzureBlobFileSystem,
                {"account_name": "test", "account_key": "test"},
            ),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type, credentials):
        data_set = HoloviewsWriter(filepath=filepath, credentials=credentials)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)


class TestHoloviewsWriterVersioned:
    def test_version_str_repr(self, hv_writer, versioned_hv_writer):
        """Test that version is in string representation of the class instance
        when applicable."""

        assert str(hv_writer._filepath) in str(hv_writer)
        assert "version=" not in str(hv_writer)
        assert "protocol" in str(hv_writer)
        assert "save_args" in str(hv_writer)

        assert str(versioned_hv_writer._filepath) in str(versioned_hv_writer)
        ver_str = f"version={versioned_hv_writer._version}"
        assert ver_str in str(versioned_hv_writer)
        assert "protocol" in str(versioned_hv_writer)
        assert "save_args" in str(versioned_hv_writer)

    def test_prevent_overwrite(self, dummy_hv_object, versioned_hv_writer):
        """Check the error when attempting to override the data set if the
        corresponding file for a given save version already exists."""
        versioned_hv_writer.save(dummy_hv_object)
        pattern = (
            r"Save path \`.+\` for HoloviewsWriter\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_hv_writer.save(dummy_hv_object)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, load_version, save_version, dummy_hv_object, versioned_hv_writer
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            fr"Save version `{save_version}` did not match load version "
            fr"`{load_version}` for HoloviewsWriter\(.+\)"
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_hv_writer.save(dummy_hv_object)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            HoloviewsWriter(
                filepath="https://example.com/file.png", version=Version(None, None)
            )

    def test_no_versions(self, versioned_hv_writer):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for HoloviewsWriter\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_hv_writer.load()

    def test_exists(self, versioned_hv_writer, dummy_hv_object):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_hv_writer.exists()
        versioned_hv_writer.save(dummy_hv_object)
        assert versioned_hv_writer.exists()

    def test_save_data(self, versioned_hv_writer, dummy_hv_object, tmp_path):
        """Test saving Holoviews object with enabled versioning."""
        versioned_hv_writer.save(dummy_hv_object)

        test_filepath = tmp_path / "test_image.png"
        actual_filepath = Path(versioned_hv_writer._get_load_path())

        hv.save(dummy_hv_object, test_filepath)

        assert actual_filepath.read_bytes() == test_filepath.read_bytes()
