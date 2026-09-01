"""Tests for the on-demand validation API."""

from __future__ import annotations

import json
from typing import ClassVar

import pandas as pd
import pandera.pandas as pa
import pytest

from kedro.io import DataCatalog
from kedro.validation import (
    DataValidationError,
    ValidationResult,
    validate_catalog,
    validate_dataset,
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
        result = validate_dataset(catalog, "valid_companies")

        assert result.status == "passed"
        assert bool(result) is True
        assert result.validator == f"{_MODULE}.CompaniesSchema"
        assert result.failures == []
        pd.testing.assert_frame_equal(result.data, valid_df)

    def test_failed_populates_failures(self, catalog):
        result = validate_dataset(catalog, "invalid_companies")

        assert result.status == "failed"
        assert bool(result) is False
        assert result.failures
        checks = {failure.check for failure in result.failures}
        assert "greater_than_or_equal_to(0)" in checks
        assert "field_uniqueness" in checks
        assert "Validation failed for dataset 'invalid_companies'" in result.message

    def test_failed_records_api_mode(self, catalog):
        result = validate_dataset(catalog, "invalid_companies")
        assert "on api" in result.message

    def test_skipped_no_validator(self, catalog):
        result = validate_dataset(catalog, "no_validator")

        assert result.status == "skipped"
        assert result.reason == "no validator declared"
        assert result.validator is None
        assert bool(result) is True

    def test_skipped_wrong_direction(self, catalog):
        result = validate_dataset(catalog, "save_only", on="load")

        assert result.status == "skipped"
        assert result.reason == "validator declared for save only"
        assert result.validator == f"{_MODULE}.CompaniesSchema"
        assert bool(result) is True

    def test_errored_unresolvable_validator(self, catalog):
        result = validate_dataset(catalog, "unresolvable")

        assert result.status == "errored"
        assert result.error_type == "unresolvable_validator"
        assert "NoSuchValidator" in result.message
        assert bool(result) is False

    def test_errored_missing_dependency(self, catalog):
        result = validate_dataset(catalog, "missing_dep")

        assert result.status == "errored"
        assert result.error_type == "missing_dependency"
        assert "definitely_not_installed_pkg" in result.message

    def test_errored_dataset_error(self, catalog):
        result = validate_dataset(catalog, "missing_file")

        assert result.status == "errored"
        assert result.error_type == "dataset_error"
        assert result.message

    def test_non_validation_exception_reported_as_failed(self, catalog):
        result = validate_dataset(catalog, "exploding")

        assert result.status == "failed"
        assert "kaboom" in result.message


class TestExplicitCallsAlwaysValidate:
    def test_ignores_catalog_validation_enabled(self, catalog):
        catalog.validation_enabled = False
        result = validate_dataset(catalog, "invalid_companies")
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

        result = validate_dataset(catalog, "companies")

        assert result.status == "failed"
        assert result.enabled is False  # the flag is reported, not applied


class TestArguments:
    def test_save_without_data_raises_value_error(self, catalog):
        with pytest.raises(ValueError, match="data must be provided"):
            validate_dataset(catalog, "valid_companies", on="save")

    def test_invalid_on_raises_value_error(self, catalog):
        with pytest.raises(ValueError, match="'on' must be 'load' or 'save'"):
            validate_dataset(catalog, "valid_companies", on="bogus")

    def test_explicit_data_validated_without_touching_dataset(
        self, catalog, invalid_df
    ):
        result = validate_dataset(catalog, "missing_file", invalid_df, on="save")
        # file does not exist, but data was supplied so validation runs
        assert result.status == "failed"

    def test_none_data_is_treated_as_data(self, catalog):
        result = validate_dataset(catalog, "valid_companies", None, on="save")
        # None is real data (not the sentinel) -> validator receives it and fails
        assert result.status == "failed"


class TestResultBehaviour:
    def test_raise_if_failed_raises_for_failed(self, catalog):
        result = validate_dataset(catalog, "invalid_companies")
        with pytest.raises(DataValidationError) as exc_info:
            result.raise_if_failed()
        assert exc_info.value.dataset_name == "invalid_companies"
        assert exc_info.value.mode == "api"
        assert exc_info.value.failures == result.failures

    def test_raise_if_failed_raises_for_errored(self, catalog):
        result = validate_dataset(catalog, "unresolvable")
        with pytest.raises(DataValidationError):
            result.raise_if_failed()

    def test_raise_if_failed_noop_for_passed_and_skipped(self, catalog):
        validate_dataset(catalog, "valid_companies").raise_if_failed()
        validate_dataset(catalog, "no_validator").raise_if_failed()

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
            result = validate_dataset(catalog, name)
            as_dict = result.to_dict()
            json.dumps(as_dict, allow_nan=False)  # strict JSON, must not raise
            assert "data" not in as_dict
            assert as_dict["dataset_name"] == name
            assert as_dict["status"] == result.status

    def test_to_dict_failures_shape(self, catalog):
        result = validate_dataset(catalog, "invalid_companies")
        failure_dict = result.to_dict()["failures"][0]
        assert set(failure_dict) == {
            "message",
            "check",
            "column",
            "failure_count",
            "failure_examples",
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


class TestCatalogCompatibility:
    def test_catalog_without_validator_support_is_skipped(self):
        class PlainCatalog:
            pass

        result = validate_dataset(PlainCatalog(), "anything")
        assert result.status == "skipped"
        assert "does not support" in result.reason
        assert bool(result) is True

    def test_factory_pattern_dataset_is_materialised_and_validated(
        self, tmp_path, invalid_df
    ):
        csv = tmp_path / "companies_data.csv"
        invalid_df.to_csv(csv, index=False)
        catalog = DataCatalog.from_config(
            {
                "{name}_data": {
                    "type": "pandas.CSVDataset",
                    "filepath": str(tmp_path / "{name}_data.csv"),
                    "validator": f"{_MODULE}.CompaniesSchema",
                }
            }
        )
        assert "companies_data" not in catalog.validator_specs  # not materialised

        result = validate_dataset(catalog, "companies_data")

        assert result.status == "failed"
        assert result.validator == f"{_MODULE}.CompaniesSchema"

    def test_unmaterialised_factory_names_need_explicit_listing(
        self, tmp_path, valid_df
    ):
        csv = tmp_path / "companies_data.csv"
        valid_df.to_csv(csv, index=False)
        catalog = DataCatalog.from_config(
            {
                "{name}_data": {
                    "type": "pandas.CSVDataset",
                    "filepath": str(tmp_path / "{name}_data.csv"),
                    "validator": f"{_MODULE}.CompaniesSchema",
                }
            }
        )
        assert validate_catalog(catalog) == {}  # nothing captured yet

        results = validate_catalog(catalog, names=["companies_data"])
        assert results["companies_data"].status == "passed"

    def test_unqueryable_catalog_reports_no_validator(self):
        class ExplodingContains:
            validator_specs: ClassVar[dict] = {}

            def __contains__(self, name):
                raise RuntimeError("boom")

        result = validate_dataset(ExplodingContains(), "ds")
        assert result.status == "skipped"
        assert result.reason == "no validator declared"

    def test_name_not_in_catalog_is_dataset_error(self, catalog):
        result = validate_dataset(catalog, "no_such_dataset")

        assert result.status == "errored"
        assert result.error_type == "dataset_error"
        assert "not found in the catalog" in result.message

    def test_materialisation_failure_is_dataset_error(self, tmp_path):
        catalog = DataCatalog.from_config(
            {
                "{name}_data": {
                    "type": "pandas.NoSuchDatasetType",
                    "filepath": str(tmp_path / "{name}_data.csv"),
                    "validator": f"{_MODULE}.CompaniesSchema",
                }
            }
        )

        result = validate_dataset(catalog, "companies_data")

        assert result.status == "errored"
        assert result.error_type == "dataset_error"
        assert "could not be created" in result.message


class TestInternals:
    def test_unset_sentinel_repr(self):
        from kedro.validation.api import _UNSET

        assert repr(_UNSET) == "<unset>"

    def test_json_safe_falls_back_to_repr(self):
        from kedro.validation.api import _json_safe

        assert _json_safe(None) is None
        assert _json_safe(3) == 3
        assert _json_safe(object()).startswith("<object")

    def test_spec_without_resolvable_dataset_is_dataset_error(self):
        from kedro.validation import ValidatorSpec

        class SpecOnlyCatalog:
            validator_specs: ClassVar[dict] = {
                "ghost": ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
            }

            def get(self, name, version=None):
                return None

        result = validate_dataset(SpecOnlyCatalog(), "ghost")
        assert result.status == "errored"
        assert result.error_type == "dataset_error"
        assert "not found" in result.message


class TestReviewedBehaviours:
    def test_non_finite_failure_examples_are_strict_json_safe(self):
        from kedro.validation import CheckFailure
        from kedro.validation.api import _failure_to_dict

        failure = CheckFailure(
            message="m",
            failure_examples=[float("nan"), float("inf"), float("-inf"), 1.5],
        )
        as_dict = _failure_to_dict(failure)

        json.dumps(as_dict, allow_nan=False)  # must not raise
        assert as_dict["failure_examples"] == ["nan", "inf", "-inf", 1.5]

    def test_warn_severity_still_reports_failed(self, tmp_path, invalid_df):
        path = tmp_path / "invalid.csv"
        invalid_df.to_csv(path, index=False)
        catalog = DataCatalog.from_config(
            {
                "companies": {
                    "type": "pandas.CSVDataset",
                    "filepath": str(path),
                    "validator": {
                        "class": f"{_MODULE}.CompaniesSchema",
                        "severity": "warn",
                    },
                }
            }
        )

        result = validate_dataset(catalog, "companies")

        assert result.status == "failed"

    def test_save_mode_success(self, catalog, valid_df):
        result = validate_dataset(catalog, "valid_companies", valid_df, on="save")

        assert result.status == "passed"
        pd.testing.assert_frame_equal(result.data, valid_df)

    def test_version_forwarded_to_catalog_get(self, valid_df):
        from kedro.validation import ValidatorSpec

        received = {}

        class Dataset:
            def load(self):
                return valid_df

        class VersionedCatalog:
            validator_specs: ClassVar[dict] = {
                "companies": ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
            }

            def get(self, name, version=None):
                received["version"] = version
                return Dataset()

        result = validate_dataset(
            VersionedCatalog(), "companies", version="2026-01-01T00.00.00.000Z"
        )

        assert result.status == "passed"
        assert received["version"].load == "2026-01-01T00.00.00.000Z"

    def test_raise_if_failed_carries_error_type(self, catalog):
        result = validate_dataset(catalog, "missing_dep")

        with pytest.raises(DataValidationError) as exc_info:
            result.raise_if_failed()
        assert exc_info.value.error_type == "missing_dependency"
