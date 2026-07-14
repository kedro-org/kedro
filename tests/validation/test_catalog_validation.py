"""Integration tests for the DataCatalog validation funnel (KEP-7 v2).

These tests exercise the catalog-native ``validator:`` key end-to-end: spec
capture from config, the single load/save validation funnel, enablement
controls, factory patterns, round-tripping and pickling.
"""

from __future__ import annotations

import logging
import pickle

import pandas as pd
import pandera.pandas as pa
import pytest

from kedro.io import AbstractDataset, DataCatalog
from kedro.validation import (
    DataValidationError,
    ValidationConfigurationError,
)

_MODULE = "tests.validation.test_catalog_validation"


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(unique=True)
    company_rating: float = pa.Field(ge=0)

    class Config:
        strict = False


class CountingValidator:
    """Counts validate calls; pass-through."""

    def __init__(self):
        self.calls = 0

    def validate(self, data):
        self.calls += 1
        return data


class UppercasingValidator:
    """Transforming validator: uppercases the 'name' column."""

    def validate(self, data):
        data = data.copy()
        data["name"] = data["name"].str.upper()
        return data


@pytest.fixture
def valid_df():
    return pd.DataFrame({"id": [1, 2, 3], "company_rating": [0.5, 2.0, 10.0]})


@pytest.fixture
def invalid_df():
    return pd.DataFrame({"id": [1, 1, 3], "company_rating": [-0.5, -1.2, 1.0]})


@pytest.fixture
def csv_path(tmp_path):
    return tmp_path / "companies.csv"


def make_catalog(csv_path, validator=f"{_MODULE}.CompaniesSchema", **kwargs):
    config = {
        "companies": {
            "type": "pandas.CSVDataset",
            "filepath": str(csv_path),
            "validator": validator,
        }
    }
    return DataCatalog.from_config(config, **kwargs)


class TestLoadValidation:
    def test_valid_load_passes(self, csv_path, valid_df):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)

        loaded = catalog.load("companies")
        pd.testing.assert_frame_equal(loaded, valid_df)

    def test_invalid_load_raises_with_dataset_name_and_mode(self, csv_path, invalid_df):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)

        with pytest.raises(DataValidationError) as exc_info:
            catalog.load("companies")

        exc = exc_info.value
        assert exc.dataset_name == "companies"
        assert exc.mode == "load"
        assert exc.failures
        assert "Validation failed for dataset 'companies' on load" in str(exc)

    def test_unresolvable_validator_raises_config_error_on_load(
        self, csv_path, valid_df
    ):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path, validator="definitely_not_installed_pkg.X")

        with pytest.raises(ValidationConfigurationError):
            catalog.load("companies")

    def test_invalid_spec_raises_at_catalog_construction(self, csv_path):
        with pytest.raises(ValidationConfigurationError, match="bogus_key"):
            make_catalog(
                csv_path,
                validator={"class": f"{_MODULE}.CompaniesSchema", "bogus_key": 1},
            )


class TestSaveValidation:
    def test_save_validates_before_write(self, csv_path, invalid_df):
        catalog = make_catalog(csv_path)

        with pytest.raises(DataValidationError) as exc_info:
            catalog.save("companies", invalid_df)

        assert exc_info.value.mode == "save"
        assert exc_info.value.dataset_name == "companies"
        assert not csv_path.exists()

    def test_valid_save_writes(self, csv_path, valid_df):
        catalog = make_catalog(csv_path)
        catalog.save("companies", valid_df)
        assert csv_path.exists()

    def test_transformed_data_flows_to_dataset_on_save(self, tmp_path):
        path = tmp_path / "named.csv"
        config = {
            "named": {
                "type": "pandas.CSVDataset",
                "filepath": str(path),
                "validator": f"{_MODULE}.UppercasingValidator",
            }
        }
        catalog = DataCatalog.from_config(config)
        catalog.save("named", pd.DataFrame({"name": ["alpha", "beta"]}))

        written = pd.read_csv(path)
        assert written["name"].tolist() == ["ALPHA", "BETA"]

    def test_transformed_data_returned_on_load(self, tmp_path):
        path = tmp_path / "named.csv"
        pd.DataFrame({"name": ["alpha"]}).to_csv(path, index=False)
        config = {
            "named": {
                "type": "pandas.CSVDataset",
                "filepath": str(path),
                "validator": {
                    "class": f"{_MODULE}.UppercasingValidator",
                    "on": ["load"],
                },
            }
        }
        catalog = DataCatalog.from_config(config)

        loaded = catalog.load("named")
        assert loaded["name"].tolist() == ["ALPHA"]


