"""Tests for ``PanderaValidator`` and the pandera adapter (KEP-7 v2)."""

from __future__ import annotations

import pandas as pd
import pandera.errors as pa_errors
import pandera.pandas as pa
import pytest

from kedro.validation import (
    CheckFailure,
    DataValidationError,
    PanderaValidator,
    ValidationConfigurationError,
)
from kedro.validation.pandera_validator import (
    _is_pandera_model,
    _is_pandera_schema_instance,
    pandera_adapter,
)

_MODULE = "tests.validation.test_pandera_validator"


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(unique=True)
    company_rating: float = pa.Field(ge=0)

    class Config:
        strict = False


class CoercingSchema(pa.DataFrameModel):
    id: int = pa.Field()

    class Config:
        coerce = True


@pytest.fixture
def valid_df():
    return pd.DataFrame({"id": [1, 2, 3], "company_rating": [0.0, 2.5, 10.0]})


@pytest.fixture
def invalid_df():
    # two failed checks: id uniqueness (1 case pair) and rating >= 0 (2 cases)
    return pd.DataFrame({"id": [10542, 10542, 3], "company_rating": [-0.5, -1.2, 1.0]})


class TestDetectionHelpers:
    def test_dataframe_model_subclass_detected(self):
        assert _is_pandera_model(CompaniesSchema) is True

    def test_non_pandera_class_not_detected(self):
        assert _is_pandera_model(dict) is False

    def test_non_class_not_detected(self):
        assert _is_pandera_model("not a class") is False
        assert _is_pandera_model(pa.DataFrameSchema({})) is False

    def test_schema_instance_detected(self):
        assert _is_pandera_schema_instance(pa.DataFrameSchema({})) is True

    def test_schema_class_not_detected_as_instance(self):
        assert _is_pandera_schema_instance(pa.DataFrameSchema) is False
        assert _is_pandera_schema_instance(pd.DataFrame()) is False


class TestPanderaAdapter:
    def test_model_class_adapted(self):
        validator = pandera_adapter(CompaniesSchema, {})
        assert isinstance(validator, PanderaValidator)

    def test_schema_instance_adapted(self):
        schema = pa.DataFrameSchema({"id": pa.Column(int)})
        validator = pandera_adapter(schema, {})
        assert isinstance(validator, PanderaValidator)

    def test_options_forwarded(self):
        validator = pandera_adapter(
            CompaniesSchema,
            {"lazy": False, "head": 5, "tail": 2, "sample": 3, "random_state": 42},
        )
        assert validator._lazy is False
        assert validator._head == 5
        assert validator._tail == 2
        assert validator._sample == 3
        assert validator._random_state == 42

    @pytest.mark.parametrize("obj", [dict, "string", 42, pd.DataFrame])
    def test_non_pandera_object_returns_none(self, obj):
        assert pandera_adapter(obj, {}) is None

    def test_unknown_option_raises_config_error(self):
        with pytest.raises(ValidationConfigurationError) as exc_info:
            pandera_adapter(CompaniesSchema, {"bogus_option": 1})
        message = str(exc_info.value)
        assert "CompaniesSchema" in message
        assert "Supported options: lazy, head, tail, sample, random_state" in message


