"""A module containing predefined node decorators in Kedro.
"""

import logging
import time
import warnings
from functools import wraps
from typing import Callable

warnings.simplefilter("default", DeprecationWarning)

warnings.warn(
    "Support for decorators will be deprecated in Kedro 0.18.0. "
    "Please use Hooks to extend the behaviour of a node or pipeline.",
    DeprecationWarning,
)


def _func_full_name(func: Callable):
    if not getattr(func, "__module__", None):
        return getattr(func, "__qualname__", repr(func))
    return f"{func.__module__}.{func.__qualname__}"


def _human_readable_time(elapsed: float):
    mins, secs = divmod(elapsed, 60)
    hours, mins = divmod(mins, 60)

    if hours > 0:
        message = f"{int(hours)}h{int(mins):02}m{int(secs):02}s"
    elif mins > 0:
        message = f"{int(mins)}m{int(secs):02}s"
    elif secs >= 1:
        message = f"{secs:.2f}s"
    else:
        message = f"{secs * 1000.0:.0f}ms"

    return message


def log_time(func: Callable) -> Callable:
    """A function decorator which logs the time taken for executing a function.

    Args:
        func: The function to be logged.

    Returns:
        A wrapped function, which will execute the provided function and log
        the running time.

    """

    @wraps(func)
    def with_time(*args, **kwargs):
        log = logging.getLogger(__name__)
        t_start = time.time()
        result = func(*args, **kwargs)
        t_end = time.time()
        elapsed = t_end - t_start

        log.info(
            "Running %r took %s [%.3fs]",
            _func_full_name(func),
            _human_readable_time(elapsed),
            elapsed,
        )
        return result

    return with_time
