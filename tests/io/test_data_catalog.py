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
    VersionAlreadyExistsError,
    generate_timestamp,
    parse_dataset_definition,
)


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
                "filepath": "data/01_raw/audi_cars.parquet",
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
        "filepath": "data/01_raw/{brand}_plane.parquet",
    }
    return config_with_dataset_factories


@pytest.fixture
def config_with_dataset_factories_only_patterns():
    return {
        "catalog": {
            "{namespace}_{dataset}": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{namespace}_{dataset}.parquet",
            },
            "{country}_companies": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{country}_companies.csv",
            },
            "{dataset}s": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{dataset}s.csv",
            },
            "{user_default}": {
                "type": "pandas.ExcelDataset",
                "filepath": "data/01_raw/{user_default}.xlsx",
            },
        },
    }


@pytest.fixture
def config_with_dataset_factories_only_patterns_no_default(
    config_with_dataset_factories_only_patterns,
):
    del config_with_dataset_factories_only_patterns["catalog"]["{user_default}"]
    return config_with_dataset_factories_only_patterns


@pytest.fixture
def multi_catalog():
    csv = CSVDataset(filepath="abc.csv")
    parq = ParquetDataset(filepath="xyz.parq")
    return DataCatalog({"abc": csv, "xyz": parq})


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
def data_catalog(dataset):
    return DataCatalog(datasets={"test": dataset})


@pytest.fixture
def data_catalog_from_config(correct_config):
    return DataCatalog.from_config(**correct_config)


class TestDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the dataset"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, dataset, dummy_dataframe):
        """Test adding and then saving and reloading the dataset"""
        catalog = DataCatalog(datasets={})
        catalog.add("test", dataset)
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_all_save_and_load(self, dataset, dummy_dataframe):
        """Test adding all to the data catalog and then saving and reloading
        the dataset"""
        catalog = DataCatalog(datasets={})
        catalog.add_all({"test": dataset})
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a dataset
        from nonexistent source"""
        pattern = r"Failed while loading data from dataset CSVDataset"
        with pytest.raises(DatasetError, match=pattern):
            data_catalog.load("test")

    def test_add_dataset_twice(self, data_catalog, dataset):
        """Check the error when attempting to add the dataset twice"""
        pattern = r"Dataset 'test' has already been registered"
        with pytest.raises(DatasetAlreadyExistsError, match=pattern):
            data_catalog.add("test", dataset)

    def test_load_from_unregistered(self):
        """Check the error when attempting to load unregistered dataset"""
        catalog = DataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.load("test")

    def test_save_to_unregistered(self, dummy_dataframe):
        """Check the error when attempting to save to unregistered dataset"""
        catalog = DataCatalog(datasets={})
        pattern = r"Dataset 'test' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern):
            catalog.save("test", dummy_dataframe)

    def test_feed_dict(self, memory_catalog, conflicting_feed_dict):
        """Test feed dict overriding some of the datasets"""
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
        """Test calling `exists` on the dataset, which didn't implement it"""
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
        """Check the error when calling `exists` on invalid dataset"""
        assert not data_catalog.exists("wrong_key")

    def test_release_unregistered(self, data_catalog):
        """Check the error when calling `release` on unregistered dataset"""
        pattern = r"Dataset \'wrong_key\' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern) as e:
            data_catalog.release("wrong_key")
        assert "did you mean" not in str(e.value)

    def test_release_unregistered_typo(self, data_catalog):
        """Check the error when calling `release` on mistyped dataset"""
        pattern = (
            "Dataset 'text' not found in the catalog"
            " - did you mean one of these instead: test"
        )
        with pytest.raises(DatasetNotFoundError, match=re.escape(pattern)):
            data_catalog.release("text")

    def test_multi_catalog_list(self, multi_catalog):
        """Test data catalog which contains multiple datasets"""
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
        """Test that regex patterns filter datasets accordingly"""
        assert multi_catalog.list(regex_search=pattern) == expected

    def test_multi_catalog_list_bad_regex(self, multi_catalog):
        """Test that bad regex is caught accordingly"""
        escaped_regex = r"\(\("
        pattern = f"Invalid regular expression provided: '{escaped_regex}'"
        with pytest.raises(SyntaxError, match=pattern):
            multi_catalog.list("((")

    def test_eq(self, multi_catalog, data_catalog):
        assert multi_catalog == multi_catalog.shallow_copy({})
        assert multi_catalog != data_catalog

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.datasets.boats, CSVDataset)
        assert isinstance(data_catalog_from_config.datasets.cars, CSVDataset)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config.add("new_dataset", CSVDataset(filepath="some_path"))
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
        """Test confirming a non-existent dataset or one that
        does not have `confirm` method"""
        with pytest.raises(DatasetError, match=re.escape(error_pattern)):
            data_catalog.confirm(dataset_name)

    def test_shallow_copy_returns_correct_class_type(
        self,
    ):
        class MyDataCatalog(DataCatalog):
            pass

        data_catalog = MyDataCatalog()
        copy = data_catalog.shallow_copy()
        assert isinstance(copy, MyDataCatalog)

    def test_key_completions(self, data_catalog_from_config):
        """Test catalog.datasets key completions"""
        assert isinstance(data_catalog_from_config.datasets["boats"], CSVDataset)
        assert isinstance(data_catalog_from_config.datasets["cars"], CSVDataset)
        data_catalog_from_config.add_feed_dict(
            {
                "params:model_options": [1, 2, 4],
                "params:model_options.random_state": [0, 42, 67],
            }
        )
        assert isinstance(
            data_catalog_from_config.datasets["params:model_options"], MemoryDataset
        )
        assert isinstance(
            data_catalog_from_config.datasets["params__model_options.random_state"],
            MemoryDataset,
        )
        assert set(data_catalog_from_config.datasets._ipython_key_completions_()) == {
            "boats",
            "cars",
            "params:model_options",
            "params:model_options.random_state",
        }


