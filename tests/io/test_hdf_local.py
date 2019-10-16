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
import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.io import DataSetError, HDFLocalDataSet
from kedro.io.core import Version


@pytest.fixture
def filepath_hdf(tmp_path):
    return str(tmp_path / "test.hdf")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def hdf_data_set(filepath_hdf):
    return HDFLocalDataSet(filepath=filepath_hdf, key="test_hdf")


@pytest.fixture
def hdf_data_set_with_args(filepath_hdf):
    return HDFLocalDataSet(
        filepath=filepath_hdf,
        key="test_hdf",
        load_args={"errors": "ignore"},
        save_args={"errors": "ignore"},
    )


@pytest.fixture
def versioned_hdf_data_set(filepath_hdf, load_version, save_version):
    return HDFLocalDataSet(
        filepath=filepath_hdf,
        key="test_hdf",
        version=Version(load_version, save_version),
    )


class TestHDFLocalDataSet:
    def test_save_and_load(self, hdf_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        hdf_data_set.save(dummy_dataframe)
        reloaded_df = hdf_data_set.load()

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_missing(self, hdf_data_set):
        """Check the error when trying to load missing hdf file."""
        pattern = r"Failed while loading data from data set HDFLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            hdf_data_set.load()

    def test_exists(self, hdf_data_set, filepath_hdf, dummy_dataframe):
        """Test `exists` method invocation."""
        # file does not exist
        assert not hdf_data_set.exists()

        # file and key exist
        hdf_data_set.save(dummy_dataframe)
        assert hdf_data_set.exists()

        # file exists but the key does not
        data_set2 = HDFLocalDataSet(filepath=filepath_hdf, key="test_hdf_different_key")
        assert not data_set2.exists()

    def test_overwrite_if_exists(self, hdf_data_set, dummy_dataframe):
        """Test overriding existing hdf file."""
        hdf_data_set.save(dummy_dataframe)
        assert hdf_data_set.exists()

        hdf_data_set.save(dummy_dataframe.T)
        reloaded_df = hdf_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe.T)

    def test_save_and_load_args(self, hdf_data_set_with_args, dummy_dataframe):
        """Test saving and reloading the data set."""
        hdf_data_set_with_args.save(dummy_dataframe)
        reloaded_df = hdf_data_set_with_args.load()

        assert_frame_equal(reloaded_df, dummy_dataframe)


class TestHDFLocalDataSetVersioned:
    def test_save_and_load(self, versioned_hdf_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_hdf_data_set.save(dummy_dataframe)
        reloaded_df = versioned_hdf_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_hdf_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for HDFLocalDataSet\(.+\)"
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
            r"Save path \`.+\` for HDFLocalDataSet\(.+\) must "
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
            r"for HDFLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_hdf_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.hdf"
        ds = HDFLocalDataSet(filepath=filepath, key="test_hdf")
        ds_versioned = HDFLocalDataSet(
            filepath=filepath,
            key="test_hdf",
            version=Version(load_version, save_version),
        )

        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
