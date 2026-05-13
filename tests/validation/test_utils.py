"""Tests for kedro.validation.utils."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from pydantic import BaseModel

from kedro.validation.exceptions import ParameterValidationError
from kedro.validation.utils import (
    get_typed_fields,
    is_pydantic_class,
    is_pydantic_model,
    resolve_nested_dict_path,
    set_nested_dict_value,
)

from .conftest import SampleDataclass, SamplePydanticModel


class TestIsPydanticModel:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (SamplePydanticModel(test_size=0.2, random_state=3), True),
            ({"x": 1}, False),
            (SampleDataclass(name="test", value=1.0), False),
            ("hello", False),
        ],
    )
    def test_is_pydantic_model(self, value, expected):
        assert is_pydantic_model(value) is expected

    def test_returns_false_when_pydantic_not_installed(self):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert is_pydantic_model({"x": 1}) is False


class TestIsPydanticClass:
    @pytest.mark.parametrize(
        "cls,expected",
        [
            (SamplePydanticModel, True),
            (SampleDataclass, False),
            (str, False),
            (dict, False),
        ],
    )
    def test_is_pydantic_class(self, cls, expected):
        assert is_pydantic_class(cls) is expected

    def test_returns_false_when_pydantic_not_installed(self):
        with patch.dict("sys.modules", {"pydantic": None}):
            assert is_pydantic_class(SampleDataclass) is False


class TestGetTypedFields:
    def test_pydantic_model(self):
        instance = SamplePydanticModel(test_size=0.2, random_state=3)
        result = get_typed_fields(instance)
        assert result == {"test_size": 0.2, "random_state": 3}

    def test_dataclass(self):
        instance = SampleDataclass(name="test", value=1.5)
        result = get_typed_fields(instance)
        assert result == {"name": "test", "value": 1.5}

    @pytest.mark.parametrize(
        "value",
        [{"x": 1}, "hello", 42, None],
    )
    def test_non_structured_returns_none(self, value):
        assert get_typed_fields(value) is None

    def test_dataclass_type_returns_none(self):
        assert get_typed_fields(SampleDataclass) is None

    def test_preserves_nested_pydantic(self):
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


class TestResolveNestedDictPath:
    def test_flat_key(self):
        data = {"test_size": 0.2}
        assert resolve_nested_dict_path(data, "test_size") == 0.2

    def test_nested_key(self):
        data = {"model": {"options": {"test_size": 0.2}}}
        assert resolve_nested_dict_path(data, "model.options.test_size") == 0.2

    def test_missing_flat_key(self):
        data = {"test_size": 0.2}
        assert resolve_nested_dict_path(data, "missing") is None

    def test_missing_nested_key(self):
        data = {"model": {"options": {}}}
        assert resolve_nested_dict_path(data, "model.options.missing") is None

    def test_intermediate_not_dict(self):
        data = {"model": "not_a_dict"}
        assert resolve_nested_dict_path(data, "model.options") is None

    def test_namespace_flat_key(self):
        """Namespaced params are stored as flat dotted keys."""
        data = {"demo.config": {"my_name": "dummy"}}
        assert resolve_nested_dict_path(data, "demo.config") == {"my_name": "dummy"}

    def test_flat_key_takes_priority_over_nested(self):
        """When both flat and nested paths exist, flat key wins."""
        data = {"demo.config": "flat", "demo": {"config": "nested"}}
        assert resolve_nested_dict_path(data, "demo.config") == "flat"


class TestSetNestedDictValue:
    def test_flat_key(self):
        data = {}
        set_nested_dict_value(data, "key", "value")
        assert data["key"] == "value"

    def test_nested_key(self):
        data = {"model": {"options": {}}}
        set_nested_dict_value(data, "model.options.test_size", 0.3)
        assert data["model"]["options"]["test_size"] == 0.3

    def test_creates_intermediate_dicts(self):
        data = {}
        set_nested_dict_value(data, "model.options.test_size", 0.3)
        assert data["model"]["options"]["test_size"] == 0.3

    def test_intermediate_not_dict_raises(self):
        data = {"model": "not_a_dict"}
        with pytest.raises(ParameterValidationError, match="not a dictionary"):
            set_nested_dict_value(data, "model.options.test_size", 0.3)

    def test_namespace_flat_key_updated_in_place(self):
        """Namespaced params stored as flat dotted keys are updated directly."""
        data = {"demo.config": {"my_name": "old"}}
        set_nested_dict_value(data, "demo.config", {"my_name": "new"})
        assert data["demo.config"] == {"my_name": "new"}
        assert "demo" not in data