class TestDataCatalogFromConfig:
    def test_from_correct_config(self, data_catalog_from_config, dummy_dataframe):
        """Test populating the data catalog from config"""
        data_catalog_from_config.save("boats", dummy_dataframe)
        reloaded_df = data_catalog_from_config.load("boats")
        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_config_missing_type(self, correct_config):
        """Check the error if type attribute is missing for some dataset(s)
        in the config"""
        del correct_config["catalog"]["boats"]["type"]
        pattern = (
            "An exception occurred when parsing config for dataset 'boats':\n"
            "'type' is missing from dataset catalog configuration"
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**correct_config)

    def test_config_invalid_module(self, correct_config):
        """Check the error if the type points to nonexistent module"""
        correct_config["catalog"]["boats"]["type"] = (
            "kedro.invalid_module_name.io.CSVDataset"
        )

        error_msg = "No module named 'kedro.invalid_module_name'"
        with pytest.raises(DatasetError, match=re.escape(error_msg)):
            DataCatalog.from_config(**correct_config)

    def test_config_relative_import(self, correct_config):
        """Check the error if the type points to a relative import"""
        correct_config["catalog"]["boats"]["type"] = ".CSVDatasetInvalid"

        pattern = "'type' class path does not support relative paths"
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**correct_config)

    def test_config_import_kedro_datasets(self, correct_config, mocker):
        """Test kedro_datasets default path to the dataset class"""
        # Spy _load_obj because kedro_datasets is not installed and we can't import it.

        import kedro.io.core

        spy = mocker.spy(kedro.io.core, "_load_obj")
        parse_dataset_definition(correct_config["catalog"]["boats"])
        for prefix, call_args in zip(_DEFAULT_PACKAGES, spy.call_args_list):
            # In Python 3.7 call_args.args is not available thus we access the call
            # arguments with less meaningful index.
            # The 1st index returns a tuple, the 2nd index return the name of module.
            assert call_args[0][0] == f"{prefix}pandas.CSVDataset"

    def test_config_import_extras(self, correct_config):
        """Test kedro_datasets default path to the dataset class"""
        correct_config["catalog"]["boats"]["type"] = "pandas.CSVDataset"
        assert DataCatalog.from_config(**correct_config)

    def test_config_missing_class(self, correct_config):
        """Check the error if the type points to nonexistent class"""
        correct_config["catalog"]["boats"]["type"] = "kedro.io.CSVDatasetInvalid"

        with pytest.raises(DatasetError) as exc_info:
            DataCatalog.from_config(**correct_config)

        error_message = str(exc_info.value)

        assert "Dataset 'CSVDatasetInvalid' not found" in error_message

    def test_config_invalid_dataset(self, correct_config):
        """Check the error if the type points to invalid class"""
        correct_config["catalog"]["boats"]["type"] = "DataCatalog"
        pattern = (
            "An exception occurred when parsing config for dataset 'boats':\n"
            "Dataset type 'kedro.io.data_catalog.DataCatalog' is invalid: "
            "all dataset types must extend 'AbstractDataset'"
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            DataCatalog.from_config(**correct_config)

    def test_config_invalid_arguments(self, correct_config):
        """Check the error if the dataset config contains invalid arguments"""
        correct_config["catalog"]["boats"]["save_and_load_args"] = False
        pattern = (
            r"Dataset 'boats' must only contain arguments valid for "
            r"the constructor of '.*CSVDataset'"
        )
        with pytest.raises(DatasetError, match=pattern):
            DataCatalog.from_config(**correct_config)

    def test_config_invalid_dataset_config(self, correct_config):
        correct_config["catalog"]["invalid_entry"] = "some string"
        pattern = (
            "Catalog entry 'invalid_entry' is not a valid dataset configuration. "
            "\nHint: If this catalog entry is intended for variable interpolation, "
            "make sure that the key is preceded by an underscore."
        )
        with pytest.raises(DatasetError, match=pattern):
            DataCatalog.from_config(**correct_config)

    def test_empty_config(self):
        """Test empty config"""
        assert DataCatalog.from_config(None)

    def test_config_invalid_class_path_format(self, correct_config):
        """Check the error if the dataset type has an invalid format causing ValueError"""
        # An invalid type path that doesn't include a dot or is otherwise malformed
        correct_config["catalog"]["boats"]["type"] = "InvalidFormatNoDot"

        with pytest.raises(DatasetError) as exc_info:
            DataCatalog.from_config(**correct_config)

        assert "Invalid dataset path: 'InvalidFormatNoDot'" in str(exc_info.value)

    def test_missing_credentials(self, correct_config):
        """Check the error if credentials can't be located"""
        correct_config["catalog"]["cars"]["credentials"] = "missing"
        with pytest.raises(KeyError, match=r"Unable to find credentials \'missing\'"):
            DataCatalog.from_config(**correct_config)

    def test_link_credentials(self, correct_config, mocker):
        """Test credentials being linked to the relevant dataset"""
        mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
        config = deepcopy(correct_config)
        del config["catalog"]["boats"]

        DataCatalog.from_config(**config)

        expected_client_kwargs = correct_config["credentials"]["s3_credentials"]
        mock_client.filesystem.assert_called_with("s3", **expected_client_kwargs)

    def test_nested_credentials(self, correct_config_with_nested_creds, mocker):
        mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
        config = deepcopy(correct_config_with_nested_creds)
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

    def test_missing_nested_credentials(self, correct_config_with_nested_creds):
        del correct_config_with_nested_creds["credentials"]["other_credentials"]
        pattern = "Unable to find credentials 'other_credentials'"
        with pytest.raises(KeyError, match=pattern):
            DataCatalog.from_config(**correct_config_with_nested_creds)

    def test_missing_dependency(self, correct_config, mocker):
        """Test that dependency is missing."""
        pattern = "dependency issue"

        def dummy_load(obj_path, *args, **kwargs):
            if obj_path == "kedro_datasets.pandas.CSVDataset":
                raise AttributeError(pattern)
            if obj_path == "kedro_datasets.pandas.__all__":
                return ["CSVDataset"]

        mocker.patch("kedro.io.core.load_obj", side_effect=dummy_load)
        with pytest.raises(DatasetError, match=pattern):
            DataCatalog.from_config(**correct_config)

    def test_idempotent_catalog(self, correct_config):
        """Test that data catalog instantiations are idempotent"""
        _ = DataCatalog.from_config(**correct_config)
        catalog = DataCatalog.from_config(**correct_config)
        assert catalog

    def test_error_dataset_init(self, bad_config):
        """Check the error when trying to instantiate erroneous dataset"""
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
    def test_bad_confirm(self, correct_config, dataset_name, pattern):
        """Test confirming non existent dataset or the one that
        does not have `confirm` method"""
        data_catalog = DataCatalog.from_config(**correct_config)
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            data_catalog.confirm(dataset_name)


class TestDataCatalogVersioned:
    def test_from_correct_config_versioned(self, correct_config, dummy_dataframe):
        """Test load and save of versioned datasets from config"""
        correct_config["catalog"]["boats"]["versioned"] = True

        # Decompose `generate_timestamp` to keep `current_ts` reference.
        current_ts = datetime.now(tz=timezone.utc)
        fmt = (
            "{d.year:04d}-{d.month:02d}-{d.day:02d}T{d.hour:02d}"
            ".{d.minute:02d}.{d.second:02d}.{ms:03d}Z"
        )
        version = fmt.format(d=current_ts, ms=current_ts.microsecond // 1000)

        catalog = DataCatalog.from_config(
            **correct_config,
            load_versions={"boats": version},
            save_version=version,
        )

        catalog.save("boats", dummy_dataframe)
        path = Path(correct_config["catalog"]["boats"]["filepath"])
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
    def test_from_correct_config_versioned_warn(
        self, caplog, correct_config, versioned
    ):
        """Check the warning if `version` attribute was added
        to the dataset config"""
        correct_config["catalog"]["boats"]["versioned"] = versioned
        correct_config["catalog"]["boats"]["version"] = True
        DataCatalog.from_config(**correct_config)
        log_record = caplog.records[0]
        expected_log_message = (
            "'version' attribute removed from dataset configuration since it "
            "is a reserved word and cannot be directly specified"
        )
        assert log_record.levelname == "WARNING"
        assert expected_log_message in log_record.message

    def test_from_correct_config_load_versions_warn(self, correct_config):
        correct_config["catalog"]["boats"]["versioned"] = True
        version = generate_timestamp()
        load_version = {"non-boat": version}
        pattern = r"\'load_versions\' keys \[non-boat\] are not found in the catalog\."
        with pytest.raises(DatasetNotFoundError, match=pattern):
            DataCatalog.from_config(**correct_config, load_versions=load_version)

    def test_compare_tracking_and_other_dataset_versioned(
        self, correct_config_with_tracking_ds, dummy_dataframe
    ):
        """Test saving of tracking datasets from config results in the same
        save version as other versioned datasets."""

        catalog = DataCatalog.from_config(**correct_config_with_tracking_ds)

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

    def test_load_version(self, correct_config, dummy_dataframe, mocker):
        """Test load versioned datasets from config"""
        new_dataframe = pd.DataFrame({"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]})
        correct_config["catalog"]["boats"]["versioned"] = True
        mocker.patch(
            "kedro.io.data_catalog.generate_timestamp", side_effect=["first", "second"]
        )

        # save first version of the dataset
        catalog = DataCatalog.from_config(**correct_config)
        catalog.save("boats", dummy_dataframe)

        # save second version of the dataset
        catalog = DataCatalog.from_config(**correct_config)
        catalog.save("boats", new_dataframe)

        assert_frame_equal(catalog.load("boats", version="first"), dummy_dataframe)
        assert_frame_equal(catalog.load("boats", version="second"), new_dataframe)
        assert_frame_equal(catalog.load("boats"), new_dataframe)

    def test_load_version_on_unversioned_dataset(
        self, correct_config, dummy_dataframe, mocker
    ):
        mocker.patch("kedro.io.data_catalog.generate_timestamp", return_value="first")

        catalog = DataCatalog.from_config(**correct_config)
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
        versioned_dataset = CSVDataset(filepath="s3://bucket/file.csv", version=version)
        pattern = re.escape(
            f"Did not find any versions for {versioned_dataset}. "
            f"This could be due to insufficient permission."
        )
        with pytest.raises(DatasetError, match=pattern):
            versioned_dataset.load()

    def test_redefine_save_version_via_catalog(self, correct_config, dataset_versioned):
        """Test redefining save version when it is already set"""
        # Version is set automatically for the catalog
        catalog = DataCatalog.from_config(**correct_config)
        with pytest.raises(VersionAlreadyExistsError):
            catalog.add("ds_versioned", dataset_versioned)

        # Version is set manually for the catalog
        correct_config["catalog"]["boats"]["versioned"] = True
        catalog = DataCatalog.from_config(**correct_config)
        with pytest.raises(VersionAlreadyExistsError):
            catalog.add("ds_versioned", dataset_versioned)

    def test_set_load_and_save_versions(self, correct_config, dataset_versioned):
        """Test setting load and save versions for catalog based on dataset's versions provided"""
        catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})

        assert catalog._load_versions["ds_versioned"] == dataset_versioned._version.load
        assert catalog._save_version == dataset_versioned._version.save

    def test_set_same_versions(self, correct_config, dataset_versioned):
        """Test setting the same load and save versions for catalog based on dataset's versions provided"""
        catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})
        catalog.add("ds_same_versions", dataset_versioned)

        assert catalog._load_versions["ds_versioned"] == dataset_versioned._version.load
        assert catalog._save_version == dataset_versioned._version.save

    def test_redefine_load_version(self, correct_config, dataset_versioned):
        """Test redefining save version when it is already set"""
        catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})
        dataset_versioned._version = Version(
            load="another_load_version.csv",
            save="test_save_version.csv",
        )
        catalog.add("ds_same_versions", dataset_versioned)

        assert (
            catalog._load_versions["ds_same_versions"]
            == dataset_versioned._version.load
        )
        assert catalog._load_versions["ds_versioned"] == "test_load_version.csv"
        assert catalog._save_version == dataset_versioned._version.save

    def test_redefine_save_version(self, correct_config, dataset_versioned):
        """Test redefining save version when it is already set"""
        catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})
        dataset_versioned._version = Version(
            load="another_load_version.csv",
            save="another_save_version.csv",
        )
        with pytest.raises(VersionAlreadyExistsError):
            catalog.add("ds_same_versions", dataset_versioned)

    def test_redefine_save_version_with_cached_dataset(
        self, correct_config, cached_dataset_versioned
    ):
        """Test redefining load and save version with CachedDataset"""
        catalog = DataCatalog.from_config(**correct_config)

        # Redefining save version fails
        with pytest.raises(VersionAlreadyExistsError):
            catalog.add("cached_dataset_versioned", cached_dataset_versioned)

        # Redefining load version passes
        cached_dataset_versioned._dataset._version = Version(
            load="test_load_version.csv", save=None
        )
        catalog.add("cached_dataset_versioned", cached_dataset_versioned)

        assert (
            catalog._load_versions["cached_dataset_versioned"]
            == "test_load_version.csv"
        )
        assert catalog._save_version


