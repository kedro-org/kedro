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

# pylint: disable=unused-argument
import numpy as np
import pandas as pd
import pytest

from kedro.io import DataSetError, MemoryDataSet


def _update_data(data, idx, jdx, value):
    if isinstance(data, pd.DataFrame):
        data.iloc[idx, jdx] = value
        return data
    if isinstance(data, np.ndarray):
        data[idx, jdx] = value
        return data
    return data  # pragma: no cover


def _check_equals(data1, data2):
    if isinstance(data1, pd.DataFrame) and isinstance(data2, pd.DataFrame):
        return data1.equals(data2)
    if isinstance(data1, np.ndarray) and isinstance(data2, np.ndarray):
        return np.array_equal(data1, data2)
    return False  # pragma: no cover


@pytest.fixture
def dummy_numpy_array():
    return np.array([[1, 4, 5], [2, 5, 6]])


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=["dummy_dataframe", "dummy_numpy_array"])
def input_data(request):
    return request.getfixturevalue(request.param)


@pytest.fixture
def new_data():
    return pd.DataFrame({"col1": ["a", "b"], "col2": ["c", "d"], "col3": ["e", "f"]})


@pytest.fixture
def memory_data_set(input_data):
    return MemoryDataSet(data=input_data)


class TestMemoryDataSet:
    def test_load(self, memory_data_set, input_data):
        """Test basic load"""
        loaded_data = memory_data_set.load()
        assert _check_equals(loaded_data, input_data)

    def test_save(self, memory_data_set, input_data, new_data):
        """Test overriding the data set"""
        memory_data_set.save(data=new_data)
        reloaded = memory_data_set.load()
        assert not _check_equals(reloaded, input_data)
        assert _check_equals(reloaded, new_data)

    def test_load_modify_original_data(self, memory_data_set, input_data):
        """Check that the data set object is not updated when the original
        object is changed."""
        input_data = _update_data(input_data, 1, 1, -5)
        assert not _check_equals(memory_data_set.load(), input_data)

    def test_save_modify_original_data(self, memory_data_set, new_data):
        """Check that the data set object is not updated when the original
        object is changed."""
        memory_data_set.save(new_data)
        new_data = _update_data(new_data, 1, 1, "new value")

        assert not _check_equals(memory_data_set.load(), new_data)

    @pytest.mark.parametrize(
        "input_data", ["dummy_dataframe", "dummy_numpy_array"], indirect=True
    )
    def test_load_returns_new_object(self, memory_data_set, input_data):
        """Test that consecutive loads point to different objects in case of a
        pandas DataFrame and numpy array"""
        loaded_data = memory_data_set.load()
        reloaded_data = memory_data_set.load()
        assert _check_equals(loaded_data, input_data)
        assert _check_equals(reloaded_data, input_data)
        assert loaded_data is not reloaded_data

    def test_create_without_data(self):
        """Test instantiation without data"""
        assert MemoryDataSet() is not None

    def test_loading_none(self):
        """Check the error when attempting to load the data set that doesn't
        contain any data"""
        pattern = r"Data for MemoryDataSet has not been saved yet\."
        with pytest.raises(DataSetError, match=pattern):
            MemoryDataSet().load()

    def test_saving_none(self):
        """Check the error when attempting to save the data set without
        providing the data"""
        pattern = r"Saving `None` to a `DataSet` is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            MemoryDataSet().save(None)

    @pytest.mark.parametrize(
        "input_data,expected",
        [
            ("dummy_dataframe", "MemoryDataSet(data=<DataFrame>)"),
            ("dummy_numpy_array", "MemoryDataSet(data=<ndarray>)"),
        ],
        indirect=["input_data"],
    )
    def test_str_representation(self, memory_data_set, input_data, expected):
        """Test string representation of the data set"""
        assert expected in str(memory_data_set)

    def test_exists(self, new_data):
        """Test `exists` method invocation"""
        data_set = MemoryDataSet()
        assert not data_set.exists()

        data_set.save(new_data)
        assert data_set.exists()
