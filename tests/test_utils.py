"""Test a set of helper functions being used across kedro components."""

import warnings
from typing import Any, NoReturn, TypeVar

import pytest

from kedro.utils import KedroExperimentalWarning, experimental, load_obj

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


@experimental
def sample_func(a, b):
    return a + b


@experimental
class SampleClass:
    def __init__(self, x):
        self.x = x


def test_function_emits_warning():
    with pytest.warns(KedroExperimentalWarning) as record:
        result = sample_func(2, 3)

    assert result == 5
    assert len(record) == 1
    assert "sample_func is experimental" in str(record[0].message)


def test_function_has_marker_and_wrapped():
    assert getattr(sample_func, "__kedro_experimental__", False) is True
    assert hasattr(sample_func, "__wrapped__")
    assert sample_func.__wrapped__.__name__ == "sample_func"


def test_class_emits_warning_on_instantiation():
    with pytest.warns(KedroExperimentalWarning) as record:
        obj = SampleClass(10)

    assert obj.x == 10
    assert len(record) == 1
    assert "SampleClass is experimental" in str(record[0].message)


def test_class_has_marker_and_wrapped_init():
    assert getattr(SampleClass, "__kedro_experimental__", False) is True
    assert hasattr(SampleClass.__init__, "__wrapped__")

    # unwrap recovers the original __init__
    original = SampleClass.__init__.__wrapped__
    assert callable(original)
    assert original.__name__ in (
        "__init__",
        "SampleClass",
    )  # depending on inline definition style


def test_class_unwrap_recovers_original_init():
    import inspect

    assert inspect.unwrap(SampleClass.__init__).__name__ == "__init__"


def test_silencing_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
        # Should not raise
        sample_func(1, 2)
        SampleClass(3)


def test_experimental_non_callable_passthrough():
    """Non-callable objects should be returned unchanged with no warnings emitted."""
    original = {"a": 1, "b": 2}

    with warnings.catch_warnings(record=True) as w:
        result = experimental(original)

    assert result is original
    assert len(w) == 0
    assert not hasattr(result, "__kedro_experimental__")


def test_experimental_injects_docstring_function():
    @experimental
    def sample():
        """Original function docs."""
        return 42

    assert sample.__doc__.startswith('!!! warning "Experimental"')
    assert "Original function docs." in sample.__doc__
    assert "experimental" in sample.__doc__.lower()


def test_experimental_injects_docstring_class():
    @experimental
    class Foo:
        """Test class documentation."""

        pass

    assert Foo.__doc__.startswith('!!! warning "Experimental"')
    assert "Test class documentation." in Foo.__doc__


def test_experimental_docstring_not_duplicated():
    @experimental
    @experimental
    def func():
        """Docs."""
        return True

    assert func.__doc__.count('!!! warning "Experimental"') == 1


def test_experimental_warning_and_docstring_together():
    @experimental
    def fn(x):
        return x * 2

    with pytest.warns(KedroExperimentalWarning):
        fn(10)

    assert fn.__doc__.startswith('!!! warning "Experimental"')


def test_experimental_function_warns_once():
    @experimental
    def foo(x):
        return x + 1

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        foo(1)  # warns
        foo(2)  # no warning
        foo(3)  # no warning

    assert len([x for x in w if issubclass(x.category, KedroExperimentalWarning)]) == 1


def test_experimental_class_warns_once():
    @experimental
    class A:
        def __init__(self, x):
            self.x = x

    with warnings.catch_warnings(record=True) as w:
        warnings.simplefilter("always")
        A(1)  # warns
        A(2)  # no warning
        A(3)  # no warning

    assert len([x for x in w if issubclass(x.category, KedroExperimentalWarning)]) == 1
