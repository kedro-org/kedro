"""Tests for the standalone validation API (KEP-7 v2)."""

from __future__ import annotations

import json

import pandas as pd
import pandera.pandas as pa
import pytest

from kedro.io import DataCatalog
from kedro.validation import (
    DataValidationError,
    ValidationResult,
    validate_catalog,
    validate_catalog_dataset,
)

_MODULE = "tests.validation.test_api"


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(unique=True)
    company_rating: float = pa.Field(ge=0)

    class Config:
        strict = False


class ExplodingValidator:
    """Validator raising a non-DataValidationError exception."""

    def validate(self, data):
        raise RuntimeError("kaboom")


@pytest.fixture
def valid_df():
    return pd.DataFrame({"id": [1, 2], "company_rating": [0.5, 2.0]})


@pytest.fixture
def invalid_df():
    return pd.DataFrame({"id": [1, 1], "company_rating": [-0.5, 2.0]})


@pytest.fixture
def catalog(tmp_path, valid_df, invalid_df):
    valid_path = tmp_path / "valid.csv"
    invalid_path = tmp_path / "invalid.csv"
    valid_df.to_csv(valid_path, index=False)
    invalid_df.to_csv(invalid_path, index=False)
    config = {
        "valid_companies": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            "validator": f"{_MODULE}.CompaniesSchema",
        },
        "invalid_companies": {
            "type": "pandas.CSVDataset",
            "filepath": str(invalid_path),
            "validator": f"{_MODULE}.CompaniesSchema",
        },
        "save_only": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            "validator": {"class": f"{_MODULE}.CompaniesSchema", "on": ["save"]},
        },
        "no_validator": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
        },
        "unresolvable": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            "validator": f"{_MODULE}.NoSuchValidator",
        },
        "missing_dep": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            "validator": "definitely_not_installed_pkg.schemas.Schema",
        },
        "missing_file": {
            "type": "pandas.CSVDataset",
            "filepath": str(tmp_path / "nowhere.csv"),
            "validator": f"{_MODULE}.CompaniesSchema",
        },
        "exploding": {
            "type": "pandas.CSVDataset",
            "filepath": str(valid_path),
            "validator": f"{_MODULE}.ExplodingValidator",
        },
    }
    return DataCatalog.from_config(config)


class TestStatuses:
    def test_passed(self, catalog, valid_df):
        result = validate_catalog_dataset(catalog, "valid_companies")

        assert result.status == "passed"
        assert bool(result) is True
        assert result.validator == f"{_MODULE}.CompaniesSchema"
        assert result.failures == []
        pd.testing.assert_frame_equal(result.data, valid_df)

    def test_failed_populates_failures(self, catalog):
        result = validate_catalog_dataset(catalog, "invalid_companies")

        assert result.status == "failed"
        assert bool(result) is False
        assert result.failures
        checks = {failure.check for failure in result.failures}
        assert "greater_than_or_equal_to(0)" in checks
        assert "field_uniqueness" in checks
        assert "Validation failed for dataset 'invalid_companies'" in result.message

    def test_failed_records_api_mode(self, catalog):
        result = validate_catalog_dataset(catalog, "invalid_companies")
        assert "on api" in result.message

    def test_skipped_no_validator(self, catalog):
        result = validate_catalog_dataset(catalog, "no_validator")

        assert result.status == "skipped"
        assert result.reason == "no validator declared"
        assert result.validator is None
        assert bool(result) is True

    def test_skipped_wrong_direction(self, catalog):
        result = validate_catalog_dataset(catalog, "save_only", on="load")

        assert result.status == "skipped"
        assert result.reason == "validator declared for save only"
        assert result.validator == f"{_MODULE}.CompaniesSchema"
        assert bool(result) is True

    def test_errored_unresolvable_validator(self, catalog):
        result = validate_catalog_dataset(catalog, "unresolvable")

        assert result.status == "errored"
        assert result.error_type == "unresolvable_validator"
        assert "NoSuchValidator" in result.message
        assert bool(result) is False

    def test_errored_missing_dependency(self, catalog):
        result = validate_catalog_dataset(catalog, "missing_dep")

        assert result.status == "errored"
        assert result.error_type == "missing_dependency"
        assert "definitely_not_installed_pkg" in result.message

    def test_errored_dataset_error(self, catalog):
        result = validate_catalog_dataset(catalog, "missing_file")

        assert result.status == "errored"
        assert result.error_type == "dataset_error"
        assert result.message

    def test_non_validation_exception_reported_as_failed(self, catalog):
        result = validate_catalog_dataset(catalog, "exploding")

        assert result.status == "failed"
        assert "kaboom" in result.message


