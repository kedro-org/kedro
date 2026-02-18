from __future__ import annotations

from kedro.framework.validation import ValidationError
from kedro.framework.validation.exceptions import ModelInstantiationError

from .conftest import SampleDataclass


class TestValidationError:
    def test_basic_error(self):
        error = ValidationError("something failed")
        assert str(error) == "something failed"
        assert error.source_key is None
        assert error.errors == []

    def test_error_with_source_key(self):
        error = ValidationError("bad param", source_key="model_options")
        assert error.source_key == "model_options"

    def test_error_with_errors_list(self):
        errors = ["missing field x", "invalid type y"]
        error = ValidationError("validation failed", errors=errors)
        assert error.errors == errors

    def test_error_with_all_fields(self):
        error = ValidationError("failed", source_key="config", errors=["err1", "err2"])
        assert str(error) == "failed"
        assert error.source_key == "config"
        assert error.errors == ["err1", "err2"]


class TestModelInstantiationError:
    def test_basic_instantiation_error(self):
        original = ValueError("bad value")
        error = ModelInstantiationError(
            "failed to instantiate",
            source_key="model_options",
            model_type=SampleDataclass,
            original_error=original,
        )
        assert str(error) == "failed to instantiate"
        assert error.source_key == "model_options"
        assert error.model_type == SampleDataclass
        assert error.original_error == original

    def test_instantiation_error_without_original(self):
        error = ModelInstantiationError(
            "failed",
            source_key="config",
            model_type=SampleDataclass,
            original_error=None,
        )
        assert error.original_error is None
        assert error.model_type == SampleDataclass
