"""Tests for kedro.validation.model_factory."""

from __future__ import annotations

import pytest

from kedro.validation.exceptions import ModelInstantiationError
from kedro.validation.model_factory import instantiate_model

from .conftest import SampleDataclass, SamplePydanticModel


class TestInstantiateModel:
    def test_instantiate_pydantic_model(self):
        raw = {"test_size": 0.2, "random_state": 3}
        result = instantiate_model("model_options", raw, SamplePydanticModel)
        assert isinstance(result, SamplePydanticModel)
        assert result.test_size == 0.2
        assert result.random_state == 3

    def test_instantiate_pydantic_invalid_data(self):
        raw = {"test_size": "banana", "random_state": 3}
        with pytest.raises(ModelInstantiationError):
            instantiate_model("model_options", raw, SamplePydanticModel)

    def test_instantiate_dataclass(self):
        raw = {"name": "test", "value": 1.5}
        result = instantiate_model("config", raw, SampleDataclass)
        assert isinstance(result, SampleDataclass)
        assert result.name == "test"
        assert result.value == 1.5

    def test_instantiate_dataclass_invalid_fields(self):
        raw = {"wrong_field": "value"}
        with pytest.raises(ModelInstantiationError):
            instantiate_model("config", raw, SampleDataclass)

    def test_instantiate_dataclass_non_dict(self):
        """Non-dict raw value raises ModelInstantiationError."""
        with pytest.raises(ModelInstantiationError):
            instantiate_model("config", "not a dict", SampleDataclass)

    def test_instantiate_unsupported_type_returns_raw(self):
        raw = 42
        result = instantiate_model("threshold", raw, int)
        assert result is raw

    def test_instantiate_unsupported_type_str(self):
        raw = "hello"
        result = instantiate_model("name", raw, str)
        assert result is raw

    def test_error_message_includes_context(self):
        raw = {"wrong_field": "value"}
        with pytest.raises(
            ModelInstantiationError,
            match="Failed to instantiate SampleDataclass for source 'config'",
        ):
            instantiate_model("config", raw, SampleDataclass)
