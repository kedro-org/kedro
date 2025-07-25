import logging
import re
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
from kedro_datasets.pandas import CSVDataset, ParquetDataset
from pandas.testing import assert_frame_equal

from kedro.io import (
    CachedDataset,
    CatalogConfigResolver,
    DataCatalog,
    DatasetError,
    DatasetNotFoundError,
    MemoryDataset,
)
from kedro.io.core import (
    _DEFAULT_PACKAGES,
    VERSION_FORMAT,
    AbstractDataset,
    Version,
    VersionAlreadyExistsError,
    generate_timestamp,
    parse_dataset_definition,
)


@pytest.fixture
def data_catalog(dataset):
    return DataCatalog(datasets={"test": dataset})


@pytest.fixture
def memory_catalog():
    ds1 = MemoryDataset({"data": 42})
    ds2 = MemoryDataset([1, 2, 3, 4, 5])
    return DataCatalog({"ds1": ds1, "ds2": ds2})


@pytest.fixture
def conflicting_parameters():
    return {"ds1": 0, "ds3": 1}


@pytest.fixture
def multi_catalog():
    csv_1 = CSVDataset(filepath="abc.csv")
    csv_2 = CSVDataset(filepath="def.csv")
    parq = ParquetDataset(filepath="xyz.parq")
    return DataCatalog({"abc": csv_1, "def": csv_2, "xyz": parq})


@pytest.fixture
def data_catalog_from_config(correct_config):
    return DataCatalog.from_config(**correct_config)


class NonExistentDataset(AbstractDataset):
    def __init__(self):
        pass

    def _load(self):
        pass

    def _save(self, data):
        pass

    def _describe(self):
        return {}


