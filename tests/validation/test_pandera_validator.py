"""Tests for `PanderaValidator` and the pandera adapter."""

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


class TestErrorRenderingEdgeCases:
    def test_long_example_is_truncated(self):
        failure = CheckFailure(
            message="m", check="c", column="col", failure_examples=["x" * 100]
        )
        text = str(DataValidationError("boom", dataset_name="ds", failures=[failure]))
        assert "..." in text
        assert "x" * 100 not in text

    def test_label_variants(self):
        f_check_only = CheckFailure(message="m1", check="only_check")
        f_column_only = CheckFailure(message="m2", column="only_col")
        f_message_only = CheckFailure(message="only_message")
        text = str(
            DataValidationError(
                "boom",
                dataset_name="ds",
                failures=[f_check_only, f_column_only, f_message_only],
            )
        )
        assert "only_check" in text
        assert "only_col: m2" in text
        assert "only_message" in text

    def test_without_dataset_name_message_is_the_header(self):
        assert str(DataValidationError("standalone message")) == "standalone message"

    def test_empty_message_without_dataset_name_falls_back(self):
        assert str(DataValidationError("")) == "Validation failed"

    def test_long_header_is_truncated(self):
        text = str(DataValidationError("x" * 600))
        assert len(text.splitlines()[0]) <= 500

    def test_message_shown_and_truncated_when_no_failures(self):
        err = DataValidationError("detail " * 100, dataset_name="ds")
        text = str(err)
        assert text.startswith("Validation failed for dataset 'ds'")
        assert text.endswith("...")


class TestFailureCaseRecords:
    def test_none_returns_empty(self):
        from kedro.validation.pandera_validator import _failure_cases_records

        assert _failure_cases_records(None) == []

    def test_polars_style_to_dicts(self):
        from kedro.validation.pandera_validator import _failure_cases_records

        class FakePolarsFrame:
            def to_dicts(self):
                return [{"column": "a", "check": "c", "failure_case": 1}]

        assert _failure_cases_records(FakePolarsFrame()) == [
            {"column": "a", "check": "c", "failure_case": 1}
        ]

    def test_pandas_to_dict_without_orient_falls_through(self):
        from kedro.validation.pandera_validator import _failure_cases_records

        class WeirdFrame:
            columns = ("a",)

            def to_dict(self):  # no orient parameter -> TypeError
                return {}

            def to_dicts(self):
                return [{"ok": 1}]

        assert _failure_cases_records(WeirdFrame()) == [{"ok": 1}]

    def test_list_input_is_normalised(self):
        from kedro.validation.pandera_validator import _failure_cases_records

        assert _failure_cases_records(["bad"]) == [{"failure_case": "bad"}]
        assert _failure_cases_records([{"a": 1}]) == [{"a": 1}]

    def test_unknown_object_returns_empty(self):
        from kedro.validation.pandera_validator import _failure_cases_records

        assert _failure_cases_records(object()) == []


class TestCleanColumn:
    def test_variants(self):
        from kedro.validation.pandera_validator import _clean_column

        assert _clean_column(None) is None
        assert _clean_column(float("nan")) is None
        assert _clean_column("col") == "col"
        assert _clean_column(5) == "5"


def test_failures_from_error_without_failure_cases():
    from kedro.validation.pandera_validator import _failures_from_schema_errors

    assert _failures_from_schema_errors(ValueError("plain")) == [
        CheckFailure(message="plain")
    ]


def test_adapter_unsupported_option_is_config_error():
    with pytest.raises(ValidationConfigurationError, match="Supported options"):
        pandera_adapter(CompaniesSchema, {"bogus": 1})


