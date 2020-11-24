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

import numpy
import pandas
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import AVRODataSet
from kedro.extras.datasets.pandas.avro_dataset import infer_pandas_dtype_to_avro_type
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER

FILENAME = "test.avro"


@pytest.fixture
@pytest.mark.parametrize("tmp_path", ["/tmp"], indirect=True)
def filepath_avro(tmp_path):
    return (tmp_path / FILENAME).as_posix()


@pytest.fixture
def dummy_data():
    return pandas.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def avro_pd_data_set(filepath_avro):
    return AVRODataSet(filepath=filepath_avro)


class TestPandasAvroDataSet:
    def test_credentials_propagated(self, mocker):
        """Test propagating credentials for connecting to GCS"""
        mock_fs = mocker.patch("fsspec.filesystem")
        credentials = {"key": "value"}

        AVRODataSet(filepath=FILENAME, credentials=credentials)

        mock_fs.assert_called_once_with("file", **credentials)

    def test_save_and_load(self, tmp_path, dummy_data):
        """Test saving and reloading the data set."""
        filepath = (tmp_path / FILENAME).as_posix()
        data_set = AVRODataSet(filepath=filepath)
        data_set.save(dummy_data)
        reloaded = data_set.load()
        assert dummy_data.equals(reloaded)

        data_set = AVRODataSet(filepath=tmp_path.as_posix())
        pattern = r"Saving AVRODataSet to a directory is not supported."
        with pytest.raises(DataSetError, match=pattern):
            data_set.save(dummy_data)

    def test_exists(self, avro_pd_data_set, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not avro_pd_data_set.exists()
        avro_pd_data_set.save(dummy_data)
        assert avro_pd_data_set.exists()

        def patch_error():
            raise DataSetError("test")

        avro_pd_data_set._get_load_path = patch_error
        assert not avro_pd_data_set.exists()

    def test_load_missing_file(self, avro_pd_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set AVRODataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            avro_pd_data_set.load()

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


class TestInferPandasToAvroType:
    def test_happy_path(self):
        tests = [
            {"in": numpy.dtype("bool"), "want": {"type": ["null", "boolean"]}},
            {"in": numpy.bool_, "want": {"type": ["null", "boolean"]}},
            {"in": numpy.int8, "want": {"type": ["null", "int"]}},
            {"in": numpy.int16, "want": {"type": ["null", "int"]}},
            {"in": numpy.int32, "want": {"type": ["null", "int"]}},
            {"in": numpy.uint8, "want": {"type": ["null", "int"]}},
            {"in": numpy.uint16, "want": {"type": ["null", "int"]}},
            {"in": numpy.uint32, "want": {"type": ["null", "int"]}},
            {"in": numpy.int64, "want": {"type": ["null", "long"]}},
            {"in": numpy.uint64, "want": {"type": ["null", "long"]}},
            {"in": numpy.object_, "want": {"type": ["null", "string"]}},
            {"in": numpy.dtype("O"), "want": {"type": ["null", "string"]}},
            {"in": numpy.str_, "want": {"type": ["null", "string"]}},
            {"in": numpy.float32, "want": {"type": ["null", "float"]}},
            {"in": numpy.float64, "want": {"type": ["null", "double"]}},
            {
                "in": numpy.datetime64,
                "want": {
                    "type": [
                        "null",
                        {"type": "long", "logicalType": "timestamp-micros"},
                    ]
                },
            },
            {
                "in": pandas.DatetimeTZDtype,
                "want": {
                    "type": [
                        "null",
                        {"type": "long", "logicalType": "timestamp-micros"},
                    ]
                },
            },
            {
                "in": pandas.Timestamp,
                "want": {
                    "type": [
                        "null",
                        {"type": "long", "logicalType": "timestamp-micros"},
                    ]
                },
            },
            {"in": numpy.nan, "want": {"type": ["null", "string"]}},
        ]

        for test in tests:
            got = infer_pandas_dtype_to_avro_type(test["in"])
            assert got == test["want"]

    def test_unhappy_path(self):
        pattern = r"Invalid type: .*."
        with pytest.raises(TypeError, match=pattern):
            infer_pandas_dtype_to_avro_type(int)
