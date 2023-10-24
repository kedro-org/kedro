import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
import pytest
from kedro_datasets.pandas import CSVDataset, ParquetDataset
from pandas.testing import assert_frame_equal

from kedro.io import (
    AbstractDataset,
    DataCatalog,
    DatasetAlreadyExistsError,
    DatasetError,
    DatasetNotFoundError,
    LambdaDataset,
    MemoryDataset,
)
from kedro.io.core import (
    _DEFAULT_PACKAGES,
    VERSION_FORMAT,
    Version,
    generate_timestamp,
    parse_dataset_definition,
)


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
            "boats": {"type": "pandas.CSVDataset", "filepath": filepath},
            "cars": {
                "type": "pandas.CSVDataset",
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
                "type": "pandas.CSVDataset",
                "filepath": boat_path,
                "versioned": True,
            },
            "planes": {"type": "tracking.MetricsDataset", "filepath": plane_path},
        },
    }


@pytest.fixture
def config_with_dataset_factories():
    return {
        "catalog": {
            "{brand}_cars": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{brand}_cars.csv",
            },
            "audi_cars": {
                "type": "pandas.ParquetDataset",
                "filepath": "data/01_raw/audi_cars.pq",
            },
            "{type}_boats": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{type}_boats.csv",
            },
        },
    }


@pytest.fixture
def config_with_dataset_factories_nested():
    return {
        "catalog": {
            "{brand}_cars": {
                "type": "kedro_datasets.partitions.PartitionedDataset",
                "path": "data/01_raw",
                "dataset": "pandas.CSVDataset",
                "metadata": {
                    "my-plugin": {
                        "brand": "{brand}",
                        "list_config": [
                            "NA",
                            "{brand}",
                        ],
                        "nested_list_dict": [{}, {"brand": "{brand}"}],
                    }
                },
            },
        },
    }


@pytest.fixture
def config_with_dataset_factories_with_default(config_with_dataset_factories):
    config_with_dataset_factories["catalog"]["{default_dataset}"] = {
        "type": "pandas.CSVDataset",
        "filepath": "data/01_raw/{default_dataset}.csv",
    }
    return config_with_dataset_factories


@pytest.fixture
def config_with_dataset_factories_bad_pattern(config_with_dataset_factories):
    config_with_dataset_factories["catalog"]["{type}@planes"] = {
        "type": "pandas.ParquetDataset",
        "filepath": "data/01_raw/{brand}_plane.pq",
    }
    return config_with_dataset_factories


@pytest.fixture
def config_with_dataset_factories_only_patterns():
    return {
        "catalog": {
            "{default}": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{default}.csv",
            },
            "{namespace}_{dataset}": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{namespace}_{dataset}.pq",
            },
            "{country}_companies": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{country}_companies.csv",
            },
            "{dataset}s": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{dataset}s.csv",
            },
        },
    }


@pytest.fixture
def dataset(filepath):
    return CSVDataset(filepath=filepath, save_args={"index": False})


@pytest.fixture
def multi_catalog():
    csv = CSVDataset(filepath="abc.csv")
    parq = ParquetDataset(filepath="xyz.parq")
    layers = {"raw": {"abc.csv"}, "model": {"xyz.parq"}}
    return DataCatalog({"abc": csv, "xyz": parq}, layers=layers)


@pytest.fixture
def memory_catalog():
    ds1 = MemoryDataset({"data": 42})
    ds2 = MemoryDataset([1, 2, 3, 4, 5])
    return DataCatalog({"ds1": ds1, "ds2": ds2})


@pytest.fixture
def conflicting_feed_dict():
    ds1 = MemoryDataset({"data": 0})
    return {"ds1": ds1, "ds3": 1}


class BadDataset(AbstractDataset):  # pragma: no cover
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
        "bad": {"type": "tests.io.test_data_catalog.BadDataset", "filepath": filepath}
    }


@pytest.fixture
def data_catalog(dataset):
    return DataCatalog(datasets={"test": dataset})


@pytest.fixture
def data_catalog_from_config(sane_config):
    return DataCatalog.from_config(**sane_config)


class TestDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the data set"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, dataset, dummy_dataframe):
        """Test adding and then saving and reloading the data set"""
        catalog = DataCatalog(datasets={})
        catalog.add("test", dataset)
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_all_save_and_load(self, dataset, dummy_dataframe):
        """Test adding all to the data catalog and then saving and reloading
        the data set"""
        catalog = DataCatalog(datasets={})
        catalog.add_all({"test": dataset})
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a data set
        from nonexistent source"""
        pattern = r"Failed while loading data from data set CSVDataset"
        with pytest.raises(DatasetError, match=pattern):
            data_catalog.load("test")

    def test_add_dataset_twice(self, data_catalog, dataset):
        """Check the error when attempting to add the data set twice"""
        pattern = r"Dataset 'test' has already been registered"
        with pytest.raises(DatasetAlreadyExistsError, match=pattern):
            data_catalog.add("test", dataset)

    def test_load_from_unregistered(self):
        """Check the error when attempting to load unregistered data set"""
        catalog = DataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.load("test")

    def test_save_to_unregistered(self, dummy_dataframe):
        """Check the error when attempting to save to unregistered data set"""
        catalog = DataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
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
        catalog = DataCatalog(datasets={"test": LambdaDataset(None, None)})
        result = catalog.exists("test")

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "'exists()' not implemented for 'LambdaDataset'. "
            "Assuming output does not exist." in log_record.message
        )
        assert result is False

    def test_exists_invalid(self, data_catalog):
        """Check the error when calling `exists` on invalid data set"""
        assert not data_catalog.exists("wrong_key")

    def test_release_unregistered(self, data_catalog):
        """Check the error when calling `release` on unregistered data set"""
        pattern = r"Dataset \'wrong_key\' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern) as e:
            data_catalog.release("wrong_key")
        assert "did you mean" not in str(e.value)

    def test_release_unregistered_typo(self, data_catalog):
        """Check the error when calling `release` on mistyped data set"""
        pattern = (
            "Dataset 'text' not found in the catalog"
            " - did you mean one of these instead: test"
        )
        with pytest.raises(DatasetNotFoundError, match=re.escape(pattern)):
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
        pattern = f"Invalid regular expression provided: '{escaped_regex}'"
        with pytest.raises(SyntaxError, match=pattern):
            multi_catalog.list("((")

    def test_eq(self, multi_catalog, data_catalog):
        assert multi_catalog == multi_catalog.shallow_copy()
        assert multi_catalog != data_catalog

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.datasets.boats, CSVDataset)
        assert isinstance(data_catalog_from_config.datasets.cars, CSVDataset)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config.add("new_dataset", CSVDataset("some_path"))
        assert isinstance(data_catalog_from_config.datasets.new_dataset, CSVDataset)
        assert isinstance(data_catalog_from_config.datasets.boats, CSVDataset)

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
        with caplog.at_level(logging.INFO):
            mock_ds = mocker.Mock()
            data_catalog = DataCatalog(datasets={"mocked": mock_ds})
            data_catalog.confirm("mocked")
            mock_ds.confirm.assert_called_once_with()
            assert caplog.record_tuples == [
                (
                    "kedro.io.data_catalog",
                    logging.INFO,
                    "Confirming dataset 'mocked'",
                )
            ]

    @pytest.mark.parametrize(
        "dataset_name,error_pattern",
        [
            ("missing", "Dataset 'missing' not found in the catalog"),
            ("test", "Dataset 'test' does not have 'confirm' method"),
        ],
    )
    def test_bad_confirm(self, data_catalog, dataset_name, error_pattern):
        """Test confirming a non existent dataset or one that
        does not have `confirm` method"""
        with pytest.raises(DatasetError, match=re.escape(error_pattern)):
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
            "An exception occurred when parsing config for dataset 'boats':\n"
            "'type' is missing from dataset catalog configuration"
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_module(self, sane_config):
        """Check the error if the type points to nonexistent module"""
        sane_config["catalog"]["boats"][
            "type"
        ] = "kedro.invalid_module_name.io.CSVDataset"

        error_msg = "Class 'kedro.invalid_module_name.io.CSVDataset' not found"
        with pytest.raises(DatasetError, match=re.escape(error_msg)):
            DataCatalog.from_config(**sane_config)

    def test_config_relative_import(self, sane_config):
        """Check the error if the type points to a relative import"""
        sane_config["catalog"]["boats"]["type"] = ".CSVDatasetInvalid"

        pattern = "'type' class path does not support relative paths"
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_import_kedro_datasets(self, sane_config, mocker):
        """Test kedro_datasets default path to the dataset class"""
        # Spy _load_obj because kedro_datasets is not installed and we can't import it.

        import kedro.io.core

        spy = mocker.spy(kedro.io.core, "_load_obj")
        parse_dataset_definition(sane_config["catalog"]["boats"])
        for prefix, call_args in zip(_DEFAULT_PACKAGES, spy.call_args_list):
            # In Python 3.7 call_args.args is not available thus we access the call
            # arguments with less meaningful index.
            # The 1st index returns a tuple, the 2nd index return the name of module.
            assert call_args[0][0] == f"{prefix}pandas.CSVDataset"

    def test_config_import_extras(self, sane_config):
        """Test kedro_datasets default path to the dataset class"""
        sane_config["catalog"]["boats"]["type"] = "pandas.CSVDataset"
        assert DataCatalog.from_config(**sane_config)

    def test_config_missing_class(self, sane_config):
        """Check the error if the type points to nonexistent class"""
        sane_config["catalog"]["boats"]["type"] = "kedro.io.CSVDatasetInvalid"

        pattern = (
            "An exception occurred when parsing config for dataset 'boats':\n"
            "Class 'kedro.io.CSVDatasetInvalid' not found"
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_dataset(self, sane_config):
        """Check the error if the type points to invalid class"""
        sane_config["catalog"]["boats"]["type"] = "DataCatalog"
        pattern = (
            "An exception occurred when parsing config for dataset 'boats':\n"
            "Dataset type 'kedro.io.data_catalog.DataCatalog' is invalid: "
            "all data set types must extend 'AbstractDataset'"
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**sane_config)

    def test_config_invalid_arguments(self, sane_config):
        """Check the error if the data set config contains invalid arguments"""
        sane_config["catalog"]["boats"]["save_and_load_args"] = False
        pattern = (
            r"Dataset 'boats' must only contain arguments valid for "
            r"the constructor of '.*CSVDataset'"
        )
        with pytest.raises(DatasetError, match=pattern):
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
        mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
        config = deepcopy(sane_config)
        del config["catalog"]["boats"]

        DataCatalog.from_config(**config)

        expected_client_kwargs = sane_config["credentials"]["s3_credentials"]
        mock_client.filesystem.assert_called_with("s3", **expected_client_kwargs)

    def test_nested_credentials(self, sane_config_with_nested_creds, mocker):
        mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
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

        def dummy_load(obj_path, *args, **kwargs):
            if obj_path == "kedro_datasets.pandas.CSVDataset":
                raise AttributeError(pattern)
            if obj_path == "kedro_datasets.pandas.__all__":
                return ["CSVDataset"]

        mocker.patch("kedro.io.core.load_obj", side_effect=dummy_load)
        with pytest.raises(DatasetError, match=pattern):
            DataCatalog.from_config(**sane_config)

    def test_idempotent_catalog(self, sane_config):
        """Test that data catalog instantiations are idempotent"""
        _ = DataCatalog.from_config(**sane_config)  # NOQA
        catalog = DataCatalog.from_config(**sane_config)
        assert catalog

    def test_error_dataset_init(self, bad_config):
        """Check the error when trying to instantiate erroneous data set"""
        pattern = r"Failed to instantiate dataset \'bad\' of type '.*BadDataset'"
        with pytest.raises(DatasetError, match=pattern):
            DataCatalog.from_config(bad_config, None)

    def test_confirm(self, tmp_path, caplog, mocker):
        """Confirm the dataset"""
        with caplog.at_level(logging.INFO):
            mock_confirm = mocker.patch(
                "kedro_datasets.partitions.incremental_dataset.IncrementalDataset.confirm"
            )
            catalog = {
                "ds_to_confirm": {
                    "type": "kedro_datasets.partitions.incremental_dataset.IncrementalDataset",
                    "dataset": "pandas.CSVDataset",
                    "path": str(tmp_path),
                }
            }
            data_catalog = DataCatalog.from_config(catalog=catalog)
            data_catalog.confirm("ds_to_confirm")
            assert caplog.record_tuples == [
                (
                    "kedro.io.data_catalog",
                    logging.INFO,
                    "Confirming dataset 'ds_to_confirm'",
                )
            ]
            mock_confirm.assert_called_once_with()

    @pytest.mark.parametrize(
        "dataset_name,pattern",
        [
            ("missing", "Dataset 'missing' not found in the catalog"),
            ("boats", "Dataset 'boats' does not have 'confirm' method"),
        ],
    )
    def test_bad_confirm(self, sane_config, dataset_name, pattern):
        """Test confirming non existent dataset or the one that
        does not have `confirm` method"""
        data_catalog = DataCatalog.from_config(**sane_config)
        with pytest.raises(DatasetError, match=re.escape(pattern)):
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
            catalog.datasets.boats.resolve_load_version(),
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
            "'version' attribute removed from data set configuration since it "
            "is a reserved word and cannot be directly specified"
        )
        assert log_record.levelname == "WARNING"
        assert expected_log_message in log_record.message

    def test_from_sane_config_load_versions_warn(self, sane_config):
        sane_config["catalog"]["boats"]["versioned"] = True
        version = generate_timestamp()
        load_version = {"non-boart": version}
        pattern = r"\'load_versions\' keys \[non-boart\] are not found in the catalog\."
        with pytest.raises(DatasetNotFoundError, match=pattern):
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
            catalog.datasets.boats.resolve_save_version(),
            VERSION_FORMAT,
        )
        tracking_timestamp = datetime.strptime(
            catalog.datasets.planes.resolve_save_version(),
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

        with pytest.raises(DatasetError):
            catalog.load("boats", version="first")

    def test_replacing_nonword_characters(self):
        """Test replacing non-word characters in dataset names"""
        csv = CSVDataset(filepath="abc.csv")
        datasets = {"ds1@spark": csv, "ds2_spark": csv, "ds3.csv": csv, "jalapeño": csv}

        catalog = DataCatalog(datasets=datasets)
        assert "ds1@spark" not in catalog.datasets.__dict__
        assert "ds2__spark" not in catalog.datasets.__dict__
        assert "ds3.csv" not in catalog.datasets.__dict__
        assert "jalape__o" not in catalog.datasets.__dict__

        assert "ds1__spark" in catalog.datasets.__dict__
        assert "ds2_spark" in catalog.datasets.__dict__
        assert "ds3__csv" in catalog.datasets.__dict__
        assert "jalapeño" in catalog.datasets.__dict__

    def test_no_versions_with_cloud_protocol(self, monkeypatch):
        """Check the error if no versions are available for load from cloud storage"""
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "dummmy")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "dummmy")
        version = Version(load=None, save=None)
        versioned_dataset = CSVDataset("s3://bucket/file.csv", version=version)
        pattern = re.escape(
            f"Did not find any versions for {versioned_dataset}. "
            f"This could be due to insufficient permission."
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_dataset.load()


class TestDataCatalogDatasetFactories:
    def test_match_added_to_datasets_on_get(self, config_with_dataset_factories):
        """Check that the datasets that match patterns are only added when fetched"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        assert "{brand}_cars" not in catalog._datasets
        assert "tesla_cars" not in catalog._datasets
        assert "{brand}_cars" in catalog._dataset_patterns

        tesla_cars = catalog._get_dataset("tesla_cars")
        assert isinstance(tesla_cars, CSVDataset)
        assert "tesla_cars" in catalog._datasets

    @pytest.mark.parametrize(
        "dataset_name, expected",
        [
            ("audi_cars", True),
            ("tesla_cars", True),
            ("row_boats", True),
            ("boats", False),
            ("tesla_card", False),
        ],
    )
    def test_exists_in_catalog_config(
        self, config_with_dataset_factories, dataset_name, expected
    ):
        """Check that the dataset exists in catalog when it matches a pattern
        or is in the catalog"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        assert (dataset_name in catalog) == expected

    def test_patterns_not_in_catalog_datasets(self, config_with_dataset_factories):
        """Check that the pattern is not in the catalog datasets"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        assert "audi_cars" in catalog._datasets
        assert "{brand}_cars" not in catalog._datasets
        assert "audi_cars" not in catalog._dataset_patterns
        assert "{brand}_cars" in catalog._dataset_patterns

    def test_explicit_entry_not_overwritten(self, config_with_dataset_factories):
        """Check that the existing catalog entry is not overwritten by config in pattern"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        audi_cars = catalog._get_dataset("audi_cars")
        assert isinstance(audi_cars, ParquetDataset)

    @pytest.mark.parametrize(
        "dataset_name,pattern",
        [
            ("missing", "Dataset 'missing' not found in the catalog"),
            ("tesla@cars", "Dataset 'tesla@cars' not found in the catalog"),
        ],
    )
    def test_dataset_not_in_catalog_when_no_pattern_match(
        self, config_with_dataset_factories, dataset_name, pattern
    ):
        """Check that the dataset is not added to the catalog when there is no pattern"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            catalog._get_dataset(dataset_name)

    def test_sorting_order_patterns(self, config_with_dataset_factories_only_patterns):
        """Check that the sorted order of the patterns is correct according
        to parsing rules"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories_only_patterns)
        sorted_keys_expected = [
            "{country}_companies",
            "{namespace}_{dataset}",
            "{dataset}s",
            "{default}",
        ]
        assert list(catalog._dataset_patterns.keys()) == sorted_keys_expected

    def test_default_dataset(self, config_with_dataset_factories_with_default, caplog):
        """Check that default dataset is used when no other pattern matches"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories_with_default)
        assert "jet@planes" not in catalog._datasets
        jet_dataset = catalog._get_dataset("jet@planes")
        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "Config from the dataset factory pattern '{default_dataset}' "
            "in the catalog will be used to override the default "
            "MemoryDataset creation for the dataset 'jet@planes'" in log_record.message
        )
        assert isinstance(jet_dataset, CSVDataset)

    def test_unmatched_key_error_when_parsing_config(
        self, config_with_dataset_factories_bad_pattern
    ):
        """Check error raised when key mentioned in the config is not in pattern name"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories_bad_pattern)
        pattern = (
            "Unable to resolve 'data/01_raw/{brand}_plane.pq' from the pattern '{type}@planes'. "
            "Keys used in the configuration should be present in the dataset factory pattern."
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            catalog._get_dataset("jet@planes")

    def test_factory_layer(self, config_with_dataset_factories):
        """Check that layer is correctly processed for patterned datasets"""
        config_with_dataset_factories["catalog"]["{brand}_cars"]["layer"] = "raw"
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        _ = catalog._get_dataset("tesla_cars")
        assert catalog.layers["raw"] == {"tesla_cars"}

    def test_factory_config_versioned(
        self, config_with_dataset_factories, filepath, dummy_dataframe
    ):
        """Test load and save of versioned data sets from config"""
        config_with_dataset_factories["catalog"]["{brand}_cars"]["versioned"] = True
        config_with_dataset_factories["catalog"]["{brand}_cars"]["filepath"] = filepath

        assert "tesla_cars" not in config_with_dataset_factories

        # Decompose `generate_timestamp` to keep `current_ts` reference.
        current_ts = datetime.now(tz=timezone.utc)
        fmt = (
            "{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}"
            ".{d.minute:02d}.{d.second:02d}.{ms:03d}Z"
        )
        version = fmt.format(d=current_ts, ms=current_ts.microsecond // 1000)

        catalog = DataCatalog.from_config(
            **config_with_dataset_factories,
            load_versions={"tesla_cars": version},
            save_version=version,
        )

        catalog.save("tesla_cars", dummy_dataframe)
        path = Path(
            config_with_dataset_factories["catalog"]["{brand}_cars"]["filepath"]
        )
        path = path / version / path.name
        assert path.is_file()

        reloaded_df = catalog.load("tesla_cars")
        assert_frame_equal(reloaded_df, dummy_dataframe)

        reloaded_df_version = catalog.load("tesla_cars", version=version)
        assert_frame_equal(reloaded_df_version, dummy_dataframe)

        # Verify that `VERSION_FORMAT` can help regenerate `current_ts`.
        actual_timestamp = datetime.strptime(
            catalog.datasets.tesla_cars.resolve_load_version(),
            VERSION_FORMAT,
        )
        expected_timestamp = current_ts.replace(
            microsecond=current_ts.microsecond // 1000 * 1000, tzinfo=None
        )
        assert actual_timestamp == expected_timestamp

    def test_factory_nested_config(self, config_with_dataset_factories_nested):
        catalog = DataCatalog.from_config(**config_with_dataset_factories_nested)
        dataset = catalog._get_dataset("tesla_cars")
        assert dataset.metadata["my-plugin"]["brand"] == "tesla"
        assert dataset.metadata["my-plugin"]["list_config"] == ["NA", "tesla"]
        assert dataset.metadata["my-plugin"]["nested_list_dict"] == [
            {},
            {"brand": "tesla"},
        ]