class TestModeAndEnablementGating:
    def test_on_save_only_skips_load_validation(self, csv_path, invalid_df):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(
            csv_path,
            validator={"class": f"{_MODULE}.CompaniesSchema", "on": ["save"]},
        )

        loaded = catalog.load("companies")  # must not raise
        pd.testing.assert_frame_equal(loaded, invalid_df)

        with pytest.raises(DataValidationError):
            catalog.save("companies", invalid_df)

    def test_per_dataset_enabled_false_skips_validation(self, csv_path, invalid_df):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(
            csv_path,
            validator={"class": f"{_MODULE}.CompaniesSchema", "enabled": False},
        )

        loaded = catalog.load("companies")
        pd.testing.assert_frame_equal(loaded, invalid_df)

    def test_severity_warn_logs_and_returns_original_data(
        self, csv_path, invalid_df, caplog
    ):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(
            csv_path,
            validator={"class": f"{_MODULE}.CompaniesSchema", "severity": "warn"},
        )

        with caplog.at_level(logging.WARNING, logger="kedro.io.data_catalog"):
            loaded = catalog.load("companies")

        pd.testing.assert_frame_equal(loaded, invalid_df)
        assert "Validation failed for dataset 'companies' on load" in caplog.text

    def test_severity_warn_wraps_non_validation_errors(self, csv_path, caplog):
        # validator blows up with a KeyError (missing column) -> warn + raw data
        df = pd.DataFrame({"unrelated": [1]})
        df.to_csv(csv_path, index=False)
        catalog = make_catalog(
            csv_path,
            validator={
                "class": f"{_MODULE}.UppercasingValidator",
                "severity": "warn",
            },
        )

        with caplog.at_level(logging.WARNING, logger="kedro.io.data_catalog"):
            loaded = catalog.load("companies")

        pd.testing.assert_frame_equal(loaded, df)
        assert "Validation failed for dataset 'companies' on load" in caplog.text

    def test_validation_enabled_false_short_circuits(self, csv_path, invalid_df):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        catalog.validation_enabled = False

        loaded = catalog.load("companies")
        pd.testing.assert_frame_equal(loaded, invalid_df)

    def test_validation_enabled_constructor_arg(self):
        catalog = DataCatalog(validation_enabled=False)
        assert catalog.validation_enabled is False
        assert DataCatalog().validation_enabled is True

    def test_env_var_disables_validation(self, csv_path, invalid_df, monkeypatch):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        assert catalog.validation_enabled is True

        monkeypatch.setenv("KEDRO_DATASET_VALIDATION", "0")
        loaded = catalog.load("companies")
        pd.testing.assert_frame_equal(loaded, invalid_df)

    def test_env_var_enables_validation_over_catalog_flag(
        self, csv_path, invalid_df, monkeypatch
    ):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        catalog.validation_enabled = False

        monkeypatch.setenv("KEDRO_DATASET_VALIDATION", "1")
        with pytest.raises(DataValidationError):
            catalog.load("companies")

    def test_unrecognised_env_var_falls_back_to_catalog_flag(
        self, csv_path, invalid_df, monkeypatch
    ):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)

        monkeypatch.setenv("KEDRO_DATASET_VALIDATION", "banana")
        with pytest.raises(DataValidationError):
            catalog.load("companies")


class TestSkipLoadAfterSave:
    def _counting_catalog(self, csv_path, skip_load_after_save):
        return make_catalog(
            csv_path,
            validator={
                "class": f"{_MODULE}.CountingValidator",
                "skip_load_after_save": skip_load_after_save,
            },
        )

    def test_save_then_load_validates_once(self, csv_path, valid_df):
        catalog = self._counting_catalog(csv_path, skip_load_after_save=True)

        catalog.save("companies", valid_df)
        validator = catalog._validators["companies"]
        assert validator.calls == 1

        catalog.load("companies")
        assert validator.calls == 1  # load validation skipped

    def test_release_resets_skip_bookkeeping(self, csv_path, valid_df):
        catalog = self._counting_catalog(csv_path, skip_load_after_save=True)

        catalog.save("companies", valid_df)
        catalog.release("companies")
        catalog.load("companies")

        assert catalog._validators["companies"].calls == 2

    def test_without_flag_load_validates_again(self, csv_path, valid_df):
        catalog = self._counting_catalog(csv_path, skip_load_after_save=False)

        catalog.save("companies", valid_df)
        catalog.load("companies")

        assert catalog._validators["companies"].calls == 2


