"""Tests for kedro.validation.utils."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from kedro.validation.utils import (
    get_typed_fields,
    is_pydantic_class,
    is_pydantic_model,
)

from .conftest import PYDANTIC_AVAILABLE, SampleDataclass

if PYDANTIC_AVAILABLE:
    from .conftest import SamplePydanticModel


class TestIsPydanticModel:
    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_pydantic_instance_returns_true(self):
        instance = SamplePydanticModel(test_size=0.2, random_state=3)
        assert is_pydantic_model(instance) is True

    def test_dict_returns_false(self):
        assert is_pydantic_model({"x": 1}) is False

    def test_dataclass_returns_false(self):
        instance = SampleDataclass(name="test", value=1.0)
        assert is_pydantic_model(instance) is False

    def test_string_returns_false(self):
        assert is_pydantic_model("hello") is False

    def test_returns_false_when_pydantic_not_installed(self):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert is_pydantic_model({"x": 1}) is False


class TestIsPydanticClass:
    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_pydantic_class_returns_true(self):
        assert is_pydantic_class(SamplePydanticModel) is True

    def test_dataclass_returns_false(self):
        assert is_pydantic_class(SampleDataclass) is False

    def test_builtin_type_returns_false(self):
        assert is_pydantic_class(str) is False

    def test_dict_type_returns_false(self):
        assert is_pydantic_class(dict) is False

    def test_returns_false_when_pydantic_not_installed(self):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert is_pydantic_class(SampleDataclass) is False


class TestGetTypedFields:
    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_pydantic_model(self):
        instance = SamplePydanticModel(test_size=0.2, random_state=3)
        result = get_typed_fields(instance)
        assert result == {"test_size": 0.2, "random_state": 3}

    def test_dataclass(self):
        instance = SampleDataclass(name="test", value=1.5)
        result = get_typed_fields(instance)
        assert result == {"name": "test", "value": 1.5}

    def test_dict_returns_none(self):
        assert get_typed_fields({"x": 1}) is None

    def test_string_returns_none(self):
        assert get_typed_fields("hello") is None

    def test_dataclass_type_returns_none(self):
        assert get_typed_fields(SampleDataclass) is None

    @pytest.mark.skipif(not PYDANTIC_AVAILABLE, reason="Pydantic not installed")
    def test_preserves_nested_pydantic(self):
        from pydantic import BaseModel

        class Inner(BaseModel):
            value: int

        class Outer(BaseModel):
            inner: Inner

        outer = Outer(inner=Inner(value=42))
        result = get_typed_fields(outer)
        assert isinstance(result["inner"], Inner)

    def test_returns_none_when_pydantic_not_installed(self):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert get_typed_fields({"x": 1}) is None
