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
from random import randint

import numpy as np
import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.io import DataSetError, ParquetLocalDataSet
from kedro.io.core import Version


def _generate_sample_pandas_df(
    randomised: bool = False, with_nan: bool = False
) -> pd.DataFrame:
    """
    Return a dummy data frame with 2-columns [Name, Age]

    Args:
        randomised: Set to true to randomise ages.
        with_nan: Include an entry with nan age value.

    Returns:
        Dataframe as specified by the arguments.

    """

    def age(default):
        return randint(1, 120) if randomised else default

    return pd.DataFrame(
        {
            "Name": ["Alex", "Bob", "Clarke", "Dave"],
            "Age": [age(31), age(12), age(65), np.nan if with_nan else age(29)],
        }
    )


@pytest.fixture(params=[(False, False)])
def input_data(request):
    randomised, with_nan = request.param
    return _generate_sample_pandas_df(randomised, with_nan)


@pytest.fixture
def data_path(tmp_path):
    return str(tmp_path / "data")


@pytest.fixture(params=[dict()])
def parquet_data_set(data_path, request):
    return ParquetLocalDataSet(filepath=data_path, **request.param)


@pytest.fixture
def versioned_parquet_data_set(data_path, load_version, save_version):
    return ParquetLocalDataSet(
        filepath=data_path, version=Version(load_version, save_version)
    )


class TestParquetLocalDataSet:
    _AGE_COLUMN = "Age"

    @pytest.mark.parametrize("input_data", [(False, False)], indirect=True)
    def test_save(self, parquet_data_set, input_data):
        """Test saving and overriding the data set."""
        parquet_data_set.save(input_data)

        # Check that it is loaded correctly
        loaded_data = parquet_data_set.load()
        assert_frame_equal(loaded_data, input_data)

        # Save on top of existing
        new_data = _generate_sample_pandas_df(randomised=True)
        parquet_data_set.save(new_data)

        # Assert data has been overwritten
        reloaded_data = parquet_data_set.load()
        assert_frame_equal(reloaded_data, new_data)

    @pytest.mark.parametrize("input_data", [(False, True)], indirect=True)
    @pytest.mark.parametrize(
        "parquet_data_set", [dict(load_args={"columns": [_AGE_COLUMN]})], indirect=True
    )
    def test_load_with_args(self, parquet_data_set, input_data):
        """Test loading the data set with extra load arguments specified."""
        parquet_data_set.save(input_data)
        loaded_data = parquet_data_set.load()
        assert_frame_equal(loaded_data, input_data[[self._AGE_COLUMN]])

    @pytest.mark.parametrize(
        "parquet_data_set", [dict(save_args={"compression": "GZIP"})], indirect=True
    )
    def test_save_with_args(self, parquet_data_set, input_data):
        """Test loading the data set with extra save arguments specified."""
        parquet_data_set.save(input_data)
        loaded_data = parquet_data_set.load()
        assert_frame_equal(loaded_data, input_data)

    def test_save_none(self, parquet_data_set):
        """Check the error when trying to save None."""
        pattern = r"Saving `None` to a `DataSet` is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            parquet_data_set.save(None)

    def test_str_representation(self):
        """Test string representation of the data set instance."""
        parquet_data_set = ParquetLocalDataSet("test_file.parquet")
        pattern = (
            "ParquetLocalDataSet(engine=auto, "
            "filepath=test_file.parquet, save_args={})"
        )
        assert pattern in str(parquet_data_set)

    def test_exists(self, parquet_data_set, input_data):
        """Test `exists` method invocation."""
        assert not parquet_data_set.exists()
        parquet_data_set.save(input_data)
        assert parquet_data_set.exists()


class TestParquetLocalDataSetVersioned:
    def test_save_and_load(self, versioned_parquet_data_set, input_data):
        """Test that saved and reloaded data matches the original one for
        the versioned data set."""
        versioned_parquet_data_set.save(input_data)
        reloaded_df = versioned_parquet_data_set.load()
        assert_frame_equal(reloaded_df, input_data)

    def test_no_versions(self, versioned_parquet_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for ParquetLocalDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.load()

    def test_exists(self, versioned_parquet_data_set, input_data):
        """Test `exists` method invocation for versioned data set."""
        assert not versioned_parquet_data_set.exists()

        versioned_parquet_data_set.save(input_data)
        assert versioned_parquet_data_set.exists()

    def test_prevent_overwrite(self, versioned_parquet_data_set, input_data):
        """Check the error when attempting to override the data set if the
        corresponding parquet file for a given save version already exists."""
        versioned_parquet_data_set.save(input_data)
        pattern = (
            r"Save path \`.+\` for ParquetLocalDataSet\(.+\) must "
            r"not exist if versioning is enabled\."
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_parquet_data_set.save(input_data)

    @pytest.mark.parametrize(
        "load_version", ["2019-01-01T23.59.59.999Z"], indirect=True
    )
    @pytest.mark.parametrize(
        "save_version", ["2019-01-02T00.00.00.000Z"], indirect=True
    )
    def test_save_version_warning(
        self, versioned_parquet_data_set, load_version, save_version, input_data
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        pattern = (
            r"Save version `{0}` did not match load version `{1}` "
            r"for ParquetLocalDataSet\(.+\)".format(save_version, load_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_parquet_data_set.save(input_data)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        filepath = "data"
        ds = ParquetLocalDataSet(filepath=filepath)
        ds_versioned = ParquetLocalDataSet(
            filepath=filepath, version=Version(load_version, save_version)
        )
        assert filepath in str(ds)
        assert "version" not in str(ds)

        assert filepath in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)
