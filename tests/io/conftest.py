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


@pytest.fixture
def correct_config(filepath):
    return {
        "catalog": {
            "boats": {"type": "pandas.CSVDataset", "filepath": filepath},
            "cars": {
                "type": "pandas.CSVDataset",
                "filepath": "s3://test_bucket/test_file.csv",
                "credentials": "s3_credentials",
            },
        },
        "credentials": {
            "s3_credentials": {"key": "FAKE_ACCESS_KEY", "secret": "FAKE_SECRET_KEY"}
        },
    }


@pytest.fixture
def correct_config_versioned(filepath):
    return {
        "catalog": {
            "boats": {
                "type": "pandas.CSVDataset",
                "filepath": filepath,
                "versioned": True,
            },
            "cars": {
                "type": "pandas.CSVDataset",
                "filepath": "s3://test_bucket/test_file.csv",
                "credentials": "cars_credentials",
            },
        },
        "credentials": {
            "cars_credentials": {"key": "FAKE_ACCESS_KEY", "secret": "FAKE_SECRET_KEY"}
        },
    }


@pytest.fixture
def correct_config_with_nested_creds(correct_config):
    correct_config["catalog"]["cars"]["credentials"] = {
        "client_kwargs": {"credentials": "other_credentials"},
        "key": "secret",
    }
    correct_config["credentials"]["other_credentials"] = {
        "client_kwargs": {
            "aws_access_key_id": "OTHER_FAKE_ACCESS_KEY",
            "aws_secret_access_key": "OTHER_FAKE_SECRET_KEY",
        }
    }
    return correct_config


@pytest.fixture
def bad_config(filepath):
    return {
        "bad": {"type": "tests.io.test_data_catalog.BadDataset", "filepath": filepath}
    }


@pytest.fixture
def correct_config_with_tracking_ds(tmp_path):
    boat_path = (tmp_path / "some" / "dir" / "test.csv").as_posix()
    plane_path = (tmp_path / "some" / "dir" / "metrics.json").as_posix()
    return {
        "catalog": {
            "boats": {
                "type": "pandas.CSVDataset",
                "filepath": boat_path,
                "versioned": True,
            },
            "planes": {"type": "tracking.MetricsDataset", "filepath": plane_path},
        },
    }
