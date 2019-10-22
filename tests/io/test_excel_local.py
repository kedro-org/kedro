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

from kedro.io import DataSetError, ExcelLocalDataSet
from kedro.io.core import Version


@pytest.fixture
def filepath_xls(tmp_path):
    return str(tmp_path / "test.xlsx")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=[dict()])
def xls_data_set(filepath_xls, request):
    return ExcelLocalDataSet(filepath=filepath_xls, **request.param)


@pytest.fixture
def versioned_xls_data_set(filepath_xls, load_version, save_version):
    return ExcelLocalDataSet(
        filepath=filepath_xls, version=Version(load_version, save_version)
    )


class TestExcelLocalDataSet:
    @pytest.mark.parametrize(
        "xls_data_set",
        [dict(load_args={"sheet_name": "Sheet1"}, save_args={"na_rep": "N/A"})],
        indirect=True,
    )
    def test_save_and_load(self, xls_data_set, dummy_dataframe):
        """Test saving and reloading the data set."""
        xls_data_set.save(dummy_dataframe)
        reloaded_df = xls_data_set.load()

        assert dummy_dataframe.equals(reloaded_df)

    @pytest.mark.parametrize(
        "xls_data_set",
        [
            dict(
                save_args={
                    "na_rep": "N/A",
                    "writer": {
                        "date_format": "YYYY-MM-DD",
                        "datetime_format": "YYYY-MM-DD HH:MM:SS",
                    },
                }
            )
        ],
        indirect=True,
    )
    def test_save_custom_writer(
        self, xls_data_set, dummy_dataframe, filepath_xls, mocker
    ):
        """Check that save options are passed down to the ExcelWriter"""
        mock_writer = mocker.patch("pandas.ExcelWriter")
        mocker.patch("pandas.DataFrame.to_excel")
        save_args_before = xls_data_set._save_args

        xls_data_set.save(dummy_dataframe)
        save_args_after = xls_data_set._save_args

        mock_writer.assert_called_once_with(
            filepath_xls,
            engine="xlsxwriter",
            date_format="YYYY-MM-DD",
            datetime_format="YYYY-MM-DD HH:MM:SS",
        )
        assert save_args_before == save_args_after  # ensure save_args were not mutated

    @pytest.mark.parametrize(
        "xls_data_set",
        [
            dict(
                engine="xlsxwriter",
                save_args={
                    "na_rep": "N/A",
                    "writer": {"mode": "a", "engine": "openpyxl"},
                },
            )
        ],
        indirect=True,
    )
    def test_save_custom_writer_overwrite_engine(
        self, xls_data_set, dummy_dataframe, filepath_xls, mocker
    ):
        """Check that engine defined under writer save_args takes precedence
        over the one defined on the class."""
        mock_writer = mocker.patch("pandas.ExcelWriter")
        mocker.patch("pandas.DataFrame.to_excel")

        xls_data_set.save(dummy_dataframe)

        mock_writer.assert_called_once_with(filepath_xls, engine="openpyxl", mode="a")

    @pytest.mark.parametrize(
        "xls_data_set", [dict(load_args={"sheet_name": "Sheet1"})], indirect=True
    )
    def test_load_missing_xls_file(self, xls_data_set):
        """Check the error raised when trying to load nonexistent xlsx file."""
        pattern = r"Failed while loading data from data set ExcelLocalDataSet"
        with pytest.raises(DataSetError, match=pattern):
            xls_data_set.load()

    def test_exists(self, xls_data_set, dummy_dataframe):
        """Test `exists` method invocation."""
        assert not xls_data_set.exists()

        xls_data_set.save(dummy_dataframe)
        assert xls_data_set.exists()


class TestExcelLocalDataSetVersioned:
    def test_save_and_load(self, versioned_xls_data_set, dummy_dataframe):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_xls_data_set.save(dummy_dataframe)
        reloaded_df = versioned_xls_data_set.load()
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_no_versions(self, versioned_xls_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ExcelLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_xls_data_set.load()

    def test_exists(self, versioned_xls_data_set, dummy_dataframe):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_xls_data_set.exists()

        versioned_xls_data_set.save(dummy_dataframe)
        assert versioned_xls_data_set.exists()

    def test_prevent_override(self, versioned_xls_data_set, dummy_dataframe):
        """Check the error when attempting to override the data set if the
        corresponding xls file for a given save version already exists."""
        versioned_xls_data_set.save(dummy_dataframe)
        pattern = (
            r"Save path \`.+\` for ExcelLocalDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_xls_data_set.save(dummy_dataframe)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_xls_data_set, load_version, save_version, dummy_dataframe
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for ExcelLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_xls_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "test.xlsx"
        ds = ExcelLocalDataSet(filepath=filepath)
        ds_versioned = ExcelLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
