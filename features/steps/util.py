"""Common functions for e2e testing."""

from __future__ import annotations

import os
import re
from contextlib import contextmanager
from time import sleep, time
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable, Iterator
    from pathlib import Path


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


def clean_up_log(stdout: str) -> str:
    """
    Cleans up log output by removing duplicate lines, extra whitespaces,
    and log levels (INFO, WARNING, ERROR) along with .py filenames.

    Args:
        stdout (str): The log output to be cleaned.

    Returns:
        str: Cleaned log output without unnecessary information.
    """
    cleaned_lines = []
    already_extracted = set()

    for line in stdout.split("\n"):
        if any(word in line for word in ["WARNING", "INFO", "ERROR"]):
            # Remove log levels and .py filenames
            cleaned_line = re.sub(r"\b(INFO|WARNING|ERROR)\b|\s+\w+\.py:\d+", "", line)
            cleaned_lines.append(cleaned_line.strip())
            already_extracted.add(line)
        elif line not in already_extracted:
            cleaned_lines.append(line)

    cleaned_output = "\n".join(cleaned_lines)
    cleaned_output = re.sub(r"\s+", " ", cleaned_output)

    return cleaned_output.strip()
