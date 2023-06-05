"""Test a set of helper functions being used across kedro components."""

import pytest

from kedro.utils import DeprecatedClassMeta, load_obj


# pylint: disable=too-few-public-methods
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


class NewClass:
    foo = 1


class NewClassSubclass(NewClass):
    pass


class DeprecatedClass(metaclass=DeprecatedClassMeta):
    _DeprecatedClassMeta__alias = NewClass


class DeprecatedClassSubclass(DeprecatedClass):
    foo = 2


class DeprecatedClassSubSubclass(DeprecatedClassSubclass):
    foo = 3


class TestDeprecatedClassMeta:
    def test_is_subclass_of_deprecated_class(self):
        assert issubclass(DeprecatedClass, DeprecatedClass)
        assert issubclass(DeprecatedClassSubclass, DeprecatedClass)
        assert issubclass(DeprecatedClassSubSubclass, DeprecatedClass)
        assert issubclass(NewClass, DeprecatedClass)
        assert issubclass(NewClassSubclass, DeprecatedClass)

    def test_is_subclass_of_new_class(self):
        assert issubclass(DeprecatedClassSubclass, NewClass)
        assert issubclass(DeprecatedClassSubSubclass, NewClass)

    def test_is_instance_of_deprecated_class(self):
        assert isinstance(DeprecatedClass(), DeprecatedClass)
        assert isinstance(DeprecatedClassSubclass(), DeprecatedClass)
        assert isinstance(DeprecatedClassSubSubclass(), DeprecatedClass)
        assert isinstance(NewClass(), DeprecatedClass)
        assert isinstance(NewClassSubclass(), DeprecatedClass)

    def test_is_instance_of_new_class(self):
        assert isinstance(DeprecatedClassSubclass(), NewClass)
        assert isinstance(DeprecatedClassSubSubclass(), NewClass)

    def test_inheritance(self):
        assert NewClass().foo == 1
        assert DeprecatedClass().foo == 1
        assert DeprecatedClassSubclass().foo == 2
        assert DeprecatedClassSubSubclass().foo == 3
