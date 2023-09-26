"""Common functions for e2e testing.
"""
from __future__ import annotations

import os
import re
from contextlib import contextmanager
from pathlib import Path
from time import sleep, time
from typing import Any, Callable, Iterator


@contextmanager
def chdir(path: Path) -> Iterator:
    """Context manager to help execute code in a different directory.

    Args:
        path: directory to change to.

    Yields:
        None
    """
    old_pwd = os.getcwd()
    os.chdir(str(path))
    try:
        yield
    finally:
        os.chdir(old_pwd)


class WaitForException(Exception):
    pass


def wait_for(
    func: Callable,
    timeout_: int = 10,
    print_error: bool = False,
    sleep_for: int = 1,
    **kwargs,
) -> Any:
    """Run specified function until it returns expected result until timeout.

    Args:
        func: Specified function.
        timeout_: Time out in seconds. Defaults to 10.
        print_error: whether any exceptions raised should be printed.
            Defaults to False.
        sleep_for: Execute func every specified number of seconds.
            Defaults to 1.
        **kwargs: Arguments to be passed to func.

    Raises:
         WaitForException: if func doesn't return expected result within the
         specified time.

    Returns:
        Function return.

    """
    end = time() + timeout_
    while time() <= end:
        try:
            result = func(**kwargs)
            return result
        except Exception as err:
            if print_error:
                print(err)

        sleep(sleep_for)
    raise WaitForException(
        f"func: {func}, didn't return within specified timeout: {timeout_}"
    )


def parse_csv(text: str) -> list[str]:
    """Parse comma separated **double quoted** strings in behave steps

    Args:
        text: double quoted comma separated string

    Returns:
        List of string tokens
    """
    return re.findall(r"\"(.+?)\"\s*,?", text)
