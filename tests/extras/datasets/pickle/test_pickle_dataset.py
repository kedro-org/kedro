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

import pickle
from pathlib import PurePosixPath

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pickle import PickleDataSet
from kedro.io import DataSetError
from kedro.io.core import Version


@pytest.fixture
def filepath_pickle(tmp_path):
    return str(tmp_path / "test.pkl")


@pytest.fixture
def pickle_data_set(filepath_pickle, load_args, save_args, fs_args):
    return PickleDataSet(
        filepath=filepath_pickle,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_pickle_data_set(filepath_pickle, load_version, save_version):
    return PickleDataSet(
        filepath=filepath_pickle, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestPickleDataSet:
    def test_save_and_load(self, pickle_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        pickle_data_set.save(dummy_dataframe)
        reloaded = pickle_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)
        assert pickle_data_set._fs_open_args_load == {}
        assert pickle_data_set._fs_open_args_save == {"mode": "wb"}

    def test_exists(self, pickle_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not pickle_data_set.exists()
        pickle_data_set.save(dummy_dataframe)
        assert pickle_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "errors": "strict"}], indirect=True
    )
    def test_load_extra_params(self, pickle_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert pickle_data_set._load_args[key] == value

    @pytest.mark.parametrize("save_args", [{"k1": "v1", "protocol": 2}], indirect=True)
    def test_save_extra_params(self, pickle_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert pickle_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, pickle_data_set, fs_args):
        assert pickle_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert pickle_data_set._fs_open_args_save == {"mode": "wb"}  # default unchanged

    def test_load_missing_file(self, pickle_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set PickleDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            pickle_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.pkl", S3FileSystem),
            ("file:///tmp/test.pkl", LocalFileSystem),
            ("/tmp/test.pkl", LocalFileSystem),
            ("gcs://bucket/file.pkl", GCSFileSystem),
            ("https://example.com/file.pkl", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = PickleDataSet(filepath=filepath)
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
        filepath = "test.pkl"
        data_set = PickleDataSet(filepath=filepath)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_unserializable_data(self, pickle_data_set, dummy_dataframe, mocker):
        mocker.patch("pickle.dump", side_effect=pickle.PickleError)
        pattern = r".+ was not serialized due to:.*"

        with pytest.raises(DataSetError, match=pattern):
            pickle_data_set.save(dummy_dataframe)

    def test_invalid_backend(self):
        pattern = r"'backend' should be one of \['pickle', 'joblib'\], got 'invalid'\."
        with pytest.raises(ValueError, match=pattern):
            PickleDataSet(filepath="test.pkl", backend="invalid")

    def test_no_joblib(self, mocker):
        mocker.patch.object(PickleDataSet, "BACKENDS", {"joblib": None})
        with pytest.raises(ImportError):
            PickleDataSet(filepath="test.pkl", backend="joblib")


class TestPickleDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.pkl"
        ds = PickleDataSet(filepath=filepath)
        ds_versioned = PickleDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "PickleDataSet" in str(ds_versioned)
        assert "PickleDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        assert "backend" in str(ds_versioned)
        assert "backend" in str(ds)

    def test_save_and_load(self, versioned_pickle_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_pickle_data_set.save(dummy_dataframe)
        reloaded_df = versioned_pickle_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_pickle_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for PickleDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_pickle_data_set.load()

    def test_exists(self, versioned_pickle_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_pickle_data_set.exists()
        versioned_pickle_data_set.save(dummy_dataframe)
        assert versioned_pickle_data_set.exists()

    def test_prevent_overwrite(self, versioned_pickle_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding Pickle file for a given save version already exists."""
        versioned_pickle_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for PickleDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_pickle_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_pickle_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for PickleDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_pickle_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            PickleDataSet(
                filepath="https://example.com/file.pkl", version=Version(None, None)
            )