class TestExplicitCallsAlwaysValidate:
    def test_ignores_catalog_validation_enabled(self, catalog):
        catalog.validation_enabled = False
        result = validate_catalog_dataset(catalog, "invalid_companies")
        assert result.status == "failed"

    def test_ignores_spec_enabled_flag(self, tmp_path, invalid_df):
        path = tmp_path / "invalid.csv"
        invalid_df.to_csv(path, index=False)
        catalog = DataCatalog.from_config(
            {
                "companies": {
                    "type": "pandas.CSVDataset",
                    "filepath": str(path),
                    "validator": {
                        "class": f"{_MODULE}.CompaniesSchema",
                        "enabled": False,
                    },
                }
            }
        )

        result = validate_catalog_dataset(catalog, "companies")

        assert result.status == "failed"
        assert result.enabled is False  # the flag is reported, not applied


class TestArguments:
    def test_save_without_data_raises_value_error(self, catalog):
        with pytest.raises(ValueError, match="data must be provided"):
            validate_catalog_dataset(catalog, "valid_companies", on="save")

    def test_invalid_on_raises_value_error(self, catalog):
        with pytest.raises(ValueError, match="'on' must be 'load' or 'save'"):
            validate_catalog_dataset(catalog, "valid_companies", on="bogus")

    def test_explicit_data_validated_without_touching_dataset(
        self, catalog, invalid_df
    ):
        result = validate_catalog_dataset(
            catalog, "missing_file", invalid_df, on="save"
        )
        # file does not exist, but data was supplied so validation runs
        assert result.status == "failed"

    def test_none_data_is_treated_as_data(self, catalog):
        result = validate_catalog_dataset(catalog, "valid_companies", None, on="save")
        # None is real data (not the sentinel) -> validator receives it and fails
        assert result.status == "failed"


class TestResultBehaviour:
    def test_raise_if_failed_raises_for_failed(self, catalog):
        result = validate_catalog_dataset(catalog, "invalid_companies")
        with pytest.raises(DataValidationError) as exc_info:
            result.raise_if_failed()
        assert exc_info.value.dataset_name == "invalid_companies"
        assert exc_info.value.mode == "api"
        assert exc_info.value.failures == result.failures

    def test_raise_if_failed_raises_for_errored(self, catalog):
        result = validate_catalog_dataset(catalog, "unresolvable")
        with pytest.raises(DataValidationError):
            result.raise_if_failed()

    def test_raise_if_failed_noop_for_passed_and_skipped(self, catalog):
        validate_catalog_dataset(catalog, "valid_companies").raise_if_failed()
        validate_catalog_dataset(catalog, "no_validator").raise_if_failed()

    @pytest.mark.parametrize(
        ("status", "expected"),
        [
            ("passed", True),
            ("skipped", True),
            ("failed", False),
            ("errored", False),
        ],
    )
    def test_bool_semantics(self, status, expected):
        result = ValidationResult(
            dataset_name="companies", validator=None, status=status
        )
        assert bool(result) is expected

    def test_to_dict_is_json_safe(self, catalog):
        for name in ("valid_companies", "invalid_companies", "unresolvable"):
            result = validate_catalog_dataset(catalog, name)
            as_dict = result.to_dict()
            json.dumps(as_dict)  # must not raise
            assert "data" not in as_dict
            assert as_dict["dataset_name"] == name
            assert as_dict["status"] == result.status

    def test_to_dict_failures_shape(self, catalog):
        result = validate_catalog_dataset(catalog, "invalid_companies")
        failure_dict = result.to_dict()["failures"][0]
        assert set(failure_dict) == {
            "message",
            "check",
            "column",
            "failure_count",
            "failure_examples",
            "index",
        }


class TestValidateCatalog:
    def test_batch_over_declared_specs(self, catalog):
        results = validate_catalog(catalog)

        # every dataset with a declared validator, and nothing else
        assert set(results) == {
            "valid_companies",
            "invalid_companies",
            "save_only",
            "unresolvable",
            "missing_dep",
            "missing_file",
            "exploding",
        }
        assert results["valid_companies"].status == "passed"
        assert results["invalid_companies"].status == "failed"
        assert results["save_only"].status == "skipped"
        assert results["unresolvable"].status == "errored"

    def test_explicit_names_respected(self, catalog):
        results = validate_catalog(catalog, names=["valid_companies", "no_validator"])

        assert set(results) == {"valid_companies", "no_validator"}
        assert results["no_validator"].status == "skipped"
        assert results["no_validator"].reason == "no validator declared"
