import warnings
from collections.abc import Callable
from functools import wraps


class KedroExperimentalWarning(UserWarning):
    """Warning raised when using an experimental Kedro feature."""


def experimental(obj: Callable | type):
    """Mark a function or class as experimental.

    Emits a KedroExperimentalWarning when used/instantiated.
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