class TestDataCatalog:
    def test_save_and_load(self, data_catalog, dummy_dataframe):
        """Test saving and reloading the dataset"""
        data_catalog.save("test", dummy_dataframe)
        reloaded_df = data_catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_add_save_and_load(self, dataset, dummy_dataframe):
        """Test adding and then saving and reloading the dataset"""
        catalog = DataCatalog(datasets={})
        catalog["test"] = dataset
        catalog.save("test", dummy_dataframe)
        reloaded_df = catalog.load("test")

        assert_frame_equal(reloaded_df, dummy_dataframe)

    def test_load_error(self, data_catalog):
        """Check the error when attempting to load a dataset
        from nonexistent source"""
        pattern = r"Failed while loading data from dataset kedro_datasets.pandas.csv_dataset.CSVDataset"
        with pytest.raises(DatasetError, match=pattern):
            data_catalog.load("test")

    def test_add_dataset_twice(self, data_catalog, dataset, caplog):
        """Check the warning when attempting to add the dataset twice"""
        data_catalog["test"] = dataset
        # check the logs
        log_messages = [record.getMessage() for record in caplog.records]
        expected_msg = "Replacing dataset 'test'"
        assert any(expected_msg in log_message for log_message in log_messages)

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

    def test_exists(self, data_catalog, dummy_dataframe):
        """Test `exists` method invocation"""
        assert not data_catalog.exists("test")
        data_catalog.save("test", dummy_dataframe)
        assert data_catalog.exists("test")

    def test_exists_not_implemented(self, caplog):
        """Test calling `exists` on the dataset, which didn't implement it"""
        catalog = DataCatalog(datasets={"test": NonExistentDataset()})
        result = catalog.exists("test")

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "'exists()' not implemented for 'NonExistentDataset'. "
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
        pattern = r"Dataset \'text\' not found in the catalog"
        with pytest.raises(DatasetNotFoundError, match=pattern) as e:
            data_catalog.release("text")
        assert "did you mean" not in str(e.value)

    def test_multi_catalog_keys(self, multi_catalog):
        """Test data catalog which contains multiple datasets"""
        entries = multi_catalog.keys()
        assert "abc" in entries
        assert "xyz" in entries

    @pytest.mark.parametrize(
        "pattern,expected",
        [
            ("^a", ["abc"]),
            ("a|x", ["abc", "xyz"]),
            ("^(?!(a|d|x))", []),
            ("def", ["def"]),
            ("ghi", []),
            ("", ["abc", "def", "xyz"]),
        ],
    )
    def test_multi_catalog_filter_regex(self, multi_catalog, pattern, expected):
        """Test that regex patterns filter datasets accordingly"""
        assert multi_catalog.filter(name_regex=pattern) == expected

    def test_multi_catalog_filter_bad_regex(self, multi_catalog):
        """Test that bad regex is caught accordingly"""
        pattern = r"missing \)\, unterminated subpattern at position"
        with pytest.raises(re.error, match=pattern):
            multi_catalog.filter("((")

    @pytest.mark.parametrize(
        "name_regex,type_regex,expected",
        [
            (re.compile("^a"), None, ["abc"]),
            (re.compile("^A"), None, []),
            (re.compile("^A", flags=re.IGNORECASE), None, ["abc"]),
            ("a|x", None, ["abc", "xyz"]),
            ("a|d|x", None, ["abc", "def", "xyz"]),
            ("a|d|x", "CSVDataset", ["abc", "def"]),
            ("a|d|x", "kedro_datasets", ["abc", "def", "xyz"]),
            (None, "ParquetDataset", ["xyz"]),
            ("^(?!(a|d|x))", None, []),
            ("def", None, ["def"]),
            (None, None, ["abc", "def", "xyz"]),
            ("a|d|x", "no_such_dataset", []),
        ],
    )
    def test_catalog_filter_regex(
        self, multi_catalog, name_regex, type_regex, expected
    ):
        """Test that regex patterns filter materialized datasets accordingly"""
        assert (
            multi_catalog.filter(name_regex=name_regex, type_regex=type_regex)
            == expected
        )

    @pytest.mark.parametrize(
        "name_regex,type_regex,by_type,expected",
        [
            ("b|m", None, None, ["boats", "materialized"]),
            (None, None, None, ["boats", "cars", "materialized"]),
            (None, "CSVDataset", None, ["boats", "cars"]),
            (None, "ParquetDataset", None, ["materialized"]),
            ("b|c", "ParquetDataset", None, []),
            (None, None, ParquetDataset, ["materialized"]),
            (
                None,
                None,
                [CSVDataset, ParquetDataset],
                ["boats", "cars", "materialized"],
            ),
            (None, "ParquetDataset", [CSVDataset, ParquetDataset], ["materialized"]),
            ("b|m", None, [CSVDataset, ParquetDataset], ["boats", "materialized"]),
        ],
    )
    def test_from_config_catalog_filter_regex(
        self, data_catalog_from_config, name_regex, type_regex, by_type, expected
    ):
        """Test that regex patterns filter lazy and materialized datasets accordingly"""
        data_catalog_from_config["materialized"] = ParquetDataset(filepath="xyz.parq")
        assert (
            data_catalog_from_config.filter(
                name_regex=name_regex, type_regex=type_regex, by_type=by_type
            )
            == expected
        )

    def test_datasets_on_init(self, data_catalog_from_config):
        """Check datasets are loaded correctly on construction"""
        assert isinstance(data_catalog_from_config.get("boats"), CSVDataset)
        assert isinstance(data_catalog_from_config.get("cars"), CSVDataset)

    def test_datasets_on_add(self, data_catalog_from_config):
        """Check datasets are updated correctly after adding"""
        data_catalog_from_config["new_dataset"] = CSVDataset(filepath="some_path")
        assert isinstance(data_catalog_from_config.get("new_dataset"), CSVDataset)
        assert isinstance(data_catalog_from_config.get("boats"), CSVDataset)

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

    def test_adding_raw_data(self, dummy_dataframe, dataset):
        """Test catalog initialisation with raw data"""
        catalog = DataCatalog(datasets={"ds": dataset})
        catalog["df"] = dummy_dataframe

        assert "ds" in catalog
        assert "df" in catalog
        assert isinstance(catalog["ds"], CSVDataset)
        assert isinstance(catalog["df"], MemoryDataset)

    def test_init_warns_and_removes_conflicting_datasets_from_config(self, caplog):
        # Prepare conflicting dataset name
        config_resolver = CatalogConfigResolver(
            {
                "existing_ds": {"type": "MemoryDataset", "data": "from_config"},
                "new_ds": {"type": "MemoryDataset", "data": "new_data"},
            }
        )

        datasets = {"existing_ds": MemoryDataset(data="from_datasets")}

        with caplog.at_level(logging.WARNING):
            catalog = DataCatalog(datasets=datasets, config_resolver=config_resolver)

        # 'existing_ds' should not be added from config
        assert "Cannot register dataset 'existing_ds' from config" in caplog.text
        assert "existing_ds" in catalog
        assert catalog.load("existing_ds") == "from_datasets"

        # 'new_ds' should be added from config
        assert "new_ds" in catalog
        assert catalog.load("new_ds") == "new_data"

        # Config should no longer contain the skipped dataset
        assert "existing_ds" not in config_resolver.config
        assert "new_ds" in config_resolver.config

    def test_repr(self, data_catalog_from_config):
        assert data_catalog_from_config.__repr__() == str(data_catalog_from_config)

    def test_repr_no_type_found(self, data_catalog_from_config):
        del data_catalog_from_config._lazy_datasets["boats"].config["type"]
        pattern = "'type'"
        with pytest.raises(KeyError, match=re.escape(pattern)):
            _ = str(data_catalog_from_config)

    def test_missing_keys_from_load_versions(self, correct_config):
        """Test load versions include keys missing in the catalog"""
        pattern = "'load_versions' keys [version] are not found in the catalog."
        with pytest.raises(DatasetNotFoundError, match=re.escape(pattern)):
            DataCatalog.from_config(
                **correct_config, load_versions={"version": "test_version"}
            )

    def test_get_dataset_matches_runtime_pattern(self, data_catalog):
        """Test get_dataset() when dataset is not in the catalog but default pattern matches"""
        match_pattern_ds = "match_pattern_ds"
        assert match_pattern_ds not in data_catalog

        ds = data_catalog.get(match_pattern_ds, fallback_to_runtime_pattern=False)
        assert ds is None

        ds = data_catalog.get(match_pattern_ds, fallback_to_runtime_pattern=True)
        assert isinstance(ds, MemoryDataset)

    def test_release(self, data_catalog):
        """Test release is called without errors"""
        data_catalog.release("test")

    def test_dataset_property(self, data_catalog_from_config):
        """Test _dataset attribute returns the same result as dataset property"""
        # Catalog includes only lazy dataset, we get boats dataset to materialize it
        _ = data_catalog_from_config["boats"]

        assert "boats" in data_catalog_from_config._datasets
        assert "cars" not in data_catalog_from_config._datasets

        _ = data_catalog_from_config["cars"]
        assert "cars" in data_catalog_from_config._datasets

    def test_catalogs_eq(self, data_catalog_from_config):
        expected_catalog = data_catalog_from_config
        assert data_catalog_from_config == expected_catalog

        data_catalog_copy = deepcopy(data_catalog_from_config)
        assert not data_catalog_copy == expected_catalog

    def test_get_returns_none_dataset(self):
        catalog = DataCatalog(datasets={})
        catalog._datasets["bad_ds"] = None
        assert catalog.get("bad_ds") is None

    def test_get_missing_dataset(self):
        catalog = DataCatalog(datasets={})
        assert catalog.get("missing_ds") is None

    def test_get_type_missing_dataset(self):
        catalog = DataCatalog(datasets={})
        assert catalog.get_type("missing_ds") is None

    class TestDataCatalogToConfig:
        def test_to_config(self, correct_config_versioned, dataset, filepath):
            """Test dumping catalog config"""
            config = correct_config_versioned["catalog"]
            credentials = correct_config_versioned["credentials"]
            catalog = DataCatalog.from_config(config, credentials)
            catalog["resolved_ds"] = dataset
            catalog["memory_ds"] = [1, 2, 3]
            catalog["params:a.b"] = {"abc": "def"}
            # Materialize cached_ds
            _ = catalog["cached_ds"]

            version = Version(
                load="fake_load_version.csv",  # load exact version
                save=None,  # save to exact version
            )
            versioned_dataset = CSVDataset(
                filepath="shuttles.csv", version=version, metadata=[1, 2, 3]
            )
            cached_versioned_dataset = CachedDataset(dataset=versioned_dataset)
            catalog["cached_versioned_dataset"] = cached_versioned_dataset

            catalog_config, catalog_credentials, load_version, save_version = (
                catalog.to_config()
            )

            expected_config = {
                "resolved_ds": {
                    "type": "kedro_datasets.pandas.csv_dataset.CSVDataset",
                    "filepath": filepath,
                    "save_args": {"index": False},
                    "load_args": None,
                    "credentials": None,
                    "fs_args": None,
                },
                "cached_versioned_dataset": {
                    "type": "kedro.io.cached_dataset.CachedDataset",
                    "copy_mode": None,
                    "versioned": True,
                    "dataset": {
                        "type": "kedro_datasets.pandas.csv_dataset.CSVDataset",
                        "filepath": "shuttles.csv",
                        "load_args": None,
                        "save_args": None,
                        "credentials": None,
                        "fs_args": None,
                    },
                },
            }
            expected_config.update(config)
            expected_config.pop("parameters", None)

            assert catalog_config == expected_config
            assert catalog_credentials == credentials
            # Load version is set only for cached_versioned_dataset
            assert catalog._load_versions == {
                "cached_versioned_dataset": "fake_load_version.csv"
            }
            # Save version is not None and  set to default
            assert catalog._save_version

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
                DataCatalog.from_config(**correct_config).get("boats")

        def test_config_relative_import(self, correct_config):
            """Check the error if the type points to a relative import"""
            correct_config["catalog"]["boats"]["type"] = ".CSVDatasetInvalid"

            pattern = "'type' class path does not support relative paths"
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                DataCatalog.from_config(**correct_config).get("boats")

        def test_config_import_kedro_datasets(self, correct_config, mocker):
            """Test kedro_datasets default path to the dataset class"""
            # Spy _load_obj because kedro_datasets is not installed and we can't import it.

            import kedro.io.core

            spy = mocker.spy(kedro.io.core, "_load_obj")
            parse_dataset_definition(correct_config["catalog"]["boats"])
            for prefix, call_args in zip(_DEFAULT_PACKAGES, spy.call_args_list):
                assert call_args.args[0] == f"{prefix}pandas.CSVDataset"

        def test_config_missing_class(self, correct_config):
            """Check the error if the type points to nonexistent class"""
            correct_config["catalog"]["boats"]["type"] = "kedro.io.CSVDatasetInvalid"

            with pytest.raises(DatasetError) as exc_info:
                DataCatalog.from_config(**correct_config).get("boats")

            error_message = str(exc_info.value)

            assert "Dataset 'CSVDatasetInvalid' not found" in error_message

        def test_config_invalid_class_path_format(self, correct_config):
            """Check the error if the dataset type has an invalid format causing ValueError"""
            # An invalid type path that doesn't include a dot or is otherwise malformed
            correct_config["catalog"]["boats"]["type"] = "InvalidFormatNoDot"

            with pytest.raises(DatasetError) as exc_info:
                DataCatalog.from_config(**correct_config).get("boats")

            assert "Invalid dataset path: 'InvalidFormatNoDot'" in str(exc_info.value)

        def test_config_invalid_dataset(self, correct_config):
            """Check the error if the type points to invalid class"""
            correct_config["catalog"]["boats"]["type"] = "DataCatalog"
            pattern = (
                "An exception occurred when parsing config for dataset 'boats':\n"
                "Dataset type 'kedro.io.data_catalog.DataCatalog' is invalid: "
                "all dataset types must extend 'AbstractDataset'"
            )
            with pytest.raises(DatasetError, match=re.escape(pattern)):
                DataCatalog.from_config(**correct_config).get("boats")

        def test_config_invalid_arguments(self, correct_config):
            """Check the error if the dataset config contains invalid arguments"""
            correct_config["catalog"]["boats"]["save_and_load_args"] = False
            pattern = (
                r"Dataset 'boats' must only contain arguments valid for "
                r"the constructor of '.*CSVDataset'"
            )
            with pytest.raises(DatasetError, match=pattern):
                DataCatalog.from_config(**correct_config).get("boats")

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
            assert len(DataCatalog.from_config(None)) == 0

        def test_missing_credentials(self, correct_config):
            """Check the error if credentials can't be located"""
            correct_config["catalog"]["cars"]["credentials"] = "missing"
            with pytest.raises(
                KeyError, match=r"Unable to find credentials \'missing\'"
            ):
                DataCatalog.from_config(**correct_config)

        def test_link_credentials(self, correct_config, mocker):
            """Test credentials being linked to the relevant dataset"""
            mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
            config = deepcopy(correct_config)
            del config["catalog"]["boats"]

            DataCatalog.from_config(**config).get("cars")

            expected_client_kwargs = correct_config["credentials"]["s3_credentials"]
            mock_client.filesystem.assert_called_with("s3", **expected_client_kwargs)

        def test_nested_credentials(self, correct_config_with_nested_creds, mocker):
            mock_client = mocker.patch("kedro_datasets.pandas.csv_dataset.fsspec")
            config = deepcopy(correct_config_with_nested_creds)
            del config["catalog"]["boats"]
            DataCatalog.from_config(**config).get("cars")

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
            mock_client.filesystem.assert_called_once_with(
                "s3", **expected_client_kwargs
            )

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
                DataCatalog.from_config(**correct_config).get("boats")

        def test_idempotent_catalog(self, correct_config):
            """Test that data catalog instantiations are idempotent"""
            _ = DataCatalog.from_config(**correct_config)
            catalog = DataCatalog.from_config(**correct_config)
            assert catalog

        def test_error_dataset_init(self, bad_config):
            """Check the error when trying to instantiate erroneous dataset"""
            pattern = r"An exception occurred when parsing config for dataset 'bad'"
            with pytest.raises(DatasetError, match=pattern):
                DataCatalog.from_config(bad_config, None).get("bad")

        def test_validate_dataset_config(self):
            """Test _validate_dataset_config raises error when wrong dataset config type is passed"""
            pattern = (
                "Catalog entry 'bad' is not a valid dataset configuration. \n"
                "Hint: If this catalog entry is intended for variable interpolation, make sure that the key is preceded by an underscore."
            )
            with pytest.raises(DatasetError, match=pattern):
                DataCatalog._validate_dataset_config(
                    ds_name="bad", ds_config="not_dict"
                )

        # TODO: revert commenting when we drop python3.9 support and move to kedro-datasets>=8.0.0
        # Currently the test is failing because it requires kedro-datasets version compatible with kedro 1.0
        # def test_confirm(self, tmp_path, caplog, mocker):
        #     """Confirm the dataset"""
        #     with caplog.at_level(logging.INFO):
        #         mock_confirm = mocker.patch(
        #             "kedro_datasets.partitions.IncrementalDataset.confirm"
        #         )
        #         catalog = {
        #             "ds_to_confirm": {
        #                 "type": "kedro_datasets.partitions.IncrementalDataset",
        #                 "dataset": "pandas.CSVDataset",
        #                 "path": str(tmp_path),
        #             }
        #         }
        #         data_catalog = DataCatalog.from_config(catalog=catalog)
        #         data_catalog.confirm("ds_to_confirm")
        #         assert caplog.record_tuples == [
        #             (
        #                 "kedro.io.data_catalog",
        #                 logging.INFO,
        #                 "Confirming dataset 'ds_to_confirm'",
        #             )
        #         ]
        #         mock_confirm.assert_called_once_with()

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

        def test_iteration(self, correct_config):
            """Test iterate through keys, values and items."""
            data_catalog = DataCatalog.from_config(**correct_config)

            for ds_name_cat, ds_name_config in zip(
                data_catalog, correct_config["catalog"]
            ):
                assert ds_name_cat == ds_name_config

            for ds_name_cat, ds_name_config in zip(
                data_catalog.keys(), correct_config["catalog"]
            ):
                assert ds_name_cat == ds_name_config

            for ds in data_catalog.values():
                assert isinstance(ds, CSVDataset)

            for ds_name, ds in data_catalog.items():
                assert isinstance(ds, CSVDataset)
                assert ds_name in correct_config["catalog"]

        def test_getitem_setitem(self, correct_config):
            """Test get and set item."""
            data_catalog = DataCatalog.from_config(**correct_config)
            data_catalog["test"] = 123
            assert isinstance(data_catalog["test"], MemoryDataset)

        def test_ipython_key_completions(self, correct_config):
            data_catalog = DataCatalog.from_config(**correct_config)
            assert data_catalog._ipython_key_completions_() == list(
                correct_config["catalog"].keys()
            )

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
                catalog["boats"].resolve_load_version(),
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
            DataCatalog.from_config(**correct_config).get("boats")
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
            pattern = (
                r"\'load_versions\' keys \[non-boat\] are not found in the catalog\."
            )
            with pytest.raises(DatasetNotFoundError, match=pattern):
                DataCatalog.from_config(**correct_config, load_versions=load_version)

        def test_load_version(self, correct_config, dummy_dataframe, mocker):
            """Test load versioned datasets from config"""
            new_dataframe = pd.DataFrame(
                {"col1": [0, 0], "col2": [0, 0], "col3": [0, 0]}
            )
            correct_config["catalog"]["boats"]["versioned"] = True
            mocker.patch(
                "kedro.io.data_catalog.generate_timestamp",
                side_effect=["first", "second"],
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
            mocker.patch(
                "kedro.io.data_catalog.generate_timestamp", return_value="first"
            )

            catalog = DataCatalog.from_config(**correct_config)
            catalog.save("boats", dummy_dataframe)

            with pytest.raises(DatasetError):
                catalog.load("boats", version="first")

        def test_redefine_save_version_via_catalog(
            self, correct_config, dataset_versioned
        ):
            """Test redefining save version when it is already set"""
            # Version is set automatically for the catalog
            catalog = DataCatalog.from_config(**correct_config)
            with pytest.raises(VersionAlreadyExistsError):
                catalog["ds_versioned"] = dataset_versioned

            # Version is set manually for the catalog
            correct_config["catalog"]["boats"]["versioned"] = True
            catalog = DataCatalog.from_config(**correct_config)
            with pytest.raises(VersionAlreadyExistsError):
                catalog["ds_versioned"] = dataset_versioned

        def test_set_load_and_save_versions(self, correct_config, dataset_versioned):
            """Test setting load and save versions for catalog based on dataset's versions provided"""
            catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})

            assert (
                catalog._load_versions["ds_versioned"]
                == dataset_versioned._version.load
            )
            assert catalog._save_version == dataset_versioned._version.save

        def test_set_same_versions(self, correct_config, dataset_versioned):
            """Test setting the same load and save versions for catalog based on dataset's versions provided"""
            catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})
            catalog["ds_same_versions"] = dataset_versioned

            assert (
                catalog._load_versions["ds_versioned"]
                == dataset_versioned._version.load
            )
            assert catalog._save_version == dataset_versioned._version.save

        def test_redefine_load_version(self, correct_config, dataset_versioned):
            """Test redefining save version when it is already set"""
            catalog = DataCatalog(datasets={"ds_versioned": dataset_versioned})
            dataset_versioned._version = Version(
                load="another_load_version.csv",
                save="test_save_version.csv",
            )
            catalog["ds_same_versions"] = dataset_versioned

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
                catalog["ds_same_versions"] = dataset_versioned

        def test_redefine_save_version_with_cached_dataset(
            self, correct_config, cached_dataset_versioned
        ):
            """Test redefining load and save version with CachedDataset"""
            catalog = DataCatalog.from_config(**correct_config)

            # Redefining save version fails
            with pytest.raises(VersionAlreadyExistsError):
                catalog["cached_dataset_versioned"] = cached_dataset_versioned

            # Redefining load version passes
            cached_dataset_versioned._dataset._version = Version(
                load="test_load_version.csv", save=None
            )
            catalog["cached_dataset_versioned"] = cached_dataset_versioned

            assert (
                catalog._load_versions["cached_dataset_versioned"]
                == "test_load_version.csv"
            )
            assert catalog._save_version

        def test_setitem_replaces_dataset_and_clears_state(self):
            config_resolver = CatalogConfigResolver(
                {"my_dataset": {"type": "MemoryDataset", "data": "from_config"}}
            )
            catalog = DataCatalog(config_resolver=config_resolver)
            catalog._load_versions = {"my_dataset": "old_version"}

            catalog["my_dataset"] = MemoryDataset(data="new_data")

            assert "my_dataset" in catalog._datasets
            assert catalog.load("my_dataset") == "new_data"
            assert "my_dataset" not in catalog._lazy_datasets
            assert "my_dataset" not in catalog._config_resolver.config
            assert "my_dataset" not in catalog._load_versions
