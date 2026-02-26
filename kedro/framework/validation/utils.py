"""Shared utilities for the validation framework."""

from __future__ import annotations

import inspect
from typing import Any


def is_pydantic_model(value: Any) -> bool:
    """Check if the given value is a Pydantic model instance.

    Args:
        value: The value to check.

    Returns:
        True if the value is an instance of ``pydantic.BaseModel``, False otherwise.
        Returns False if pydantic is not installed.

    Example:
    ```python
    from pydantic import BaseModel


    class MyModel(BaseModel):
        x: int = 1


    is_pydantic_model(MyModel(x=1))  # True
    is_pydantic_model({"x": 1})  # False
    ```
    """
    try:
        import pydantic

        return isinstance(value, pydantic.BaseModel)
    except ImportError:
        return False


def is_pydantic_class(cls: type) -> bool:
    """Check if the given type is a Pydantic model class.

    Args:
        cls: The type to check.

    Returns:
        True if the type is a subclass of ``pydantic.BaseModel``, False otherwise.
        Returns False if pydantic is not installed.

    Example:
    ```python
    from pydantic import BaseModel


    class MyModel(BaseModel):
        x: int = 1


    is_pydantic_class(MyModel)  # True
    is_pydantic_class(dict)  # False
    ```
    """
    try:
        import pydantic

        return inspect.isclass(cls) and issubclass(cls, pydantic.BaseModel)
    except ImportError:
        return False
