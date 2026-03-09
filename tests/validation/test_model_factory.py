"""Tests for kedro.validation.model_factory."""

from __future__ import annotations

import pytest

from kedro.validation.exceptions import ModelInstantiationError

from .conftest import SampleDataclass, SamplePydanticModel


class TestModelFactory:
    def test_instantiate_pydantic_model(self, model_factory):
        raw = {"test_size": 0.2, "random_state": 3}
        result = model_factory.instantiate("model_options", raw, SamplePydanticModel)
        assert isinstance(result, SamplePydanticModel)
        assert result.test_size == 0.2
        assert result.random_state == 3

    def test_instantiate_pydantic_invalid_data(self, model_factory):
        raw = {"test_size": "banana", "random_state": 3}
        with pytest.raises(ModelInstantiationError):
            model_factory.instantiate("model_options", raw, SamplePydanticModel)

    def test_instantiate_dataclass(self, model_factory):
        raw = {"name": "test", "value": 1.5}
        result = model_factory.instantiate("config", raw, SampleDataclass)
        assert isinstance(result, SampleDataclass)
        assert result.name == "test"
        assert result.value == 1.5

    def test_instantiate_dataclass_invalid_fields(self, model_factory):
        raw = {"wrong_field": "value"}
        with pytest.raises(ModelInstantiationError):
            model_factory.instantiate("config", raw, SampleDataclass)

    def test_instantiate_dataclass_non_dict(self, model_factory):
        """Non-dict raw value raises ModelInstantiationError."""
        with pytest.raises(ModelInstantiationError):
            model_factory.instantiate("config", "not a dict", SampleDataclass)

    def test_instantiate_unsupported_type_returns_raw(self, model_factory):
        raw = 42
        result = model_factory.instantiate("threshold", raw, int)
        assert result is raw

    def test_instantiate_unsupported_type_str(self, model_factory):
        raw = "hello"
        result = model_factory.instantiate("name", raw, str)
        assert result is raw

    def test_error_message_includes_context(self, model_factory):
        raw = {"wrong_field": "value"}
        with pytest.raises(
            ModelInstantiationError,
            match="Failed to instantiate SampleDataclass for source 'config'",
        ):
            model_factory.instantiate("config", raw, SampleDataclass)
