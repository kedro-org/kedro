"""Tests for kedro.validation.utils."""

from __future__ import annotations

from unittest.mock import patch

import pytest

from kedro.validation.utils import is_pydantic_class, is_pydantic_model

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
