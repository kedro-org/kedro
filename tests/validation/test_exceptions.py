"""Tests for kedro.validation.exceptions."""

from __future__ import annotations

import pytest

from kedro.validation.exceptions import ModelInstantiationError, ValidationError


class TestValidationError:
    def test_basic_error(self):
        error = ValidationError("something failed")
        assert str(error) == "something failed"

    def test_is_exception(self):
        error = ValidationError("bad")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ValidationError, match="param error"):
            raise ValidationError("param error")


class TestModelInstantiationError:
    def test_basic_error(self):
        error = ModelInstantiationError("failed to instantiate")
        assert str(error) == "failed to instantiate"

    def test_is_validation_error_subclass(self):
        error = ModelInstantiationError("failed")
        assert isinstance(error, ValidationError)

    def test_can_be_caught_as_validation_error(self):
        with pytest.raises(ValidationError):
            raise ModelInstantiationError("model failed")