class TestSpecLifecycle:
    def test_replacement_clears_spec(self, csv_path, valid_df, invalid_df):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        assert "companies" in catalog._validator_specs

        catalog["companies"] = invalid_df  # replace with MemoryDataset

        assert "companies" not in catalog._validator_specs
        assert "companies" not in catalog.validators
        loaded = catalog.load("companies")  # must not validate
        pd.testing.assert_frame_equal(loaded, invalid_df)

    def test_factory_pattern_entry_validates_after_materialisation(
        self, tmp_path, invalid_df
    ):
        invalid_df.to_csv(tmp_path / "companies_data.csv", index=False)
        config = {
            "{name}_data": {
                "type": "pandas.CSVDataset",
                "filepath": f"{tmp_path}/{{name}}_data.csv",
                "validator": f"{_MODULE}.CompaniesSchema",
            }
        }
        catalog = DataCatalog.from_config(config)

        with pytest.raises(DataValidationError) as exc_info:
            catalog.load("companies_data")

        assert exc_info.value.dataset_name == "companies_data"
        assert "companies_data" in catalog._validator_specs

    def test_repr_contains_real_dataset_class_no_wrapper(self, csv_path, valid_df):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        catalog.load("companies")  # materialize + resolve validator

        rendered = repr(catalog)
        assert "CSVDataset" in rendered
        assert "Validating" not in rendered
        assert type(catalog.get("companies")).__name__ == "CSVDataset"

    def test_validators_property_exposes_plain_config(self, csv_path):
        catalog = make_catalog(
            csv_path,
            validator={"class": f"{_MODULE}.CompaniesSchema", "on": ["save"]},
        )
        assert catalog.validators == {
            "companies": {"class": f"{_MODULE}.CompaniesSchema", "on": ["save"]}
        }

        shorthand_catalog = make_catalog(csv_path)
        assert shorthand_catalog.validators == {
            "companies": f"{_MODULE}.CompaniesSchema"
        }


class TestConfigRoundTrip:
    def test_to_config_reinjects_validator_shorthand(self, csv_path):
        catalog = make_catalog(csv_path)
        config, _, _, _ = catalog.to_config()
        assert config["companies"]["validator"] == f"{_MODULE}.CompaniesSchema"

    def test_to_config_reinjects_validator_long_form(self, csv_path):
        catalog = make_catalog(
            csv_path,
            validator={"class": f"{_MODULE}.CompaniesSchema", "severity": "warn"},
        )
        config, _, _, _ = catalog.to_config()
        assert config["companies"]["validator"] == {
            "class": f"{_MODULE}.CompaniesSchema",
            "severity": "warn",
        }

    def test_to_config_reinjects_for_materialized_dataset(self, csv_path, valid_df):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        catalog.load("companies")  # materialize

        config, _, _, _ = catalog.to_config()
        assert config["companies"]["validator"] == f"{_MODULE}.CompaniesSchema"

    def test_round_trip_recaptures_spec(self, csv_path, invalid_df):
        invalid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)

        rebuilt = DataCatalog.from_config(*catalog.to_config()[:2])
        assert rebuilt.validators == catalog.validators
        with pytest.raises(DataValidationError):
            rebuilt.load("companies")


class TestFromConfigDefensiveStripping:
    def test_abstract_dataset_from_config_warns_and_strips(self, csv_path, caplog):
        config = {
            "type": "pandas.CSVDataset",
            "filepath": str(csv_path),
            "validator": f"{_MODULE}.CompaniesSchema",
        }
        with caplog.at_level(logging.WARNING, logger="kedro.io.core"):
            dataset = AbstractDataset.from_config("companies", config)

        assert type(dataset).__name__ == "CSVDataset"
        assert "'validator' attribute removed" in caplog.text


class TestPickling:
    def test_pickle_round_trip_keeps_specs_drops_caches(self, csv_path, valid_df):
        valid_df.to_csv(csv_path, index=False)
        catalog = make_catalog(csv_path)
        catalog.load("companies")  # populate _validators cache
        assert catalog._validators

        restored = pickle.loads(pickle.dumps(catalog))  # noqa: S301

        assert restored._validator_specs == catalog._validator_specs
        assert restored._validators == {}
        assert restored._save_validated == set()

        # the restored catalog still validates
        invalid = pd.DataFrame({"id": [1, 1], "company_rating": [-1.0, 2.0]})
        with pytest.raises(DataValidationError):
            restored.save("companies", invalid)
