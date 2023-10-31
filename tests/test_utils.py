"""Test a set of helper functions being used across kedro components."""

import pytest

from kedro.utils import load_obj


class DummyClass:
    pass


class TestExtractObject:
    def test_load_obj(self):
        extracted_obj = load_obj("tests.test_utils.DummyClass")
        assert extracted_obj is DummyClass

    def test_load_obj_default_path(self):
        extracted_obj = load_obj("DummyClass", "tests.test_utils")
        assert extracted_obj is DummyClass

    def test_load_obj_invalid_attribute(self):
        with pytest.raises(
            AttributeError, match=r"Object 'InvalidClass' cannot be loaded"
        ):
            load_obj("InvalidClass", "tests.test_utils")

    def test_load_obj_invalid_module(self):
        with pytest.raises(ImportError, match=r"No module named 'missing_path'"):
            load_obj("InvalidClass", "missing_path")