class TestPanderaValidatorValidate:
    def test_valid_dataframe_passes(self, valid_df):
        result = PanderaValidator(CompaniesSchema).validate(valid_df)
        pd.testing.assert_frame_equal(result, valid_df)

    def test_invalid_dataframe_raises_data_validation_error(self, invalid_df):
        with pytest.raises(DataValidationError):
            PanderaValidator(CompaniesSchema).validate(invalid_df)

    def test_failures_grouped_by_column_and_check(self, invalid_df):
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(invalid_df)
        failures = exc_info.value.failures

        assert all(isinstance(failure, CheckFailure) for failure in failures)
        by_key = {(failure.column, failure.check): failure for failure in failures}

        rating_failure = by_key[("company_rating", "greater_than_or_equal_to(0)")]
        assert rating_failure.failure_count == 2
        assert -0.5 in rating_failure.failure_examples
        assert -1.2 in rating_failure.failure_examples

        uniqueness_failure = by_key[("id", "field_uniqueness")]
        assert uniqueness_failure.failure_count == 2
        assert 10542 in uniqueness_failure.failure_examples

    def test_failure_examples_capped_at_five(self):
        df = pd.DataFrame({"id": list(range(20)), "company_rating": [-1.0] * 20})
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(df)
        (failure,) = exc_info.value.failures

        assert failure.failure_count == 20
        assert len(failure.failure_examples) == 5

    def test_full_schema_errors_kept_on_cause(self, invalid_df):
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(invalid_df)
        assert isinstance(exc_info.value.__cause__, pa_errors.SchemaErrors)

    def test_validator_attribute_is_schema_dotted_path(self, invalid_df):
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(invalid_df)
        assert exc_info.value.validator == f"{_MODULE}.CompaniesSchema"

    def test_non_lazy_raises_with_single_failure(self, invalid_df):
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema, lazy=False).validate(invalid_df)

        assert isinstance(exc_info.value.__cause__, pa_errors.SchemaError)
        assert len(exc_info.value.failures) == 1
        assert exc_info.value.failures[0].check is not None

    def test_coercion_returns_coerced_frame(self):
        df = pd.DataFrame({"id": ["1", "2", "3"]})
        result = PanderaValidator(CoercingSchema).validate(df)
        assert result["id"].dtype == "int64"

    def test_schema_instance_coercion(self):
        schema = pa.DataFrameSchema({"id": pa.Column(int, coerce=True)})
        result = PanderaValidator(schema).validate(pd.DataFrame({"id": ["7"]}))
        assert result["id"].dtype == "int64"

    def test_head_option_limits_validated_rows(self):
        # only the last row is invalid; head=2 must not see it
        df = pd.DataFrame({"id": [1, 2, 3], "company_rating": [1.0, 2.0, -5.0]})

        result = PanderaValidator(CompaniesSchema, head=2).validate(df)
        pd.testing.assert_frame_equal(result, df)

        with pytest.raises(DataValidationError):
            PanderaValidator(CompaniesSchema).validate(df)

    def test_only_non_none_kwargs_forwarded_to_schema_validate(self):
        class RecordingSchema:
            def __init__(self):
                self.kwargs = None

            def validate(self, data, **kwargs):
                self.kwargs = kwargs
                return data

        schema = RecordingSchema()
        df = pd.DataFrame({"id": [1]})

        PanderaValidator(schema).validate(df)
        assert schema.kwargs == {"lazy": True}

        PanderaValidator(
            schema, lazy=False, head=2, sample=10, random_state=42
        ).validate(df)
        assert schema.kwargs == {
            "lazy": False,
            "head": 2,
            "sample": 10,
            "random_state": 42,
        }


class TestErrorRendering:
    def test_enriched_error_renders_per_spec(self, invalid_df):
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(invalid_df)
        exc = exc_info.value
        exc.dataset_name = "companies"
        exc.mode = "load"

        rendered = str(exc)
        assert "Validation failed for dataset 'companies' on load" in rendered
        assert f"(validator: {_MODULE}.CompaniesSchema)" in rendered
        assert "2 check(s) failed — 4 failure case(s):" in rendered
        assert "- company_rating: greater_than_or_equal_to(0) — 2 cases" in rendered
        assert "- id: field_uniqueness — 2 cases" in rendered
        assert "(e.g. -0.5, -1.2)" in rendered

    def test_rendering_bounded_for_large_frames(self):
        df = pd.DataFrame(
            {"id": list(range(50_000)), "company_rating": [-1.0] * 50_000}
        )
        with pytest.raises(DataValidationError) as exc_info:
            PanderaValidator(CompaniesSchema).validate(df)
        exc = exc_info.value
        exc.dataset_name = "companies"
        exc.mode = "load"

        rendered = str(exc)
        assert len(rendered) < 2000
        assert "50000 failure case(s)" in rendered

    def test_rendering_caps_number_of_checks(self):
        failures = [
            CheckFailure(message=f"check {i}", check=f"check_{i}", failure_count=1)
            for i in range(25)
        ]
        exc = DataValidationError(
            "boom", dataset_name="companies", mode="load", failures=failures
        )
        rendered = str(exc)
        assert "25 check(s) failed" in rendered
        assert "... and 15 more check(s)" in rendered
        assert len(rendered.splitlines()) < 20
