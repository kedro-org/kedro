import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.extras.datasets.pandas import CSVDataSet, ParquetDataSet
from kedro.io import (
    AbstractDataSet,
    DataCatalog,
    DataSetAlreadyExistsError,
    DataSetError,
    DataSetNotFoundError,
    LambdaDataSet,
    MemoryDataSet,
)
from kedro.io.core import VERSION_FORMAT, generate_timestamp


@pytest.fixture
def filepath(tmp_path):
    return (tmp_path / "some" / "dir" / "test.csv").as_posix()


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def sane_config(filepath):
    return {
        "catalog": {
            "boats": {"type": "pandas.CSVDataSet", "filepath": filepath},
            "cars": {
                "type": "pandas.CSVDataSet",
                "filepath": "s3://test_bucket/test_file.csv",
                "credentials": "s3_credentials",
                "layer": "raw",
            },
        },
        "credentials": {
            "s3_credentials": {"key": "FAKE_ACCESS_KEY", "secret": "FAKE_SECRET_KEY"}
        },
    }


@pytest.fixture
def sane_config_with_nested_creds(sane_config):
    sane_config["catalog"]["cars"]["credentials"] = {
        "client_kwargs": {"credentials": "other_credentials"},
        "key": "secret",
    }
    sane_config["credentials"]["other_credentials"] = {
        "client_kwargs": {
            "aws_access_key_id": "OTHER_FAKE_ACCESS_KEY",
            "aws_secret_access_key": "OTHER_FAKE_SECRET_KEY",
        }
    }
    return sane_config


@pytest.fixture
def sane_config_with_tracking_ds(tmp_path):
    boat_path = (tmp_path / "some" / "dir" / "test.csv").as_posix()
    plane_path = (tmp_path / "some" / "dir" / "metrics.json").as_posix()
    return {
        "catalog": {
            "boats": {
                "type": "pandas.CSVDataSet",
                "filepath": boat_path,
                "versioned": True,
            },
            "planes": {"type": "tracking.MetricsDataSet", "filepath": plane_path},
        },
    }


@pytest.fixture
def data_set(filepath):
    return CSVDataSet(filepath=filepath, save_args={"index": False})


