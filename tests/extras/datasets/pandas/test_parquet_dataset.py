# Copyright 2020 QuantumBlack Visual Analytics Limited
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

from pathlib import PurePosixPath

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import ParquetDataSet
from kedro.io import DataSetError
from kedro.io.core import Version

FILENAME = "test.parquet"


@pytest.fixture
def filepath_parquet(tmp_path):
    return str(tmp_path / FILENAME)


@pytest.fixture
def parquet_data_set(filepath_parquet, load_args, save_args, fs_args):
    return ParquetDataSet(
        filepath=filepath_parquet,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_parquet_data_set(filepath_parquet, load_version, save_version):
    return ParquetDataSet(
        filepath=filepath_parquet, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestParquetDataSet:
    def test_credentials_propagated(self, mocker):
        """Test propagating credentials for connecting to GCS"""
        mock_fs = mocker.patch("fsspec.filesystem")
        credentials = {"key": "value"}

        ParquetDataSet(filepath=FILENAME, credentials=credentials)

        mock_fs.assert_called_once_with("file", **credentials)

    def test_save_and_load(self, parquet_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        parquet_data_set.save(dummy_dataframe)
        reloaded = parquet_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)
        assert parquet_data_set._fs_open_args_load == {}

    def test_exists(self, parquet_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not parquet_data_set.exists()
        parquet_data_set.save(dummy_dataframe)
        assert parquet_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, parquet_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert parquet_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, parquet_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert parquet_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "r", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, parquet_data_set, fs_args):
        assert parquet_data_set._fs_open_args_load == fs_args["open_args_load"]

    def test_load_missing_file(self, parquet_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set ParquetDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            parquet_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.parquet", S3FileSystem),
            ("file:///tmp/test.parquet", LocalFileSystem),
            ("/tmp/test.parquet", LocalFileSystem),
            ("gcs://bucket/file.parquet", GCSFileSystem),
            ("https://example.com/file.parquet", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = ParquetDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        # _strip_protocol() doesn't strip http(s) protocol
        if data_set._protocol == "https":
            path = filepath.split("://")[-1]
        else:
            path = data_set._fs._strip_protocol(filepath)

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    @pytest.mark.parametrize(
        "protocol,path", [("https://", "example.com/"), ("s3://", "bucket/")]
    )
    def test_catalog_release(self, protocol, path, mocker):
        filepath = protocol + path + FILENAME
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        data_set = ParquetDataSet(filepath=filepath)
        data_set.release()
        if protocol != "https://":
            filepath = path + FILENAME
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestParquetDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        ds = ParquetDataSet(filepath=FILENAME)
        ds_versioned = ParquetDataSet(
            filepath=FILENAME, version=Version(load_version, save_version)
        )
        assert FILENAME in str(ds)
        assert "version" not in str(ds)

        assert FILENAME in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "ParquetDataSet" in str(ds_versioned)
        assert "ParquetDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_parquet_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_parquet_data_set.save(dummy_dataframe)
        reloaded_df = versioned_parquet_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_parquet_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ParquetDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.load()

    def test_exists(self, versioned_parquet_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_parquet_data_set.exists()
        versioned_parquet_data_set.save(dummy_dataframe)
        assert versioned_parquet_data_set.exists()

    def test_prevent_overwrite(self, versioned_parquet_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding parquet file for a given save version already exists."""
        versioned_parquet_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for ParquetDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_parquet_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for ParquetDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_parquet_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            ParquetDataSet(
                filepath="https://example.com/test.parquet", version=Version(None, None)
            )
