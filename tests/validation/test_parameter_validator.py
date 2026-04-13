"""Tests for kedro.validation.parameter_validator."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest

from kedro.pipeline import node as kedro_node
from kedro.validation.exceptions import ParameterValidationError
from kedro.validation.parameter_validator import ParameterValidator

from .conftest import SampleDataclass, SamplePydanticModel


class TestParameterValidator:
    def test_validate_raw_params_no_requirements(self):
        validator = ParameterValidator(pipelines={})
        result = validator.validate_raw_params({"key": "value"})
        assert result == {"key": "value"}

    def test_validate_raw_params_with_requirements(self):
        def my_func(model_options: SamplePydanticModel) -> None:
            pass

        test_node = kedro_node(
            func=my_func,
            inputs="params:model_options",
            outputs="output",
            name="test_node",
        )

        pipeline = MagicMock()
        pipeline.nodes = [test_node]

        validator = ParameterValidator(pipelines={"data_science": pipeline})
        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        result = validator.validate_raw_params(raw)

        assert isinstance(result["model_options"], SamplePydanticModel)

    def test_validate_raw_params_scoped_to_pipeline(self):
        """Only validate params from the target pipeline."""

        def ds_func(opts: SampleDataclass) -> None:
            pass

        def pydantic_func(cfg: SamplePydanticModel) -> None:
            pass

        node_a = kedro_node(
            func=ds_func,
            inputs="params:config_a",
            outputs="o1",
            name="node_a",
        )
        node_b = kedro_node(
            func=pydantic_func,
            inputs="params:config_b",
            outputs="o2",
            name="node_b",
        )

        pipeline_a = MagicMock()
        pipeline_a.nodes = [node_a]
        pipeline_b = MagicMock()
        pipeline_b.nodes = [node_b]

        validator = ParameterValidator(
            pipelines={"pipeline_a": pipeline_a, "pipeline_b": pipeline_b}
        )

        raw = {
            "config_a": {"name": "test", "value": 1.5},
            "config_b": {"test_size": 0.2, "random_state": 3},
        }

        result = validator.validate_raw_params(raw, pipeline_name="pipeline_a")

        # config_a should be validated (it's in pipeline_a)
        assert isinstance(result["config_a"], SampleDataclass)
        # config_b should remain a raw dict (pipeline_b was not inspected)
        assert isinstance(result["config_b"], dict)


class TestApplyValidation:
    def test_pydantic_model_success(self, parameter_validator):
        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        result = parameter_validator._apply_validation(raw, requirements)
        assert isinstance(result["model_options"], SamplePydanticModel)
        assert result["model_options"].test_size == 0.2

    def test_dataclass_success(self, parameter_validator):
        raw = {"config": {"name": "test", "value": 1.5}}
        requirements = {"config": SampleDataclass}

        result = parameter_validator._apply_validation(raw, requirements)
        assert isinstance(result["config"], SampleDataclass)
        assert result["config"].name == "test"

    def test_missing_param_skips(self, parameter_validator):
        raw = {"other_key": "value"}
        requirements = {"model_options": SampleDataclass}

        result = parameter_validator._apply_validation(raw, requirements)
        assert result == {"other_key": "value"}

    def test_unsupported_type_returns_raw(self, parameter_validator):
        raw = {"threshold": 0.5}
        requirements = {"threshold": float}

        result = parameter_validator._apply_validation(raw, requirements)
        assert result["threshold"] == 0.5

    def test_validation_failure_raises(self, parameter_validator):
        raw = {"model_options": {"test_size": "banana", "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        with pytest.raises(
            ParameterValidationError, match="Parameter validation failed"
        ):
            parameter_validator._apply_validation(raw, requirements)

    def test_dataclass_failure_raises(self, parameter_validator):
        raw = {"config": {"wrong_field": "value"}}
        requirements = {"config": SampleDataclass}

        with pytest.raises(
            ParameterValidationError, match="Parameter validation failed"
        ):
            parameter_validator._apply_validation(raw, requirements)

    def test_multiple_models(self, parameter_validator):
        raw = {
            "model_options": {"test_size": 0.2, "random_state": 3},
            "config": {"name": "test", "value": 1.5},
        }
        requirements = {
            "model_options": SamplePydanticModel,
            "config": SampleDataclass,
        }

        result = parameter_validator._apply_validation(raw, requirements)
        assert isinstance(result["model_options"], SamplePydanticModel)
        assert isinstance(result["config"], SampleDataclass)

    def test_nested_path_validation(self, parameter_validator):
        raw = {"ml": {"model_options": {"test_size": 0.2, "random_state": 3}}}
        requirements = {"ml.model_options": SamplePydanticModel}

        result = parameter_validator._apply_validation(raw, requirements)
        assert isinstance(result["ml"]["model_options"], SamplePydanticModel)

    def test_instantiation_count_logged(self, parameter_validator, caplog):
        raw = {"model_options": {"test_size": 0.2, "random_state": 3}}
        requirements = {"model_options": SamplePydanticModel}

        with caplog.at_level(
            logging.DEBUG, logger="kedro.validation.parameter_validator"
        ):
            parameter_validator._apply_validation(raw, requirements)

        assert "Successfully instantiated 1 parameter models" in caplog.text

    def test_does_not_modify_original(self, parameter_validator):
        """Verify apply_validation works on a deep copy."""
        raw = {"config": {"name": "test", "value": 1.5}}
        requirements = {"config": SampleDataclass}

        parameter_validator._apply_validation(raw, requirements)
        assert isinstance(raw["config"], dict)