@pytest.fixture
def multi_catalog():
    csv = CSVDataSet(filepath="abc.csv")
    parq = ParquetDataSet(filepath="xyz.parq")
    layers = {"raw": {"abc.csv"}, "model": {"xyz.parq"}}
    return DataCatalog({"abc": csv, "xyz": parq}, layers=layers)


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
        pattern = r"Failed while loading data from data set CSVDataSet"
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

    def test_exists_invalid(self, data_catalog):
        """Check the error when calling `exists` on invalid data set"""
        assert not data_catalog.exists("wrong_key")

    def test_release_unregistered(self, data_catalog):
        """Check the error when calling `release` on unregistered data set"""
        pattern = r"DataSet \'wrong_key\' not found in the catalog"
        with pytest.raises(DataSetNotFoundError, match=pattern) as e:
            data_catalog.release("wrong_key")
        assert "did you mean" not in str(e.value)

    def test_release_unregistered_typo(self, data_catalog):
        """Check the error when calling `release` on mistyped data set"""
        pattern = (
            "DataSet 'text' not found in the catalog"
            " - did you mean one of these instead: test"
        )
        with pytest.raises(DataSetNotFoundError, match=re.escape(pattern)):
            data_catalog.release("text")

    def test_multi_catalog_list(self, multi_catalog):
        """Test data catalog which contains multiple data sets"""
        entries = multi_catalog.list()
        assert "abc" in entries
        assert "xyz" in entries

    @pytest.mark.parametrize(
        "pattern,expected",
        [
            ("^a", ["abc"]),
            ("a|x", ["abc", "xyz"]),
            ("^(?!(a|x))", []),
            ("def", []),
            ("", []),
        ],
    )
    def test_multi_catalog_list_regex(self, multi_catalog, pattern, expected):
        """Test that regex patterns filter data sets accordingly"""
        assert multi_catalog.list(regex_search=pattern) == expected

    def test_multi_catalog_list_bad_regex(self, multi_catalog):
        """Test that bad regex is caught accordingly"""
        escaped_regex = r"\(\("
        pattern = f"Invalid regular expression provided: `{escaped_regex}`"
        with pytest.raises(SyntaxError, match=pattern):
            multi_catalog.list("((")

    def test_eq(self, multi_catalog, data_catalog):
        assert multi_catalog == multi_catalog  # pylint: disable=comparison-with-itself
        assert multi_catalog == multi_catalog.shallow_copy()
        assert multi_catalog != data_catalog

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.datasets.boats, CSVDataSet)
        assert isinstance(data_catalog_from_config.datasets.cars, CSVDataSet)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config.add("new_dataset", CSVDataSet("some_path"))
        assert isinstance(data_catalog_from_config.datasets.new_dataset, CSVDataSet)
        assert isinstance(data_catalog_from_config.datasets.boats, CSVDataSet)

    def test_adding_datasets_not_allowed(self, data_catalog_from_config):
        """Check error if user tries to update the datasets attribute"""
        pattern = r"Please use DataCatalog.add\(\) instead"
        with pytest.raises(AttributeError, match=pattern):
            data_catalog_from_config.datasets.new_dataset = None

    def test_add_feed_dict_should_grow_linearly(self, mocker, data_catalog_from_config):
        """Check number of calls to `_sub_nonword_chars` when adding feed dict
        should grow linearly with the number of keys in the dict.
        Simulate this issue: https://github.com/kedro-org/kedro/issues/951
        """
        mock_sub_nonword_chars = mocker.patch(
            "kedro.io.data_catalog._sub_nonword_chars"
        )
        feed_dict = {"key1": "val1", "key2": "val2", "key3": "val3", "key4": "val4"}
        data_catalog_from_config.add_feed_dict(feed_dict)
        assert mock_sub_nonword_chars.call_count == len(feed_dict)

    def test_mutating_datasets_not_allowed(self, data_catalog_from_config):
        """Check error if user tries to update the datasets attribute"""
        pattern = "Please change datasets through configuration."
        with pytest.raises(AttributeError, match=pattern):
            data_catalog_from_config.datasets.cars = None

    def test_confirm(self, mocker, caplog):
        """Confirm the dataset"""
        mock_ds = mocker.Mock()
        data_catalog = DataCatalog(data_sets={"mocked": mock_ds})
        data_catalog.confirm("mocked")
        mock_ds.confirm.assert_called_once_with()
        assert caplog.record_tuples == [
            ("kedro.io.data_catalog", logging.INFO, "Confirming DataSet 'mocked'")
        ]

    @pytest.mark.parametrize(
        "dataset_name,error_pattern",
        [
            ("missing", "DataSet 'missing' not found in the catalog"),
            ("test", "DataSet 'test' does not have 'confirm' method"),
        ],
    )
    def test_bad_confirm(self, data_catalog, dataset_name, error_pattern):
        """Test confirming a non existent dataset or one that
        does not have `confirm` method"""
        with pytest.raises(DataSetError, match=re.escape(error_pattern)):
            data_catalog.confirm(dataset_name)

    def test_layers(self, data_catalog, data_catalog_from_config):
        """Test dataset layers are correctly parsed"""
        assert data_catalog.layers is None
        # only one dataset is assigned a layer in the config
        assert data_catalog_from_config.layers == {"raw": {"cars"}}


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
        pattern = (
            "An exception occurred when parsing config for DataSet `boats`:\n"
            "`type` is missing from DataSet catalog configuration"
        )
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_module(self, sane_config):
        """Check the error if the type points to nonexistent module"""
        sane_config["catalog"]["boats"][
            "type"
        ] = "kedro.invalid_module_name.io.CSVDataSet"

        error_msg = "Class `kedro.invalid_module_name.io.CSVDataSet` not found"
        with pytest.raises(DataSetError, match=re.escape(error_msg)):
            DataCatalog.from_config(**sane_config)

    def test_config_relative_import(self, sane_config):
        """Check the error if the type points to a relative import"""
        sane_config["catalog"]["boats"]["type"] = ".CSVDataSetInvalid"

        pattern = "`type` class path does not support relative paths"
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_import_extras(self, sane_config):
        """Test kedro.extras.datasets default path to the dataset class"""
        sane_config["catalog"]["boats"]["type"] = "pandas.CSVDataSet"
        assert DataCatalog.from_config(**sane_config)

    def test_config_missing_class(self, sane_config):
        """Check the error if the type points to nonexistent class"""
        sane_config["catalog"]["boats"]["type"] = "kedro.io.CSVDataSetInvalid"

        pattern = (
            "An exception occurred when parsing config for DataSet `boats`:\n"
            "Class `kedro.io.CSVDataSetInvalid` not found"
        )
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_data_set(self, sane_config):
        """Check the error if the type points to invalid class"""
        sane_config["catalog"]["boats"]["type"] = "DataCatalog"
        pattern = (
            "An exception occurred when parsing config for DataSet `boats`:\n"
            "DataSet type `kedro.io.data_catalog.DataCatalog` is invalid: "
            "all data set types must extend `AbstractDataSet`"
        )
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_arguments(self, sane_config):
        """Check the error if the data set config contains invalid arguments"""
        sane_config["catalog"]["boats"]["save_and_load_args"] = False
        pattern = (
            r"DataSet 'boats' must only contain arguments valid for "
            r"the constructor of `.*CSVDataSet`"
        )
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_empty_config(self):
        """Test empty config"""
        assert DataCatalog.from_config(None)

    def test_missing_credentials(self, sane_config):
        """Check the error if credentials can't be located"""
        sane_config["catalog"]["cars"]["credentials"] = "missing"
        with pytest.raises(KeyError, match=r"Unable to find credentials \'missing\'"):
            DataCatalog.from_config(**sane_config)

    def test_link_credentials(self, sane_config, mocker):
        """Test credentials being linked to the relevant data set"""
        mock_client = mocker.patch("kedro.extras.datasets.pandas.csv_dataset.fsspec")
        config = deepcopy(sane_config)
        del config["catalog"]["boats"]

        DataCatalog.from_config(**config)

        expected_client_kwargs = sane_config["credentials"]["s3_credentials"]
        mock_client.filesystem.assert_called_with("s3", **expected_client_kwargs)

    def test_nested_credentials(self, sane_config_with_nested_creds, mocker):
        mock_client = mocker.patch("kedro.extras.datasets.pandas.csv_dataset.fsspec")
        config = deepcopy(sane_config_with_nested_creds)
        del config["catalog"]["boats"]
        DataCatalog.from_config(**config)

        expected_client_kwargs = {
            "client_kwargs": {
                "credentials": {
                    "client_kwargs": {
                        "aws_access_key_id": "OTHER_FAKE_ACCESS_KEY",
                        "aws_secret_access_key": "OTHER_FAKE_SECRET_KEY",
                    }
                }
            },
            "key": "secret",
        }
        mock_client.filesystem.assert_called_once_with("s3", **expected_client_kwargs)

    def test_missing_nested_credentials(self, sane_config_with_nested_creds):
        del sane_config_with_nested_creds["credentials"]["other_credentials"]
        pattern = "Unable to find credentials 'other_credentials'"
        with pytest.raises(KeyError, match=pattern):
            DataCatalog.from_config(**sane_config_with_nested_creds)

    def test_missing_dependency(self, sane_config, mocker):
        """Test that dependency is missing."""
        pattern = "dependency issue"

        # pylint: disable=unused-argument,inconsistent-return-statements
        def dummy_load(obj_path, *args, **kwargs):
            if obj_path == "kedro.extras.datasets.pandas.CSVDataSet":
                raise AttributeError(pattern)
            if obj_path == "kedro.extras.datasets.pandas.__all__":
                return ["CSVDataSet"]

        mocker.patch("kedro.io.core.load_obj", side_effect=dummy_load)
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_idempotent_catalog(self, sane_config):
        """Test that data catalog instantiations are idempotent"""
        _ = DataCatalog.from_config(**sane_config)  # NOQA
        catalog = DataCatalog.from_config(**sane_config)
        assert catalog

    def test_error_dataset_init(self, bad_config):
        """Check the error when trying to instantiate erroneous data set"""
        pattern = r"Failed to instantiate DataSet \'bad\' of type `.*BadDataSet`"
        with pytest.raises(DataSetError, match=pattern):
            DataCatalog.from_config(bad_config, None)

    def test_confirm(self, tmp_path, caplog, mocker):
        """Confirm the dataset"""
        mock_confirm = mocker.patch("kedro.io.IncrementalDataSet.confirm")
        catalog = {
            "ds_to_confirm": {
                "type": "IncrementalDataSet",
                "dataset": "pandas.CSVDataSet",
                "path": str(tmp_path),
            }
        }
        data_catalog = DataCatalog.from_config(catalog=catalog)
        data_catalog.confirm("ds_to_confirm")
        assert caplog.record_tuples == [
            (
                "kedro.io.data_catalog",
                logging.INFO,
                "Confirming DataSet 'ds_to_confirm'",
            )
        ]
        mock_confirm.assert_called_once_with()

    @pytest.mark.parametrize(
        "dataset_name,pattern",
        [
            ("missing", "DataSet 'missing' not found in the catalog"),
            ("boats", "DataSet 'boats' does not have 'confirm' method"),
        ],
    )
    def test_bad_confirm(self, sane_config, dataset_name, pattern):
        """Test confirming non existent dataset or the one that
        does not have `confirm` method"""
        data_catalog = DataCatalog.from_config(**sane_config)
        with pytest.raises(DataSetError, match=re.escape(pattern)):
            data_catalog.confirm(dataset_name)


