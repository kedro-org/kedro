"""Shared utilities for the validation framework."""

from __future__ import annotations

import dataclasses
import inspect
from typing import Any

from .exceptions import ParameterValidationError


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


def resolve_nested_dict_path(data: dict, path: str) -> Any:
    """Resolve a dot-separated path in a nested dictionary.

    Returns None if any key in the path is missing.
    """
    # If namespaced params use flat dotted keys (e.g. "demo.config"),
    # check for a literal match before treating dots as path separators.
    if path in data:
        return data[path]

    if "." not in path:
        return None

    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return None

    return value


def set_nested_dict_value(data: dict, path: str, value: Any) -> None:
    """Set a value at a dot-separated path, creating intermediate dicts as needed.

    Raises:
        ParameterValidationError: If an intermediate key is not a dictionary.
    """
    if path in data:
        data[path] = value
        return

    if "." not in path:
        data[path] = value
        return

    keys = path.split(".")
    current = data

    for key in keys[:-1]:
        if key not in current:
            current[key] = {}
        elif not isinstance(current[key], dict):
            raise ParameterValidationError(
                f"Cannot set nested value '{path}': "
                f"intermediate key '{key}' is not a dictionary"
            )
        current = current[key]

    current[keys[-1]] = value
