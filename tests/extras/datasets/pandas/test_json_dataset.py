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

from pathlib import PurePosixPath

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import JSONDataSet
from kedro.io import DataSetError
from kedro.io.core import Version


@pytest.fixture
def filepath_json(tmp_path):
    return str(tmp_path / "test.json")


@pytest.fixture
def json_data_set(filepath_json, load_args, save_args):
    return JSONDataSet(filepath=filepath_json, load_args=load_args, save_args=save_args)


@pytest.fixture
def versioned_json_data_set(filepath_json, load_version, save_version):
    return JSONDataSet(
        filepath=filepath_json, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestJSONDataSet:
    def test_save_and_load(self, json_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        json_data_set.save(dummy_dataframe)
        reloaded = json_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)

    def test_exists(self, json_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not json_data_set.exists()
        json_data_set.save(dummy_dataframe)
        assert json_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, json_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert json_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, json_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert json_data_set._save_args[key] == value

    def test_load_missing_file(self, json_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set JSONDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            json_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.json", S3FileSystem),
            ("file:///tmp/test.json", LocalFileSystem),
            ("/tmp/test.json", LocalFileSystem),
            ("gcs://bucket/file.json", GCSFileSystem),
            ("https://example.com/file.json", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = JSONDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        # _strip_protocol() doesn't strip http(s) protocol
        if data_set._protocol == "https":
            path = filepath.split("://")[-1]
        else:
            path = data_set._fs._strip_protocol(filepath)

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.json"
        data_set = JSONDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)


class TestJSONDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.json"
        ds = JSONDataSet(filepath=filepath)
        ds_versioned = JSONDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "JSONDataSet" in str(ds_versioned)
        assert "JSONDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)

    def test_save_and_load(self, versioned_json_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_json_data_set.save(dummy_dataframe)
        reloaded_df = versioned_json_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_json_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for JSONDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.load()

    def test_exists(self, versioned_json_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_json_data_set.exists()
        versioned_json_data_set.save(dummy_dataframe)
        assert versioned_json_data_set.exists()

    def test_prevent_overwrite(self, versioned_json_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_json_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for JSONDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_json_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_json_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for JSONDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_json_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            JSONDataSet(
                filepath="https://example.com/file.json", version=Version(None, None)
            )
