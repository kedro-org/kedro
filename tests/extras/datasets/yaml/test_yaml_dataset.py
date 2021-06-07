# Copyright 2021 QuantumBlack Visual Analytics Limited
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

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.yaml import YAMLDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version


@pytest.fixture
def filepath_yaml(tmp_path):
    return (tmp_path / "test.yaml").as_posix()


@pytest.fixture
def yaml_data_set(filepath_yaml, save_args, fs_args):
    return YAMLDataSet(filepath=filepath_yaml, save_args=save_args, fs_args=fs_args)


@pytest.fixture
def versioned_yaml_data_set(filepath_yaml, load_version, save_version):
    return YAMLDataSet(
        filepath=filepath_yaml, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_data():
    return {"col1": 1, "col2": 2, "col3": 3}


class TestYAMLDataSet:
    def test_save_and_load(self, yaml_data_set, dummy_data):
        """Test saving and reloading the data set."""
        yaml_data_set.save(dummy_data)
        reloaded = yaml_data_set.load()
        assert dummy_data == reloaded
        assert yaml_data_set._fs_open_args_load == {}
        assert yaml_data_set._fs_open_args_save == {"mode": "w"}

    def test_exists(self, yaml_data_set, dummy_data):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not yaml_data_set.exists()
        yaml_data_set.save(dummy_data)
        assert yaml_data_set.exists()

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, yaml_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert yaml_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, yaml_data_set, fs_args):
        assert yaml_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert yaml_data_set._fs_open_args_save == {"mode": "w"}  # default unchanged

    def test_load_missing_file(self, yaml_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set YAMLDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            yaml_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.yaml", S3FileSystem),
            ("file:///tmp/test.yaml", LocalFileSystem),
            ("/tmp/test.yaml", LocalFileSystem),
            ("gcs://bucket/file.yaml", GCSFileSystem),
            ("https://example.com/file.yaml", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = YAMLDataSet(filepath=filepath)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.yaml"
        data_set = YAMLDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_dataframe_support(self, yaml_data_set):
        data = pd.DataFrame({"col1": [1, 2], "col2": [4, 5]})
        yaml_data_set.save(data.to_dict())
        reloaded = yaml_data_set.load()
        assert isinstance(reloaded, dict)

        data_df = pd.DataFrame.from_dict(reloaded)
        assert_frame_equal(data, data_df)


class TestYAMLDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.yaml"
        ds = YAMLDataSet(filepath=filepath)
        ds_versioned = YAMLDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = f"version=Version(load={load_version}, save='{save_version}')"
        assert ver_str in str(ds_versioned)
        assert "YAMLDataSet" in str(ds_versioned)
        assert "YAMLDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        # Default save_args
        assert "save_args={'default_flow_style': False}" in str(ds)
        assert "save_args={'default_flow_style': False}" in str(ds_versioned)

    def test_save_and_load(self, versioned_yaml_data_set, dummy_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_yaml_data_set.save(dummy_data)
        reloaded = versioned_yaml_data_set.load()
        assert dummy_data == reloaded

    def test_no_versions(self, versioned_yaml_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for YAMLDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_yaml_data_set.load()

    def test_exists(self, versioned_yaml_data_set, dummy_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_yaml_data_set.exists()
        versioned_yaml_data_set.save(dummy_data)
        assert versioned_yaml_data_set.exists()

    def test_prevent_overwrite(self, versioned_yaml_data_set, dummy_data):
        """Check the error when attempting to override the data set if the
        corresponding yaml file for a given save version already exists."""
        versioned_yaml_data_set.save(dummy_data)
        pattern = (
            r"Save path \`.+\` for YAMLDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_yaml_data_set.save(dummy_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_yaml_data_set, load_version, save_version, dummy_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for YAMLDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_yaml_data_set.save(dummy_data)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            YAMLDataSet(
                filepath="https://example.com/file.yaml", version=Version(None, None)
            )
