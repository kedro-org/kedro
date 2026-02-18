"""Tests for kedro.framework.validation.model_factory."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from kedro.framework.validation.exceptions import ModelInstantiationError

from .conftest import PYDANTIC_AVAILABLE, SampleDataclass

if PYDANTIC_AVAILABLE:
    from .conftest import SamplePydanticModel


class TestModelFactory:
    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_instantiate_pydantic_model(self, model_factory):
        raw = {"test_size": 0.2, "random_state": 3}
        result = model_factory.instantiate("model_options", raw, SamplePydanticModel)
        assert isinstance(result, SamplePydanticModel)
        assert result.test_size == 0.2
        assert result.random_state == 3

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_instantiate_pydantic_invalid_data(self, model_factory):
        raw = {"test_size": "banana", "random_state": 3}
        with pytest.raises(ModelInstantiationError):
            model_factory.instantiate("model_options", raw, SamplePydanticModel)

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_instantiate_pydantic_directly(self, model_factory):
        raw = {"test_size": 0.5, "random_state": 42}
        result = model_factory.instantiate_pydantic(raw, SamplePydanticModel)
        assert isinstance(result, SamplePydanticModel)
        assert result.test_size == 0.5

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_is_pydantic_model_true(self, model_factory):
        assert model_factory._is_pydantic_model(SamplePydanticModel) is True

    def test_is_pydantic_model_false_dataclass(self, model_factory):
        assert model_factory._is_pydantic_model(SampleDataclass) is False

    def test_is_pydantic_model_false_builtin(self, model_factory):
        assert model_factory._is_pydantic_model(str) is False

    def test_is_pydantic_model_import_error(self, model_factory):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert model_factory._is_pydantic_model(SampleDataclass) is False

    def test_instantiate_dataclass(self, model_factory):
        raw = {"name": "test", "value": 1.5}
        result = model_factory.instantiate("config", raw, SampleDataclass)
        assert isinstance(result, SampleDataclass)
        assert result.name == "test"
        assert result.value == 1.5

    def test_instantiate_dataclass_directly(self, model_factory):
        raw = {"name": "direct", "value": 2.0}
        result = model_factory.instantiate_dataclass(raw, SampleDataclass)
        assert isinstance(result, SampleDataclass)
        assert result.name == "direct"

    def test_instantiate_dataclass_non_dict(self, model_factory):
        """When raw_value is not a dict, tries empty instantiation which fails."""
        with pytest.raises(TypeError):
            model_factory.instantiate_dataclass("not a dict", SampleDataclass)

    def test_instantiate_dataclass_invalid_fields(self, model_factory):
        raw = {"wrong_field": "value"}
        with pytest.raises(ModelInstantiationError):
            model_factory.instantiate("config", raw, SampleDataclass)

    def test_instantiate_unsupported_type_returns_raw(self, model_factory):
        raw = 42
        result = model_factory.instantiate("threshold", raw, int)
        assert result is raw

    def test_instantiate_unsupported_type_str(self, model_factory):
        raw = "hello"
        result = model_factory.instantiate("name", raw, str)
        assert result is raw
