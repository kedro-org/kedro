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

from pathlib import PurePosixPath

import pytest

from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem
from fsspec.implementations.http import HTTPFileSystem

from kedro.extras.datasets.avro import AVRODataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


FILENAME = "test.avro"


@pytest.fixture
@pytest.mark.parametrize("tmp_path", ["/tmp"], indirect=True)
def filepath_avro(tmp_path):
    return (tmp_path / FILENAME).as_posix()


@pytest.fixture
def dummy_data():
    return [
        {'col1': 1, 'col2': 3, 'col3': 5},
        {'col1': 2, 'col2': 4, 'col3': 6},
    ]


schema = {
    "namespace": "example.avro",
    "type": "array",
    "name": "DataArray",
    "items": {
        "type": "record",
        "name": "DataElement",
        "fields": [
            {"name": "col1", "type": "int"},
            {"name": "col2", "type": "int"},
            {"name": "col3", "type": "int"},
        ],
    },
}


@pytest.fixture
def dummy_schema():
    return schema


@pytest.fixture
def avro_data_set(filepath_avro, load_args, save_args, fs_args):
    return AVRODataSet(
        filepath=filepath_avro, load_args=load_args, save_args=save_args, fs_args=fs_args,
    )


@pytest.fixture
def versioned_avro_data_set(filepath_avro, load_version, save_version):
    return AVRODataSet(filepath=filepath_avro, version=Version(load_version, save_version),)


class TestAvroDataSet:
    def test_credentials_propagated(self, mocker):
        """Test propagating credentials for connecting to GCS"""
        mock_fs = mocker.patch("fsspec.filesystem")
        credentials = {"key": "value"}

        AVRODataSet(filepath=FILENAME, credentials=credentials)

        mock_fs.assert_called_once_with("file", **credentials)

    def test_save_and_load(self, tmp_path, dummy_data, dummy_schema):
        """Test saving and reloading the data set."""
        filepath = (tmp_path / FILENAME).as_posix()
        data_set = AVRODataSet(filepath=filepath, save_args={"schema": dummy_schema})
        data_set.save(dummy_data)
        reloaded = data_set.load()

        assert dummy_data == reloaded

    @pytest.mark.parametrize("save_args", [{"schema": schema,}], indirect=True)
    def test_exists(self, avro_data_set, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not avro_data_set.exists()
        # avro_data_set.save(dummy_data)
        # assert avro_data_set.exists()

    def test_load_missing_file(self, avro_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set AVRODataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            avro_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            (f"s3://bucket/{FILENAME}", S3FileSystem),
            (f"file:///tmp/{FILENAME}", LocalFileSystem),
            (f"/tmp/{FILENAME}", LocalFileSystem),
            (f"gcs://bucket/{FILENAME}", GCSFileSystem),
            (f"https://example.com/{FILENAME}", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = AVRODataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    @pytest.mark.parametrize(
        "protocol,path", [("https://", "example.com/"), ("s3://", "bucket/")]
    )
    def test_catalog_release(self, protocol, path, mocker):
        filepath = f"{protocol}{path}{FILENAME}"
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        data_set = AVRODataSet(filepath=filepath)
        data_set.release()
        if protocol != "https://":
            filepath = path + FILENAME
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_write_to_dir(self, dummy_data, tmp_path):
        data_set = AVRODataSet(filepath=tmp_path.as_posix(), save_args={"schema": schema})
        pattern = "Saving AVRODataSet to a directory is not supported"

        with pytest.raises(DataSetError, match=pattern):
            data_set.save(dummy_data)
