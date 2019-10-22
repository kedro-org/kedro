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
from re import escape

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.io import CSVLocalDataSet, DataSetError
from kedro.io.core import Version


@pytest.fixture()
def filepath(tmp_path):
    return str(tmp_path / "some" / "dir" / "test.csv")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=[{"sep": ","}])
def csv_data_set(filepath, request):
    return CSVLocalDataSet(filepath=filepath, save_args=request.param)


@pytest.fixture
def versioned_csv_data_set(filepath, load_version, save_version):
    return CSVLocalDataSet(
        filepath=filepath,
        save_args={"sep": ","},
        version=Version(load_version, save_version),
    )


class TestCSVLocalDataSet:
    def test_save_and_load(self, csv_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one."""
        csv_data_set.save(dummy_dataframe)
        reloaded_df = csv_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.parametrize("csv_data_set", [{"index": False}], indirect=True)
    def test_load_missing_file(self, csv_data_set):
        """Check the error while trying to load from missing source."""
        pattern = r"Failed while loading data from data set CSVLocalDataSet"
        with pytest.raises(DataSetError, match=pattern):
            csv_data_set.load()

    def test_exists(self, csv_data_set, dummy_dataframe):
        """Test `exists` method invocation for both cases."""
        assert not csv_data_set.exists()
        csv_data_set.save(dummy_dataframe)
        assert csv_data_set.exists()

    @pytest.mark.parametrize(
        "path", ["http://abc.com", "https://abc.com/def?ghi=jkl#mnop", "blahblah://abc"]
    )
    def test_fails_with_remote_path(self, path):
        pattern = "seems to be a remote file"
        with pytest.raises(ValueError, match=pattern):
            CSVLocalDataSet(filepath=path, save_args={"sep": ","})


class TestCSVLocalDataSetVersioned:
    def test_save_and_load(
        self, versioned_csv_data_set, dummy_dataframe, filepath, save_version
    ):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_csv_data_set.save(dummy_dataframe)
        path = Path(filepath)
        assert (path / save_version / path.name).is_file()
        reloaded_df = versioned_csv_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_csv_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for CSVLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_csv_data_set.load()

    def test_exists(self, versioned_csv_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_csv_data_set.exists()

        versioned_csv_data_set.save(dummy_dataframe)
        assert versioned_csv_data_set.exists()

    def test_prevent_override(self, versioned_csv_data_set, dummy_dataframe):
        """Check the error when attempt to override the same data set
        version."""
        versioned_csv_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for CSVLocalDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_csv_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_csv_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for CSVLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_csv_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.csv"
        ds = CSVLocalDataSet(filepath=filepath)
        ds_versioned = CSVLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)

    def test_sequential_save_and_load(self, dummy_dataframe, filepath):
        """Tests if the correct load version is logged when two datasets are saved
        sequentially."""

        dataset1 = CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, "2000-01-01"),
        )

        dataset2 = CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, "2001-01-01"),
        )

        dataset1.save(dummy_dataframe)
        last_save_version1 = dataset1.get_last_save_version()

        dataset2.save(dummy_dataframe)
        last_save_version2 = dataset2.get_last_save_version()

        dataset2.load()
        last_load_version = dataset2.get_last_load_version()
        assert last_save_version2 == last_load_version
        assert last_save_version1 != last_save_version2

    def test_sequential_load_from_disk(
        self, dummy_dataframe, filepath, versioned_csv_data_set
    ):
        """Tests if the correct load version is logged when two versions are saved in
        disk."""
        save_version_1 = "2019-01-01T23.00.00.000Z"
        save_version_2 = "2019-01-01T23.59.59.999Z"
        CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, save_version_1),
        ).save(dummy_dataframe)
        CSVLocalDataSet(
            filepath=filepath,
            save_args={"sep": ","},
            version=Version(None, save_version_2),
        ).save(dummy_dataframe)

        versioned_csv_data_set.load()
        last_load_version = versioned_csv_data_set.get_last_load_version()

        assert last_load_version == save_version_2

    @pytest.mark.parametrize(
        "load_version, save_version",
        [("2019-01-01T23.59.59.999Z", "2019-01-01T23.59.59.999Z")],
        indirect=True,
    )
    def test_save_and_load_with_version(
        self, dummy_dataframe, load_version, save_version, versioned_csv_data_set
    ):
        """Tests if the correct load and save versions are logged when specified."""
        versioned_csv_data_set.save(dummy_dataframe)
        last_save_version = versioned_csv_data_set.get_last_save_version()
        versioned_csv_data_set.load()
        last_load_version = versioned_csv_data_set.get_last_load_version()
        assert load_version == last_load_version
        assert save_version == last_save_version

    def test_save_versioned_after_unversioned(
        self, csv_data_set, versioned_csv_data_set, dummy_dataframe
    ):
        """
        Check the error when saving versioned dataset if unversioned path already exists
        """
        csv_data_set.save(dummy_dataframe)

        assert versioned_csv_data_set.exists() is False

        pattern = (
            r"Save path \`.+\` for CSVLocalDataSet\(.+\) must not "
            r"exist if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_csv_data_set.save(dummy_dataframe)

    def test_save_unversioned_after_versioned(
        self, csv_data_set, versioned_csv_data_set, dummy_dataframe, filepath
    ):
        """
        Check the error when saving unversioned dataset if versioned path already exists
        """
        versioned_csv_data_set.save(dummy_dataframe)

        assert csv_data_set.exists() is False

        pattern = "Is a directory: '{}'".format(filepath)
        with pytest.raises(DataSetError, match=escape(pattern)):
            csv_data_set.save(dummy_dataframe)