class TestOptionalBackendDetection:
    def test_is_pandera_model_without_pandera(self, monkeypatch):
        import sys

        monkeypatch.setitem(sys.modules, "pandera.api.dataframe.model", None)
        assert _is_pandera_model(CompaniesSchema) is False

    def test_schema_instance_detection_with_fake_backends(self, monkeypatch):
        import sys
        import types

        class FakePolarsSchema:
            pass

        class FakePySparkSchema:
            pass

        mod_polars = types.ModuleType("pandera.api.polars.container")
        mod_polars.DataFrameSchema = FakePolarsSchema
        mod_pyspark = types.ModuleType("pandera.api.pyspark.container")
        mod_pyspark.DataFrameSchema = FakePySparkSchema
        monkeypatch.setitem(sys.modules, "pandera.api.polars.container", mod_polars)
        monkeypatch.setitem(sys.modules, "pandera.api.pyspark.container", mod_pyspark)

        assert _is_pandera_schema_instance(FakePolarsSchema()) is True
        assert _is_pandera_schema_instance(FakePySparkSchema()) is True

    def test_schema_instance_detection_without_any_backend(self, monkeypatch):
        import sys

        for name in (
            "pandera.api.pandas.container",
            "pandera.api.polars.container",
            "pandera.api.pyspark.container",
        ):
            monkeypatch.setitem(sys.modules, name, None)
        assert _is_pandera_schema_instance(object()) is False


class TestPysparkAndLazyframePaths:
    def test_is_pyspark_dataframe_with_fake_modules(self, monkeypatch):
        import sys
        import types

        class FakeSparkDataFrame:
            pass

        mod_pandera_pyspark = types.ModuleType("pandera.pyspark")
        mod_pyspark_sql = types.ModuleType("pyspark.sql")
        mod_pyspark_sql.DataFrame = FakeSparkDataFrame
        monkeypatch.setitem(sys.modules, "pandera.pyspark", mod_pandera_pyspark)
        monkeypatch.setitem(sys.modules, "pyspark.sql", mod_pyspark_sql)

        validator = PanderaValidator(CompaniesSchema)
        assert validator._is_pyspark_dataframe(FakeSparkDataFrame()) is True
        assert validator._is_pyspark_dataframe(object()) is False

    def test_lazyframe_warning_emitted_once(self, monkeypatch, caplog):
        import logging
        import sys
        import types

        class FakeLazyFrame:
            pass

        fake_polars = types.ModuleType("polars")
        fake_polars.LazyFrame = FakeLazyFrame
        monkeypatch.setitem(sys.modules, "polars", fake_polars)

        validator = PanderaValidator(CompaniesSchema)
        with caplog.at_level(logging.WARNING):
            validator._maybe_warn_lazyframe(FakeLazyFrame())
            validator._maybe_warn_lazyframe(FakeLazyFrame())
        warnings = [r for r in caplog.records if "LazyFrame" in r.message]
        assert len(warnings) == 1

    def test_validate_routes_pyspark_and_raises_on_accessor_errors(self, monkeypatch):
        import types

        validator = PanderaValidator(CompaniesSchema)
        accessor = types.SimpleNamespace(errors={"SCHEMA": {"err": "details"}})
        out = types.SimpleNamespace(pandera=accessor)
        monkeypatch.setattr(
            validator, "_schema", types.SimpleNamespace(validate=lambda data: out)
        )
        monkeypatch.setattr(validator, "_is_pyspark_dataframe", lambda data: True)

        with pytest.raises(DataValidationError, match="SCHEMA"):
            validator.validate(object())

    def test_validate_pyspark_returns_output_when_no_errors(self, monkeypatch):
        import types

        validator = PanderaValidator(CompaniesSchema)
        out = types.SimpleNamespace(pandera=types.SimpleNamespace(errors={}))
        monkeypatch.setattr(
            validator, "_schema", types.SimpleNamespace(validate=lambda data: out)
        )

        assert validator._validate_pyspark(object()) is out


def test_header_includes_mode_when_set():
    err = DataValidationError("boom", dataset_name="ds", mode="load")
    assert str(err).splitlines()[0] == "Validation failed for dataset 'ds' on load"


def test_excess_failures_render_hidden_note():
    failures = [CheckFailure(message=f"m{i}") for i in range(12)]
    text = str(DataValidationError("boom", dataset_name="ds", failures=failures))
    assert "... and 2 more check(s)" in text
