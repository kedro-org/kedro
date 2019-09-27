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
from importlib import reload

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

import kedro
from kedro.io import PickleLocalDataSet
from kedro.io.core import DataSetError, Version


@pytest.fixture
def filepath_pkl(tmp_path):
    return str(tmp_path / "test.pkl")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=["pickle"])
def pickle_data_set(filepath_pkl, request):
    return PickleLocalDataSet(filepath=filepath_pkl, backend=request.param)


@pytest.fixture
def pickle_data_set_with_args(filepath_pkl):
    return PickleLocalDataSet(
        filepath=filepath_pkl,
        load_args={"fix_imports": False},
        save_args={"fix_imports": False},
    )


@pytest.fixture
def versioned_pickle_data_set(filepath_pkl, load_version, save_version):
    return PickleLocalDataSet(
        filepath=filepath_pkl, version=Version(load_version, save_version)
    )


class TestPickleLocalDataSet:
    @pytest.mark.parametrize("pickle_data_set", ["pickle", "joblib"], indirect=True)
    def test_save_and_load(self, pickle_data_set, dummy_dataframe):
        """Test saving and reloading the data using different backends."""
        pickle_data_set.save(dummy_dataframe)
        reloaded_df = pickle_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_str_representation(self):
        """Test string representation of the data set instance."""
        data_set = PickleLocalDataSet(filepath="test.pkl", backend="pickle")
        pattern = "PickleLocalDataSet(backend=pickle, filepath=test.pkl)"
        assert pattern in str(data_set)

    def test_bad_backend(self):
        """Check the error when trying to instantiate with invalid backend."""
        pattern = (
            r"backend should be one of \[\'pickle\'\, \'joblib\'\]\, "
            r"got wrong\-backend"
        )
        with pytest.raises(ValueError, match=pattern):
            PickleLocalDataSet(filepath="test.pkl", backend="wrong-backend")

    def test_exists(self, pickle_data_set, dummy_dataframe):
        """Test `exists()` method invocation."""
        assert not pickle_data_set.exists()

        pickle_data_set.save(dummy_dataframe)
        assert pickle_data_set.exists()

    def test_joblib_not_installed(self, filepath_pkl, mocker):
        """Check the error if 'joblib' module is not installed."""
        mocker.patch.dict("sys.modules", joblib=None)
        reload(kedro.io.pickle_local)
        # creating a pickle-based data set should be fine
        PickleLocalDataSet(filepath=filepath_pkl, backend="pickle")

        # creating a joblib-based data set should fail
        pattern = (
            r"selected backend \'joblib\' could not be imported\. "
            r"Make sure it is installed\."
        )
        with pytest.raises(ImportError, match=pattern):
            PickleLocalDataSet(filepath=filepath_pkl, backend="joblib")

    def test_save_and_load_args(self, pickle_data_set_with_args, dummy_dataframe):
        """Test saving and reloading the data with different options."""
        pickle_data_set_with_args.save(dummy_dataframe)
        reloaded_df = pickle_data_set_with_args.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)


class TestPickleLocalDataSetVersioned:
    def test_save_and_load(self, versioned_pickle_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_pickle_data_set.save(dummy_dataframe)
        reloaded_df = versioned_pickle_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_pickle_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for PickleLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_pickle_data_set.load()

    def test_exists(self, versioned_pickle_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_pickle_data_set.exists()

        versioned_pickle_data_set.save(dummy_dataframe)
        assert versioned_pickle_data_set.exists()

    def test_prevent_override(self, versioned_pickle_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding pickle file for a given save version already exists."""
        versioned_pickle_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for PickleLocalDataSet\(.+\) must "
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
            r"Save path `.*/{}/test\.pkl` did not match load path "
            r"`.*/{}/test\.pkl` for PickleLocalDataSet\(.+\)".format(
                save_version, load_version
            )
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_pickle_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.pkl"
        ds = PickleLocalDataSet(filepath=filepath)
        ds_versioned = PickleLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