class TestDataCatalogDatasetFactories:
    def test_match_added_to_datasets_on_get(self, config_with_dataset_factories):
        """Check that the datasets that match patterns are only added when fetched"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories)
        assert "{brand}_cars" not in catalog._datasets
        assert "tesla_cars" not in catalog._datasets
        assert "{brand}_cars" in catalog.config_resolver._dataset_patterns

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
        assert "audi_cars" not in catalog.config_resolver._dataset_patterns
        assert "{brand}_cars" in catalog.config_resolver._dataset_patterns

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
            "{user_default}",
        ]
        assert catalog.config_resolver.list_patterns() == sorted_keys_expected

    def test_multiple_catch_all_patterns_not_allowed(
        self, config_with_dataset_factories
    ):
        """Check that multiple catch-all patterns are not allowed"""
        config_with_dataset_factories["catalog"]["{default1}"] = {
            "filepath": "data/01_raw/{default1}.csv",
            "type": "pandas.CSVDataset",
        }
        config_with_dataset_factories["catalog"]["{default2}"] = {
            "filepath": "data/01_raw/{default2}.xlsx",
            "type": "pandas.ExcelDataset",
        }

        with pytest.raises(
            DatasetError, match="Multiple catch-all patterns found in the catalog"
        ):
            DataCatalog.from_config(**config_with_dataset_factories)

    def test_sorting_order_with_other_dataset_through_extra_pattern(
        self, config_with_dataset_factories_only_patterns_no_default
    ):
        """Check that the sorted order of the patterns is correct according to parsing rules when a default dataset
        is added through extra patterns (this would happen via the runner) and user default is not present"""
        extra_dataset_patterns = {
            "{default}": {"type": "MemoryDataset"},
            "{another}#csv": {
                "type": "pandas.CSVDataset",
                "filepath": "data/{another}.csv",
            },
        }
        catalog = DataCatalog.from_config(
            **config_with_dataset_factories_only_patterns_no_default
        )
        catalog_with_default = catalog.shallow_copy(
            extra_dataset_patterns=extra_dataset_patterns
        )
        sorted_keys_expected = [
            "{country}_companies",
            "{namespace}_{dataset}",
            "{dataset}s",
            "{another}#csv",
            "{default}",
        ]
        assert (
            catalog_with_default.config_resolver.list_patterns() == sorted_keys_expected
        )

    def test_user_default_overwrites_runner_default(self):
        """Check that the user default overwrites the runner default when both are present"""
        catalog_config = {
            "{dataset}s": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{dataset}s.csv",
            },
            "{a_default}": {
                "type": "pandas.ExcelDataset",
                "filepath": "data/01_raw/{a_default}.xlsx",
            },
        }
        catalog = DataCatalog.from_config(catalog_config)
        extra_dataset_patterns = {
            "{default}": {"type": "MemoryDataset"},
            "{another}#csv": {
                "type": "pandas.CSVDataset",
                "filepath": "data/{another}.csv",
            },
        }
        catalog_with_runner_default = catalog.shallow_copy(
            extra_dataset_patterns=extra_dataset_patterns
        )
        sorted_keys_expected = [
            "{dataset}s",
            "{a_default}",
            "{another}#csv",
            "{default}",
        ]
        assert (
            "{a_default}"
            in catalog_with_runner_default.config_resolver._default_pattern
        )
        assert (
            catalog_with_runner_default.config_resolver.list_patterns()
            == sorted_keys_expected
        )

    def test_default_dataset(self, config_with_dataset_factories_with_default, caplog):
        """Check that default dataset is used when no other pattern matches"""
        catalog = DataCatalog.from_config(**config_with_dataset_factories_with_default)
        assert "jet@planes" not in catalog._datasets
        jet_dataset = catalog._get_dataset("jet@planes")
        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "Config from the dataset factory pattern '{default_dataset}' "
            "in the catalog will be used to override the default dataset creation for 'jet@planes'"
            in log_record.message
        )
        assert isinstance(jet_dataset, CSVDataset)

    def test_unmatched_key_error_when_parsing_config(
        self, config_with_dataset_factories_bad_pattern
    ):
        """Check error raised when key mentioned in the config is not in pattern name"""
        pattern = (
            "Incorrect dataset configuration provided. Keys used in the configuration {'{brand}'} "
            "should present in the dataset factory pattern name {type}@planes."
        )
        with pytest.raises(DatasetError, match=re.escape(pattern)):
            _ = DataCatalog.from_config(**config_with_dataset_factories_bad_pattern)

    def test_factory_config_versioned(
        self, config_with_dataset_factories, filepath, dummy_dataframe
    ):
        """Test load and save of versioned datasets from config"""
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
