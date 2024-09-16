import numpy as np
import pandas as pd
import pytest
from kedro_datasets.pandas import CSVDataset


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
def filepath(tmp_path):
    return (tmp_path / "some" / "dir" / "test.csv").as_posix()


@pytest.fixture
def dataset(filepath):
    return CSVDataset(filepath=filepath, save_args={"index": False})
