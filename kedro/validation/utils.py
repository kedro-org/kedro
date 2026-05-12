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

    Tries the flat key first to handle namespaced parameter keys like
    ``"demo.config"`` that Kedro stores as literal flat keys in the params
    dict. Falls back to nested traversal for truly nested dicts.

    Returns None if the key is not found under either strategy.
    """
    # Flat key takes priority (handles namespace params, e.g. "demo.config")
    if path in data:
        return data[path]

    if "." not in path:
        return data.get(path)

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

    Uses the same flat-key-first strategy as `resolve_nested_dict_path`
    so that namespaced parameter keys like ``"demo.config"`` are updated in
    place rather than written into a nested structure.

    Raises:
        ParameterValidationError: If an intermediate key is not a dictionary.
    """
    # If the flat key already exists, update it directly
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
