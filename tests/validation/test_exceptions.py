"""Tests for kedro.validation.exceptions."""

from __future__ import annotations

import pytest

from kedro.validation.exceptions import (
    ModelInstantiationError,
    ParameterValidationError,
)


class TestParameterValidationError:
    def test_basic_error(self):
        error = ParameterValidationError("something failed")
        assert str(error) == "something failed"

    def test_is_exception(self):
        error = ParameterValidationError("bad")
        assert isinstance(error, Exception)

    def test_can_be_raised_and_caught(self):
        with pytest.raises(ParameterValidationError, match="param error"):
            raise ParameterValidationError("param error")


class TestModelInstantiationError:
    def test_basic_error(self):
        error = ModelInstantiationError("failed to instantiate")
        assert str(error) == "failed to instantiate"

    def test_is_parameter_validation_error_subclass(self):
        error = ModelInstantiationError("failed")
        assert isinstance(error, ParameterValidationError)

    def test_can_be_caught_as_parameter_validation_error(self):
        with pytest.raises(ParameterValidationError):
            raise ModelInstantiationError("model failed")
