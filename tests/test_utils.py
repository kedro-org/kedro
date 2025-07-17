"""Test a set of helper functions being used across kedro components."""

from typing import Any, NoReturn, TypeVar

import pytest

from kedro.utils import load_obj

T = TypeVar("T")


class DummyClass:
    pass


class TestExtractObject:
    def test_load_obj(self):
        extracted_obj = load_obj("tests.test_utils.DummyClass")
        assert extracted_obj is DummyClass

    def test_load_obj_default_path(self):
        extracted_obj = load_obj("DummyClass", "tests.test_utils")
        assert extracted_obj is DummyClass

    def test_load_obj_invalid_module(self):
        with pytest.raises(ImportError, match=r"No module named 'missing_path'"):
            load_obj("InvalidClass", "missing_path")


def identity(input1) -> T:
    """Return the input unchanged."""
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str) -> str:
    """Concatenate two strings."""
    return f"{input1}{input2}"  # pragma: no cover


def triconcat(input1: str, input2: str, input3: str) -> str:
    """Concatenate three strings."""
    return f"{input1}{input2}{input3}"  # pragma: no cover


def constant_output() -> str:
    """Return a constant output string."""
    return "output"  # pragma: no cover


# Runner test utilities
def source() -> str:
    """Return a constant source value."""
    return "stuff"


def sink(arg: Any) -> None:
    """No-op sink function."""
    pass


def fan_in(*args: Any) -> tuple[Any, ...]:
    """Return all arguments as a tuple."""
    return args


def first_arg(*args: Any) -> Any:
    """Return the first argument."""
    return args[0]


def exception_fn(*args: Any) -> NoReturn:
    """Raise a test exception."""
    raise Exception("test exception")


def return_none(arg: Any) -> None:
    """Return None."""
    return None


def return_not_serialisable(arg: Any) -> Any:
    """Return a non-serializable object (lambda)."""
    return lambda x: x


def multi_input_list_output(arg1: Any, arg2: Any, arg3: Any = None) -> list:
    """Return first two arguments as a list."""
    return [arg1, arg2]
