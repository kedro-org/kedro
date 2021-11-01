import pandas as pd
import pytest

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io import DataCatalog, DataCatalogWithDefault, MemoryDataSet


@pytest.fixture
def filepath(tmp_path):
    return str(tmp_path / "some" / "dir" / "test.csv")


@pytest.fixture
def data_set(filepath):
    return CSVDataSet(filepath=filepath, save_args={"index": False})


def default_csv(name):
    return CSVDataSet(name)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def sane_config(filepath):
    return {
        "catalog": {
            "boats": {
                "type": "kedro.extras.datasets.pandas.CSVDataSet",
                "filepath": filepath,
            },
            "cars": {
                "type": "kedro.extras.datasets.pandas.CSVDataSet",
                "filepath": "s3://test_bucket/test_file.csv",
                "credentials": "s3_credentials",
            },
        },
        "credentials": {
            "s3_credentials": {"key": "FAKE_ACCESS_KEY", "secret": "FAKE_SECRET_KEY"}
        },
    }


def test_load_from_unregistered(dummy_dataframe, tmpdir):
    catalog = DataCatalogWithDefault(data_sets={}, default=default_csv)

    path = str(tmpdir.mkdir("sub").join("test.csv"))
    catalog.save(path, dummy_dataframe)
    reloaded_df = catalog.load(path)

    assert dummy_dataframe.equals(reloaded_df)


def test_save_and_load_catalog(data_set, dummy_dataframe, tmpdir):
    catalog = DataCatalogWithDefault(data_sets={"test": data_set}, default=default_csv)

    path = str(tmpdir.mkdir("sub").join("test"))
    catalog.save(path, dummy_dataframe)
    reloaded_df = catalog.load(path)
    assert dummy_dataframe.equals(reloaded_df)


def test_from_sane_config(sane_config):
    with pytest.raises(
        ValueError, match="Cannot instantiate a `DataCatalogWithDefault`"
    ):
        DataCatalogWithDefault.from_config(
            sane_config["catalog"], sane_config["credentials"]
        )


def test_from_sane_config_default(sane_config, dummy_dataframe, tmpdir):
    catalog = DataCatalog.from_config(
        sane_config["catalog"], sane_config["credentials"]
    )
    catalog_with_default = DataCatalogWithDefault.from_data_catalog(
        catalog, default_csv
    )
    path = str(tmpdir.mkdir("sub").join("missing.csv"))
    catalog_with_default.save(path, dummy_dataframe)
    reloaded_df = catalog_with_default.load(path)
    assert dummy_dataframe.equals(reloaded_df)


def test_default_none():
    with pytest.raises(
        TypeError,
        match="Default must be a callable with a "
        "single input string argument: the "
        "key of the requested data set.",
    ):
        DataCatalogWithDefault(data_sets={}, default=None)


# pylint: disable=unused-argument
def default_memory(name):
    return MemoryDataSet(5)


def test_remember_load():
    catalog = DataCatalogWithDefault(
        data_sets={}, default=default_memory, remember=True
    )
    assert catalog.load("any") == 5
    assert "any" in catalog.list()


def test_remember_save(tmpdir, dummy_dataframe):
    catalog = DataCatalogWithDefault(data_sets={}, default=default_csv, remember=True)

    path = str(tmpdir.mkdir("sub").join("test.csv"))
    catalog.save(path, dummy_dataframe)
    assert tmpdir.join("sub").join("test.csv") in catalog.list()
