"""Shared utilities for the validation framework."""

from __future__ import annotations

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
