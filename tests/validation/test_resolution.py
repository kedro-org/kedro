"""Tests for ``resolve_validator`` and ``preflight_check`` (KEP-7 v2)."""

from __future__ import annotations

import pandas as pd
import pandera.pandas as pa
import pytest

from kedro.validation import (
    CallableValidator,
    PanderaValidator,
    ValidationConfigurationError,
    ValidatorSpec,
    preflight_check,
    resolve_validator,
)

_MODULE = "tests.validation.test_resolution"


# --- Module-level objects importable by class path -------------------------


class CompaniesSchema(pa.DataFrameModel):
    id: int = pa.Field(unique=True)
    company_rating: float = pa.Field(ge=0)

    class Config:
        strict = False


COMPANIES_SCHEMA_INSTANCE = pa.DataFrameSchema(
    {"id": pa.Column(int), "company_rating": pa.Column(float, pa.Check.ge(0))}
)


class ThresholdValidator:
    """Custom validator class taking constructor options.

    This is the runtime_checkable footgun target: it defines ``validate`` so
    ``isinstance(cls, Validator)`` would be True for the CLASS itself, but
    resolution must instantiate it (with options) rather than return the
    uninstantiated class.
    """

    def __init__(self, threshold: float = 0.0):
        self.threshold = threshold

    def validate(self, data):
        if (data["company_rating"] < self.threshold).any():
            raise ValueError(f"ratings below {self.threshold}")
        return data


class NoValidateMethod:
    """Instantiable class that does not satisfy the Validator protocol."""

    def __init__(self):
        pass


INSTANCE_VALIDATOR = ThresholdValidator(threshold=1.0)


def assert_non_empty(data):
    """Plain assertion-style validator function (returns None)."""
    assert len(data) > 0, "data is empty"


def double_ratings(data):
    """Plain transforming validator function (returns data)."""
    data = data.copy()
    data["company_rating"] = data["company_rating"] * 2
    return data


NOT_A_VALIDATOR = 42


# --- Tests ------------------------------------------------------------------


class TestPanderaResolution:
    def test_dataframe_model_class_routes_through_adapter(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert validator._schema is CompaniesSchema

    def test_dataframe_model_with_options(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.CompaniesSchema",
            options={"lazy": False, "head": 10},
        )
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert validator._lazy is False
        assert validator._head == 10

    def test_dataframe_schema_instance_accepted(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.COMPANIES_SCHEMA_INSTANCE")
        validator = resolve_validator(spec)

        assert isinstance(validator, PanderaValidator)
        assert validator._schema is COMPANIES_SCHEMA_INSTANCE

    def test_resolved_pandera_validator_validates(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"id": [1, 2], "company_rating": [0.5, 1.0]})

        result = validator.validate(df)

        pd.testing.assert_frame_equal(result, df)

    def test_unsupported_pandera_option_is_config_error(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.CompaniesSchema", options={"bogus_option": 1}
        )
        with pytest.raises(
            ValidationConfigurationError, match="CompaniesSchema"
        ) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert "bogus_option" in message
        assert "lazy, head, tail, sample, random_state" in message


class TestCustomClassResolution:
    def test_class_with_options_is_instantiated(self):
        """The runtime_checkable footgun: must NOT return the class itself."""
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.ThresholdValidator", options={"threshold": 2.5}
        )
        validator = resolve_validator(spec)

        assert isinstance(validator, ThresholdValidator)
        assert validator is not ThresholdValidator
        assert not isinstance(validator, type)
        assert validator.threshold == 2.5

    def test_class_without_options_is_instantiated_with_defaults(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.ThresholdValidator")
        validator = resolve_validator(spec)

        assert isinstance(validator, ThresholdValidator)
        assert validator.threshold == 0.0

    def test_bad_constructor_option_is_config_error_naming_option(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.ThresholdValidator", options={"bogus": 1}
        )
        with pytest.raises(ValidationConfigurationError) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert f"{_MODULE}.ThresholdValidator" in message
        assert "bogus" in message

    def test_instance_without_validate_method_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NoValidateMethod")
        with pytest.raises(ValidationConfigurationError, match="validate"):
            resolve_validator(spec)


class TestInstanceResolution:
    def test_module_level_instance_accepted(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.INSTANCE_VALIDATOR")
        validator = resolve_validator(spec)

        assert validator is INSTANCE_VALIDATOR

    def test_instance_with_options_is_config_error(self):
        spec = ValidatorSpec(
            class_path=f"{_MODULE}.INSTANCE_VALIDATOR", options={"threshold": 5.0}
        )
        with pytest.raises(ValidationConfigurationError, match="instance"):
            resolve_validator(spec)


class TestCallableResolution:
    def test_plain_function_wrapped_in_callable_validator(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)

        assert isinstance(validator, CallableValidator)

    def test_assertion_style_function_returns_original_data(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"id": [1]})

        assert validator.validate(df) is df

    def test_assertion_style_function_raise_propagates(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty")
        validator = resolve_validator(spec)

        with pytest.raises(AssertionError, match="data is empty"):
            validator.validate(pd.DataFrame())

    def test_transforming_function_returns_transformed_data(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.double_ratings")
        validator = resolve_validator(spec)
        df = pd.DataFrame({"company_rating": [1.0, 2.0]})

        result = validator.validate(df)

        assert result["company_rating"].tolist() == [2.0, 4.0]

    def test_function_with_options_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.assert_non_empty", options={"x": 1})
        with pytest.raises(ValidationConfigurationError, match="callable"):
            resolve_validator(spec)


class TestImportErrors:
    def test_missing_module_is_config_error_with_hint(self):
        spec = ValidatorSpec(class_path="definitely_not_installed_pkg.Schema")
        with pytest.raises(ValidationConfigurationError) as exc_info:
            resolve_validator(spec)
        message = str(exc_info.value)
        assert "definitely_not_installed_pkg.Schema" in message
        assert "Check that the class path is correct" in message
        assert isinstance(exc_info.value.__cause__, ModuleNotFoundError)

    def test_missing_pandera_submodule_mentions_validation_extra(self):
        spec = ValidatorSpec(class_path="pandera.no_such_submodule.Schema")
        with pytest.raises(
            ValidationConfigurationError, match=r"pip install kedro\[validation\]"
        ):
            resolve_validator(spec)

    def test_missing_attribute_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NoSuchAttribute")
        with pytest.raises(ValidationConfigurationError, match="NoSuchAttribute"):
            resolve_validator(spec)

    def test_non_validator_object_is_config_error(self):
        spec = ValidatorSpec(class_path=f"{_MODULE}.NOT_A_VALIDATOR")
        with pytest.raises(
            ValidationConfigurationError, match="not a validator"
        ) as exc_info:
            resolve_validator(spec)
        assert "int" in str(exc_info.value)


class TestPreflightCheck:
    def test_missing_package_produces_warning(self):
        specs = {
            "companies": ValidatorSpec(class_path="definitely_not_installed_pkg.Schema")
        }
        warnings = preflight_check(specs)

        assert len(warnings) == 1
        assert "companies" in warnings[0]
        assert "definitely_not_installed_pkg" in warnings[0]

    def test_installed_packages_produce_no_warnings(self):
        specs = {
            "companies": ValidatorSpec(class_path=f"{_MODULE}.CompaniesSchema"),
            "shuttles": ValidatorSpec(class_path="pandera.pandas.DataFrameModel"),
        }
        assert preflight_check(specs) == []

    def test_empty_specs_produce_no_warnings(self):
        assert preflight_check({}) == []
