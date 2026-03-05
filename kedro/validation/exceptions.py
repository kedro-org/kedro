"""Custom exceptions for the validation framework."""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when parameter validation fails."""

    pass


class ModelInstantiationError(ValidationError):
    """Raised when a typed model (Pydantic/dataclass) fails to instantiate from raw parameters."""

    pass
