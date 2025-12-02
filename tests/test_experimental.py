import warnings

import pytest

from kedro.experimental import KedroExperimentalWarning, experimental


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


def test_class_has_marker():
    assert getattr(SampleClass, "__kedro_experimental__", False) is True


def test_silencing_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=KedroExperimentalWarning)
        # Should not raise
        sample_func(1, 2)
        SampleClass(3)
