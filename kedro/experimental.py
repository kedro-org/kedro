"""
Experimental API utilities for Kedro.

This module provides the ``@experimental`` decorator and the
``KedroExperimentalWarning`` warning class, enabling the Kedro team to
introduce new features to the codebase while clearly signalling to users
that the API surface is not yet stable.

Any function or class marked with ``@experimental`` will emit a
``KedroExperimentalWarning`` when invoked or instantiated. This mechanism
helps the team gather feedback, iterate quickly, and make informed
decisions about promoting features into the stable API.
"""

import warnings
from collections.abc import Callable
from functools import wraps


class KedroExperimentalWarning(UserWarning):
    """Warning raised when using an experimental Kedro feature."""


def experimental(obj: Callable | type):
    """Mark a function or class as experimental.

    Emits a ``KedroExperimentalWarning`` when invoked (for functions) or
    instantiated (for classes). The original API remains fully usable.

    Args:
        obj: The function or class to wrap.

    Returns:
        A wrapped version of the object that emits warnings on use.

    Example:
    ```python

    @experimental
    def sample_func(a, b):
        return a + b

    @experimental
    class SampleClass:
    def __init__(self, x):
        self.x = x
    ```
    """
    warning_message = (
        f"{obj.__name__} is experimental and may change in future Kedro releases."
    )

    # Function or method
    if callable(obj) and not isinstance(obj, type):

        @wraps(obj)
        def wrapper(*args, **kwargs):
            warnings.warn(
                warning_message, category=KedroExperimentalWarning, stacklevel=2
            )
            return obj(*args, **kwargs)

        setattr(wrapper, "__kedro_experimental__", True)
        setattr(wrapper, "__wrapped__", obj)

        return wrapper

    # Class
    if isinstance(obj, type):
        original_init = obj.__init__

        @wraps(original_init)
        def new_init(self, *args, **kwargs):
            warnings.warn(
                warning_message, category=KedroExperimentalWarning, stacklevel=2
            )
            return original_init(self, *args, **kwargs)

        obj.__init__ = new_init
        setattr(obj, "__kedro_experimental__", True)

        return obj

    return obj
