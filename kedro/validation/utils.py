"""Shared utilities for the validation framework."""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any


def is_pydantic_model(value: Any) -> bool:
    """Check if a value is a Pydantic model instance."""
    try:
        import pydantic

        return isinstance(value, pydantic.BaseModel)
    except ImportError:
        return False


def is_pydantic_class(cls: type) -> bool:
    """Check if a type is a Pydantic model class."""
    try:
        import pydantic

        return inspect.isclass(cls) and issubclass(cls, pydantic.BaseModel)
    except ImportError:
        return False


def get_typed_fields(value: Any) -> dict[str, Any] | None:
    """Extract fields from a typed object (Pydantic model or dataclass).

    Returns None if the value is not a structured type.
    """
    if is_pydantic_model(value):
        return {
            field_name: getattr(value, field_name) for field_name in value.model_fields
        }
    elif dataclasses.is_dataclass(value) and not isinstance(value, type):
        return {f.name: getattr(value, f.name) for f in dataclasses.fields(value)}
    return None
