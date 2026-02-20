"""Custom exceptions for validation framework."""

from __future__ import annotations


class ValidationError(Exception):
    """Raised when validation fails."""

    def __init__(
        self,
        message: str,
        source_key: str | None = None,
        errors: list[str] | None = None,
    ):
        """Initialize validation error.

        Args:
            message: Error message
            source_key: The source key that failed validation
            errors: List of specific validation errors
        """
        super().__init__(message)
        self.source_key = source_key
        self.errors = errors or []


class ModelInstantiationError(ValidationError):
    """Raised when model instantiation fails."""

    def __init__(
        self,
        message: str,
        source_key: str,
        model_type: type,
        original_error: Exception | None = None,
    ):
        """Initialize model instantiation error.

        Args:
            message: Error message
            source_key: The source key that failed
            model_type: The model type that failed to instantiate
            original_error: The original exception that caused the failure
        """
        super().__init__(message, source_key)
        self.model_type = model_type
        self.original_error = original_error
