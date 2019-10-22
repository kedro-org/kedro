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
from typing import Any

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.io import (
    AbstractDataSet,
    CSVLocalDataSet,
    CSVS3DataSet,
    DataCatalog,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    LambdaDataSet,
    MemoryDataSet,
    ParquetLocalDataSet,
)
from kedro.io.core import generate_timestamp
from kedro.versioning.journal import Journal


@pytest.fixture
def filepath(tmp_path):
    return str(tmp_path / "some" / "dir" / "test.csv")


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def sane_config(filepath):
    return {
        "catalog": {
            "boats": {"type": "CSVLocalDataSet", "filepath": filepath},
            "cars": {
                "type": "CSVS3DataSet",
                "filepath": "test_file.csv",
                "bucket_name": "test_bucket",
                "credentials": "s3_credentials",
            },
        },
        "credentials": {
            "s3_credentials": {
                "aws_access_key_id": "FAKE_ACCESS_KEY",
                "aws_secret_access_key": "FAKE_SECRET_KEY",
            }
        },
    }


@pytest.fixture
def data_set(filepath):
    return CSVLocalDataSet(filepath=filepath, save_args={"index": False})


@pytest.fixture
def multi_catalog(mocker):
    csv = CSVLocalDataSet(filepath="abc.csv")
    parq = ParquetLocalDataSet(filepath="xyz.parq")
    journal = mocker.Mock()
    return DataCatalog({"abc": csv, "xyz": parq}, journal=journal)


@pytest.fixture
def memory_catalog():
    ds1 = MemoryDataSet({"data": 42})
    ds2 = MemoryDataSet([1, 2, 3, 4, 5])
    return DataCatalog({"ds1": ds1, "ds2": ds2})


@pytest.fixture
def conflicting_feed_dict():
    ds1 = MemoryDataSet({"data": 0})
    return {"ds1": ds1, "ds3": 1}


class BadDataSet(AbstractDataSet):  # pragma: no cover
    def __init__(self, filepath):
        self.filepath = filepath
        raise Exception("Naughty!")

    def _load(self):
        return None

    def _save(self, data: Any):
        pass

    def _describe(self):
        return {}


@pytest.fixture
def bad_config(filepath):
    return {
        "bad": {"type": "tests.io.test_data_catalog.BadDataSet", "filepath": filepath}
    }


@pytest.fixture
def data_catalog(data_set):
    return DataCatalog(data_sets={"test": data_set})


@pytest.fixture
def data_catalog_from_config(sane_config):
    return DataCatalog.from_config(**sane_config)


class TestDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the data set"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, data_set, dummy_dataframe):
        """Test adding and then saving and reloading the data set"""
        catalog = DataCatalog(data_sets={})
        catalog.add("test", data_set)
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_all_save_and_load(self, data_set, dummy_dataframe):
        """Test adding all to the data catalog and then saving and reloading
        the data set"""
        catalog = DataCatalog(data_sets={})
        catalog.add_all({"test": data_set})
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a data set
        from nonexistent source"""
        pattern = r"Failed while loading data from data set CSVLocalDataSet"
        with pytest.raises(DataSetError, match=pattern):
            data_catalog.load("test")

    def test_add_data_set_twice(self, data_catalog, data_set):
        """Check the error when attempting to add the data set twice"""
        pattern = r"DataSet 'test' has already been registered"
        with pytest.raises(DataSetAlreadyExistsError, match=pattern):
            data_catalog.add("test", data_set)

    def test_load_from_unregistered(self):
        """Check the error when attempting to load unregistered data set"""
        catalog = DataCatalog(data_sets={})
        pattern = r"DataSet 'test' not found in the catalog"
        with pytest.raises(DataSetNotFoundError, match=pattern):
            catalog.load("test")

    def test_save_to_unregistered(self, dummy_dataframe):
        """Check the error when attempting to save to unregistered data set"""
        catalog = DataCatalog(data_sets={})
        pattern = r"DataSet 'test' not found in the catalog"
        with pytest.raises(DataSetNotFoundError, match=pattern):
            catalog.save("test", dummy_dataframe)

    def test_feed_dict(self, memory_catalog, conflicting_feed_dict):
        """Test feed dict overriding some of the data sets"""
        memory_catalog.add_feed_dict(conflicting_feed_dict, replace=True)
        assert "data" in memory_catalog.load("ds1")
        assert memory_catalog.load("ds1")["data"] == 0
        assert isinstance(memory_catalog.load("ds2"), list)
        assert memory_catalog.load("ds3") == 1

    def test_exists(self, data_catalog, dummy_dataframe):
        """Test `exists` method invocation"""
        assert not data_catalog.exists("test")
        data_catalog.save("test", dummy_dataframe)
        assert data_catalog.exists("test")

    def test_exists_not_implemented(self, caplog):
        """Test calling `exists` on the data set, which didn't implement it"""
        catalog = DataCatalog(data_sets={"test": LambdaDataSet(None, None)})
        result = catalog.exists("test")

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "`exists()` not implemented for `LambdaDataSet`. "
            "Assuming output does not exist." in log_record.message
        )
        assert result is False

    def test_exists_unregistered(self, data_catalog):
        """Check the the error when calling `exists`
        on unregistered data set"""
        pattern = r"DataSet \'wrong_key\' not found in the catalog"
        with pytest.raises(DataSetError, match=pattern):
            data_catalog.exists("wrong_key")

    def test_release_unregistered(self, data_catalog):
        """Check the the error when calling `release`
        on unregistered data set"""
        pattern = r"DataSet \'wrong_key\' not found in the catalog"
        with pytest.raises(DataSetError, match=pattern):
            data_catalog.release("wrong_key")

    def test_multi_catalog_list(self, multi_catalog):
        """Test data catalog which contains multiple data sets"""
        entries = multi_catalog.list()
        assert "abc" in entries
        assert "xyz" in entries

    def test_eq(self, multi_catalog, data_catalog):
        assert multi_catalog == multi_catalog  # pylint: disable=comparison-with-itself
        assert multi_catalog == multi_catalog.shallow_copy()
        assert multi_catalog != data_catalog

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.datasets.boats, CSVLocalDataSet)
        assert isinstance(data_catalog_from_config.datasets.cars, CSVS3DataSet)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config.add("new_dataset", CSVLocalDataSet("some_path"))
        assert isinstance(
            data_catalog_from_config.datasets.new_dataset, CSVLocalDataSet
        )
        assert isinstance(data_catalog_from_config.datasets.boats, CSVLocalDataSet)

    def test_adding_datasets_not_allowed(self, data_catalog_from_config):
        """Check error if user tries to update the datasets attribute"""
        pattern = r"Please use DataCatalog.add\(\) instead"
        with pytest.raises(AttributeError, match=pattern):
            data_catalog_from_config.datasets.new_dataset = None

    def test_mutating_datasets_not_allowed(self, data_catalog_from_config):
        """Check error if user tries to update the datasets attribute"""
        pattern = "Please change datasets through configuration."
        with pytest.raises(AttributeError, match=pattern):
            data_catalog_from_config.datasets.cars = None


