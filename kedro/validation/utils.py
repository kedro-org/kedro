"""Shared utilities for the validation framework."""

from __future__ import annotations

import dataclasses
import inspect
import types
from typing import Any, Union, get_args, get_origin

try:
    import pydantic
except ImportError:  # pragma: no cover
    pydantic = None  # type: ignore[assignment]

from .exceptions import ParameterValidationError

_MISSING = object()


def _unwrap_optional(tp: type) -> type:
    """Unwrap ``Optional[X]`` / ``X | None`` to ``X``.

    If the type is a union of exactly one non-None type and ``NoneType``,
    return the non-None type. Otherwise return the original type unchanged.
    """
    if get_origin(tp) is Union or isinstance(tp, types.UnionType):
        args = [a for a in get_args(tp) if a is not type(None)]
        if len(args) == 1:
            return args[0]  # type: ignore[no-any-return]
    return tp


def _is_optional(tp: type) -> bool:
    """Return True if ``tp`` is ``Optional[X]`` (i.e. ``X | None``)."""
    if get_origin(tp) is Union or isinstance(tp, types.UnionType):
        return type(None) in get_args(tp)
    return False


def is_pydantic_model(value: Any) -> bool:
    """Check if a value is a Pydantic model instance."""
    if pydantic is None:
        return False
    return isinstance(value, pydantic.BaseModel)


def is_pydantic_class(cls: type) -> bool:
    """Check if a type is a Pydantic model class."""
    if pydantic is None:
        return False
    return inspect.isclass(cls) and issubclass(cls, pydantic.BaseModel)


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

    Returns ``_MISSING`` if the key is not found under either strategy,
    so callers can distinguish "key absent" from "key present with None value".
    """
    # Flat key takes priority (handles namespace params, e.g. "demo.config")
    if path in data:
        return data[path]

    if "." not in path:
        return _MISSING if path not in data else data[path]

    keys = path.split(".")
    value = data

    for key in keys:
        if isinstance(value, dict) and key in value:
            value = value[key]
        else:
            return _MISSING

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
