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
from pathlib import Path

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.contrib.io.feather import FeatherLocalDataSet
from kedro.io import DataSetError
from kedro.io.core import Version, generate_timestamp


@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()


@pytest.fixture()
def filepath(tmp_path):
    return str(tmp_path / "some" / "dir" / "test.feather")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def feather_data_set(filepath):
    return FeatherLocalDataSet(filepath=filepath)


@pytest.fixture
def versioned_feather_data_set(filepath, load_version, save_version):
    return FeatherLocalDataSet(
        filepath=filepath, version=Version(load_version, save_version)
    )


class TestFeatherLocalDataSet:
    def test_save_and_load(self, feather_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one."""
        feather_data_set.save(dummy_dataframe)
        reloaded_df = feather_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_missing_file(self, feather_data_set):
        """Check the error while trying to load from missing source."""
        pattern = r"Failed while loading data from data set FeatherLocalDataSet"
        with pytest.raises(DataSetError, match=pattern):
            feather_data_set.load()

    def test_exists(self, feather_data_set, dummy_dataframe):
        """Test `exists` method invocation for both cases."""
        assert not feather_data_set.exists()
        feather_data_set.save(dummy_dataframe)
        assert feather_data_set.exists()


class TestFeatherLocalDataSetVersioned:
    def test_save_and_load(
        self, versioned_feather_data_set, dummy_dataframe, filepath, save_version
    ):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_feather_data_set.save(dummy_dataframe)
        path = Path(filepath)
        assert (path / save_version / path.name).is_file()
        reloaded_df = versioned_feather_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_feather_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for FeatherLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_feather_data_set.load()

    def test_exists(self, versioned_feather_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_feather_data_set.exists()

        versioned_feather_data_set.save(dummy_dataframe)
        assert versioned_feather_data_set.exists()

    def test_prevent_override(self, versioned_feather_data_set, dummy_dataframe):
        """Check the error when attempt to override the same data set
        version."""
        versioned_feather_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for FeatherLocalDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_feather_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_feather_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for FeatherLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_feather_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.feather"
        ds = FeatherLocalDataSet(filepath=filepath)
        ds_versioned = FeatherLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
