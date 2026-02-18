from __future__ import annotations

from unittest.mock import patch

import pytest

from kedro.framework.validation import ValidationError

from ..conftest import PYDANTIC_AVAILABLE, SampleDataclass

if PYDANTIC_AVAILABLE:
    from ..conftest import SamplePydanticModel


class TestParameterValidator:
    def test_validate_raw_params_no_requirements(self, parameter_validator):
        with patch.object(
            parameter_validator, "get_pipeline_requirements", return_value={}
        ):
            result = parameter_validator.validate_raw_params({"key": "value"})
        assert result == {"key": "value"}

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_validate_raw_params_with_requirements(self, parameter_validator):
        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        with patch.object(
            parameter_validator, "get_pipeline_requirements", return_value=requirements
        ):
            result = parameter_validator.validate_raw_params(raw)

        assert isinstance(result["model_options"], SamplePydanticModel)

    def test_get_pipeline_requirements(self, parameter_validator):
        with patch.object(
            parameter_validator.type_extractor,
            "extract_types_from_pipelines",
            return_value={"model_options": SampleDataclass},
        ):
            result = parameter_validator.get_pipeline_requirements()
        assert "model_options" in result


class TestApplyValidation:
    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_pydantic_model_success(self, parameter_validator):
        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        result = parameter_validator.apply_validation(raw, requirements)
        assert isinstance(result["model_options"], SamplePydanticModel)
        assert result["model_options"].test_size == 0.2

    def test_dataclass_success(self, parameter_validator):
        raw = {"config": {"name": "test", "value": 1.5}}
        requirements = {"config": SampleDataclass}

        result = parameter_validator.apply_validation(raw, requirements)
        assert isinstance(result["config"], SampleDataclass)
        assert result["config"].name == "test"

    def test_missing_param_skips(self, parameter_validator):
        raw = {"other_key": "value"}
        requirements = {"model_options": SampleDataclass}

        # Should not raise, just skip the missing param
        result = parameter_validator.apply_validation(raw, requirements)
        assert result == {"other_key": "value"}

    def test_unsupported_type_returns_raw(self, parameter_validator):
        raw = {"threshold": 0.5}
        requirements = {"threshold": float}

        result = parameter_validator.apply_validation(raw, requirements)
        assert result["threshold"] == 0.5

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_validation_failure_raises(self, parameter_validator):
        raw = {"model_options": {"test_size": "banana", "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        with pytest.raises(ValidationError, match="Parameter validation failed"):
            parameter_validator.apply_validation(raw, requirements)

    def test_dataclass_failure_raises(self, parameter_validator):
        raw = {"config": {"wrong_field": "value"}}
        requirements = {"config": SampleDataclass}

        with pytest.raises(ValidationError, match="Parameter validation failed"):
            parameter_validator.apply_validation(raw, requirements)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_multiple_models(self, parameter_validator):
        raw = {
            "model_options": {"test_size": 0.2, "random_state": 3},
            "config": {"name": "test", "value": 1.5},
        }
        requirements = {
            "model_options": SamplePydanticModel,
            "config": SampleDataclass,
        }

        result = parameter_validator.apply_validation(raw, requirements)
        assert isinstance(result["model_options"], SamplePydanticModel)
        assert isinstance(result["config"], SampleDataclass)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_nested_path_validation(self, parameter_validator):
        raw = {"ml": {"model_options": {"test_size": 0.2, "random_state": 3}}}
        requirements = {"ml.model_options": SamplePydanticModel}

        result = parameter_validator.apply_validation(raw, requirements)
        assert isinstance(result["ml"]["model_options"], SamplePydanticModel)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_instantiation_count_logged(self, parameter_validator, caplog):
        import logging

        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        with caplog.at_level(logging.INFO):
            parameter_validator.apply_validation(raw, requirements)

        assert "Successfully instantiated 1 parameter models" in caplog.text