class TestDataCatalogVersioned:
    def test_from_sane_config_versioned(self, sane_config, dummy_dataframe):
        """Test load and save of versioned data sets from config"""
        sane_config["catalog"]["boats"]["versioned"] = True

        # Decompose `generate_timestamp` to keep `current_ts` reference.
        current_ts = datetime.now(tz=timezone.utc)
        fmt = (
            "{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}"
            ".{d.minute:02d}.{d.second:02d}.{ms:03d}Z"
        )
        version = fmt.format(d=current_ts, ms=current_ts.microsecond // 1000)

        catalog = DataCatalog.from_config(
            **sane_config,
            load_versions={"boats": version},
            save_version=version,
        )

        catalog.save("boats", dummy_dataframe)
        path = Path(sane_config["catalog"]["boats"]["filepath"])
        path = path / version / path.name
        assert path.is_file()

        reloaded_df = catalog.load("boats")
        assert_frame_equal(reloaded_df, dummy_dataframe)

        reloaded_df_version = catalog.load("boats", version=version)
        assert_frame_equal(reloaded_df_version, dummy_dataframe)

        # Verify that `VERSION_FORMAT` can help regenerate `current_ts`.
        actual_timestamp = datetime.strptime(
            catalog.datasets.boats.resolve_load_version(),  # pylint: disable=no-member
            VERSION_FORMAT,
        )
        expected_timestamp = current_ts.replace(
            microsecond=current_ts.microsecond // 1000 * 1000, tzinfo=None
        )
        assert actual_timestamp == expected_timestamp

    @pytest.mark.parametrize("versioned", [True, False])
    def test_from_sane_config_versioned_warn(self, caplog, sane_config, versioned):
        """Check the warning if `version` attribute was added
        to the data set config"""
        sane_config["catalog"]["boats"]["versioned"] = versioned
        sane_config["catalog"]["boats"]["version"] = True
        DataCatalog.from_config(**sane_config)
        log_record = caplog.records[0]
        expected_log_message = (
            "`version` attribute removed from data set configuration since it "
            "is a reserved word and cannot be directly specified"
        )
        assert log_record.levelname == "WARNING"
        assert expected_log_message in log_record.message

    def test_from_sane_config_load_versions_warn(self, sane_config):
        sane_config["catalog"]["boats"]["versioned"] = True
        version = generate_timestamp()
        load_version = {"non-boart": version}
        pattern = r"\`load_versions\` keys \[non-boart\] are not found in the catalog\."
        with pytest.raises(DataSetNotFoundError, match=pattern):
            DataCatalog.from_config(**sane_config, load_versions=load_version)

    def test_compare_tracking_and_other_dataset_versioned(
        self, sane_config_with_tracking_ds, dummy_dataframe
    ):
        """Test saving of tracking data sets from config results in the same
        save version as other versioned datasets."""

        catalog = DataCatalog.from_config(**sane_config_with_tracking_ds)

        catalog.save("boats", dummy_dataframe)
        dummy_data = {"col1": 1, "col2": 2, "col3": 3}
        catalog.save("planes", dummy_data)

        # Verify that saved version on tracking dataset is the same as on the CSV dataset
        csv_timestamp = datetime.strptime(
            catalog.datasets.boats.resolve_save_version(),  # pylint: disable=no-member
            VERSION_FORMAT,
        )
        tracking_timestamp = datetime.strptime(
            catalog.datasets.planes.resolve_save_version(),  # pylint: disable=no-member
            VERSION_FORMAT,
        )

        assert tracking_timestamp == csv_timestamp

    def test_load_version(self, sane_config, dummy_dataframe, mocker):
        """Test load versioned data sets from config"""
        new_dataframe = pd.DataFrame({"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]})
        sane_config["catalog"]["boats"]["versioned"] = True
        mocker.patch(
            "kedro.io.data_catalog.generate_timestamp", side_effect=["first", "second"]
        )

        # save first version of the dataset
        catalog = DataCatalog.from_config(**sane_config)
        catalog.save("boats", dummy_dataframe)

        # save second version of the dataset
        catalog = DataCatalog.from_config(**sane_config)
        catalog.save("boats", new_dataframe)

        assert_frame_equal(catalog.load("boats", version="first"), dummy_dataframe)
        assert_frame_equal(catalog.load("boats", version="second"), new_dataframe)
        assert_frame_equal(catalog.load("boats"), new_dataframe)

    def test_load_version_on_unversioned_dataset(
        self, sane_config, dummy_dataframe, mocker
    ):
        mocker.patch("kedro.io.data_catalog.generate_timestamp", return_value="first")

        catalog = DataCatalog.from_config(**sane_config)
        catalog.save("boats", dummy_dataframe)

        with pytest.raises(DataSetError):
            catalog.load("boats", version="first")

    def test_replacing_nonword_characters(self):
        """Test replacing non-word characters in dataset names"""
        csv = CSVDataSet(filepath="abc.csv")
        datasets = {"ds1@spark": csv, "ds2_spark": csv, "ds3.csv": csv, "jalapeño": csv}

        catalog = DataCatalog(data_sets=datasets)
        assert "ds1@spark" not in catalog.datasets.__dict__
        assert "ds2__spark" not in catalog.datasets.__dict__
        assert "ds3.csv" not in catalog.datasets.__dict__
        assert "jalape__o" not in catalog.datasets.__dict__

        assert "ds1__spark" in catalog.datasets.__dict__
        assert "ds2_spark" in catalog.datasets.__dict__
        assert "ds3__csv" in catalog.datasets.__dict__
        assert "jalapeño" in catalog.datasets.__dict__