class TestDataCatalogFromConfig:
    def test_from_sane_config(self, data_catalog_from_config, dummy_dataframe):
        """Test populating the data catalog from config"""
        data_catalog_from_config.save("boats", dummy_dataframe)
        reloaded_df = data_catalog_from_config.load("boats")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_config_missing_type(self, sane_config):
        """Check the error if type attribute is missing for some data set(s)
        in the config"""
        del sane_config["catalog"]["boats"]["type"]
        pattern = r"`type` is missing from DataSet \'boats\' " r"catalog configuration"
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_module(self, sane_config):
        """Check the error if the type points to nonexistent module"""
        sane_config["catalog"]["boats"][
            "type"
        ] = "kedro.invalid_module_name.io.CSVLocalDataSet"
        with pytest.raises(DataSetError, match=r"Cannot import module"):
            DataCatalog.from_config(**sane_config)

    def test_config_missing_class(self, sane_config):
        """Check the error if the type points to nonexistent class"""
        sane_config["catalog"]["boats"]["type"] = "kedro.io.CSVLocalDataSetInvalid"
        pattern = (
            r"Class `kedro.io.CSVLocalDataSetInvalid` for DataSet `boats` not found."
        )
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_data_set(self, sane_config):
        """Check the error if the type points to invalid class"""
        sane_config["catalog"]["boats"]["type"] = "DataCatalog"
        pattern = (
            r"DataSet 'boats' type `.*DataCatalog` is invalid: all "
            r"data set types must extend `AbstractDataSet`"
        )
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_arguments(self, sane_config):
        """Check the error if the data set config contains invalid arguments"""
        sane_config["catalog"]["boats"]["save_and_load_args"] = False
        pattern = (
            r"DataSet 'boats' must only contain arguments valid for "
            r"the constructor of `.*CSVLocalDataSet`"
        )
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_empty_config(self):
        """Test empty config"""
        assert DataCatalog.from_config(None)

    def test_missing_credentials(self, sane_config):
        """Check the error if credentials can't be located"""
        sane_config["catalog"]["cars"]["credentials"] = "missing"
        with pytest.raises(KeyError, match=r"Unable to find credentials"):
            DataCatalog.from_config(**sane_config)

    # pylint: disable=protected-access
    def test_link_credentials(self, data_catalog_from_config, sane_config):
        """Test credentials being linked to the relevant data set"""
        assert (
            data_catalog_from_config._data_sets["cars"]._credentials[
                "aws_access_key_id"
            ]
            == sane_config["credentials"]["s3_credentials"]["aws_access_key_id"]
        )

    def test_idempotent_catalog(self, sane_config):
        """Test that data catalog instantiations are idempotent"""
        _ = DataCatalog.from_config(**sane_config)  # NOQA
        catalog = DataCatalog.from_config(**sane_config)
        assert catalog

    def test_error_dataset_init(self, bad_config):
        """Check the error when trying to instantiate erroneous data set"""
        pattern = r"Failed to instantiate DataSet \'bad\' " r"of type `.*BadDataSet`"
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(bad_config, None)


class TestDataCatalogVersioned:
    def test_from_sane_config_versioned(self, sane_config, dummy_dataframe):
        """Test load and save of versioned data sets from config"""
        sane_config["catalog"]["boats"]["versioned"] = True
        version = generate_timestamp()
        journal = Journal({"run_id": "fake-id", "project_path": "fake-path"})
        catalog = DataCatalog.from_config(
            **sane_config,
            load_versions={"boats": version},
            save_version=version,
            journal=journal
        )

        assert catalog._journal == journal  # pylint: disable=protected-access

        catalog.save("boats", dummy_dataframe)
        path = Path(sane_config["catalog"]["boats"]["filepath"])
        path = path / version / path.name
        assert path.is_file()
        reloaded_df = catalog.load("boats")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    @pytest.mark.parametrize("versioned", [True, False])
    def test_from_sane_config_versioned_warn(self, caplog, sane_config, versioned):
        """Check the warning if `version` attribute was added
        to the data set config"""
        sane_config["catalog"]["boats"]["versioned"] = versioned
        sane_config["catalog"]["boats"]["version"] = True
        DataCatalog.from_config(**sane_config)
        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "`version` attribute removed from `boats` data set "
            "configuration since it is a reserved word and cannot be "
            "directly specified" in log_record.message
        )

    def test_from_sane_config_load_versions_warn(self, sane_config):
        sane_config["catalog"]["boats"]["versioned"] = True
        version = generate_timestamp()
        load_version = {"non-boart": version}
        pattern = r"\`load_versions\` keys \[non-boart\] are not found in the catalog\."
        with pytest.warns(UserWarning, match=pattern):
            DataCatalog.from_config(**sane_config, load_versions=load_version)
