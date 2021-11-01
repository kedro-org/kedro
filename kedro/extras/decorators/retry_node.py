"""
This module contains the retry decorator, which can be used as
``Node`` decorators to retry nodes. See ``kedro.pipeline.node.decorate``
"""

import logging
from functools import wraps
from time import sleep
from typing import Callable, Type


def retry(
    exceptions: Type[Exception] = Exception, n_times: int = 1, delay_sec: float = 0
) -> Callable:
    """
    Catches exceptions from the wrapped function at most n_times and then
    bundles and propagates them.

    **Make sure your function does not mutate the arguments**

    Args:
        exceptions: The superclass of exceptions to catch.
            By default catch all exceptions.
        n_times: At most let the function fail n_times. The bundle the
            errors and propagate them. By default retry only once.
        delay_sec: Delay between failure and next retry in seconds

    Returns:
        The original function with retry functionality.

    """

    def _retry(func: Callable):
        @wraps(func)
        def _wrapper(*args, **kwargs):
            counter = n_times
            errors = []
            while counter >= 0:
                try:
                    return func(*args, **kwargs)
                # pylint: disable=broad-except
                except exceptions as exc:
                    errors.append(exc)
                    if counter != 0:
                        sleep(delay_sec)
                counter -= 1

            if errors:
                log = logging.getLogger(__name__)
                log.error(
                    "Function `%s` failed %i times. Errors:\n", func.__name__, n_times
                )
                log.error("\n".join(str(err) for err in errors))
                log.error("Raising last exception")
                raise errors[-1]

        return _wrapper

    return _retry
