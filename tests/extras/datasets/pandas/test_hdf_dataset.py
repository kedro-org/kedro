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

import pandas as pd
import pytest
from fsspec.implementations.http import HTTPFileSystem
from fsspec.implementations.local import LocalFileSystem
from gcsfs import GCSFileSystem
from pandas.testing import assert_frame_equal
from s3fs.core import S3FileSystem

from kedro.extras.datasets.pandas import HDFDataSet
from kedro.io import DataSetError
from kedro.io.core import PROTOCOL_DELIMITER, Version

HDF_KEY = "data"


@pytest.fixture
def filepath_hdf(tmp_path):
    return str(tmp_path / "test.h5")


@pytest.fixture
def hdf_data_set(filepath_hdf, load_args, save_args, mocker, fs_args):
    HDFDataSet._lock = mocker.MagicMock()
    return HDFDataSet(
        filepath=filepath_hdf,
        key=HDF_KEY,
        load_args=load_args,
        save_args=save_args,
        fs_args=fs_args,
    )


@pytest.fixture
def versioned_hdf_data_set(filepath_hdf, load_version, save_version):
    return HDFDataSet(
        filepath=filepath_hdf, key=HDF_KEY, version=Version(load_version, save_version)
    )


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestHDFDataSet:
    def test_save_and_load(self, hdf_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        hdf_data_set.save(dummy_dataframe)
        reloaded = hdf_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded)
        assert hdf_data_set._fs_open_args_load == {}
        assert hdf_data_set._fs_open_args_save == {"mode": "wb"}

    def test_exists(self, hdf_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not hdf_data_set.exists()
        hdf_data_set.save(dummy_dataframe)
        assert hdf_data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, hdf_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert hdf_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, hdf_data_set, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert hdf_data_set._save_args[key] == value

    @pytest.mark.parametrize(
        "fs_args",
        [{"open_args_load": {"mode": "rb", "compression": "gzip"}}],
        indirect=True,
    )
    def test_open_extra_args(self, hdf_data_set, fs_args):
        assert hdf_data_set._fs_open_args_load == fs_args["open_args_load"]
        assert hdf_data_set._fs_open_args_save == {"mode": "wb"}  # default unchanged

    def test_load_missing_file(self, hdf_data_set):
        """Check the error when trying to load missing file."""
        pattern = r"Failed while loading data from data set HDFDataSet\(.*\)"
        with pytest.raises(DataSetError, match=pattern):
            hdf_data_set.load()

    @pytest.mark.parametrize(
        "filepath,instance_type",
        [
            ("s3://bucket/file.h5", S3FileSystem),
            ("file:///tmp/test.h5", LocalFileSystem),
            ("/tmp/test.h5", LocalFileSystem),
            ("gcs://bucket/file.h5", GCSFileSystem),
            ("https://example.com/file.h5", HTTPFileSystem),
        ],
    )
    def test_protocol_usage(self, filepath, instance_type):
        data_set = HDFDataSet(filepath=filepath, key=HDF_KEY)
        assert isinstance(data_set._fs, instance_type)

        path = filepath.split(PROTOCOL_DELIMITER, 1)[-1]

        assert str(data_set._filepath) == path
        assert isinstance(data_set._filepath, PurePosixPath)

    def test_catalog_release(self, mocker):
        fs_mock = mocker.patch("fsspec.filesystem").return_value
        filepath = "test.h5"
        data_set = HDFDataSet(filepath=filepath, key=HDF_KEY)
        data_set.release()
        fs_mock.invalidate_cache.assert_called_once_with(filepath)

    def test_save_and_load_df_with_categorical_variables(self, hdf_data_set):
        """Test saving and reloading the data set with categorical variables."""
        df = pd.DataFrame(
            {"A": [1, 2, 3], "B": pd.Series(list("aab")).astype("category")}
        )
        hdf_data_set.save(df)
        reloaded = hdf_data_set.load()
        assert_frame_equal(df, reloaded)

    def test_thread_lock_usage(self, hdf_data_set, dummy_dataframe, mocker):
        """Test thread lock usage. """
        # pylint: disable=no-member
        mocked_lock = HDFDataSet._lock
        mocked_lock.assert_not_called()

        hdf_data_set.save(dummy_dataframe)
        calls = [mocker.call.__enter__(), mocker.call.__exit__(None, None, None)]
        mocked_lock.assert_has_calls(calls)

        mocked_lock.reset_mock()
        hdf_data_set.load()
        mocked_lock.assert_has_calls(calls)


class TestHDFDataSetVersioned:
    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.h5"
        ds = HDFDataSet(filepath=filepath, key=HDF_KEY)
        ds_versioned = HDFDataSet(
            filepath=filepath, key=HDF_KEY, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
        assert "HDFDataSet" in str(ds_versioned)
        assert "HDFDataSet" in str(ds)
        assert "protocol" in str(ds_versioned)
        assert "protocol" in str(ds)
        assert "key" in str(ds_versioned)
        assert "key" in str(ds)

    def test_save_and_load(self, versioned_hdf_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_hdf_data_set.save(dummy_dataframe)
        reloaded_df = versioned_hdf_data_set.load()
        assert_frame_equal(dummy_dataframe, reloaded_df)

    def test_no_versions(self, versioned_hdf_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for HDFDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdf_data_set.load()

    def test_exists(self, versioned_hdf_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_hdf_data_set.exists()
        versioned_hdf_data_set.save(dummy_dataframe)
        assert versioned_hdf_data_set.exists()

    def test_prevent_overwrite(self, versioned_hdf_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding hdf file for a given save version already exists."""
        versioned_hdf_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for HDFDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_hdf_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_hdf_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for HDFDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_hdf_data_set.save(dummy_dataframe)

    def test_http_filesystem_no_versioning(self):
        pattern = r"HTTP\(s\) DataSet doesn't support versioning\."

        with pytest.raises(DataSetError, match=pattern):
            HDFDataSet(
                filepath="https://example.com/file.h5",
                key=HDF_KEY,
                version=Version(None, None),
            )
