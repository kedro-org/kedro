"""This module provides a set of helper functions being used across different components
of kedro package.
"""
import importlib
from typing import Any
from warnings import warn


def load_obj(obj_path: str, default_obj_path: str = "") -> Any:
    """Extract an object from a given path.

    Args:
        obj_path: Path to an object to be extracted, including the object name.
        default_obj_path: Default object path.

    Returns:
        Extracted object.

    Raises:
        AttributeError: When the object does not have the given named attribute.

    """
    obj_path_list = obj_path.rsplit(".", 1)
    obj_path = obj_path_list.pop(0) if len(obj_path_list) > 1 else default_obj_path
    obj_name = obj_path_list[0]
    module_obj = importlib.import_module(obj_path)
    if not hasattr(module_obj, obj_name):
        raise AttributeError(f"Object '{obj_name}' cannot be loaded from '{obj_path}'.")
    return getattr(module_obj, obj_name)


class DeprecatedClassMeta(type):
    """Metaclass for constructing deprecated aliases of renamed classes.

    Code implementation copied from https://stackoverflow.com/a/52087847
    """

    def __new__(mcs, name, bases, classdict, *args, **kwargs):
        alias = classdict.get("_DeprecatedClassMeta__alias")

        if alias is not None:

            def new(mcs, *args, **kwargs):
                alias = getattr(mcs, "_DeprecatedClassMeta__alias")

                if alias is not None:
                    warn(
                        f"{mcs.__name__} has been renamed to {alias.__name__}, and the "
                        f"alias will be removed Kedro 0.19.0",
                        DeprecationWarning,
                        stacklevel=2,
                    )

                return alias(*args, **kwargs)

            classdict["__new__"] = new
            classdict["_DeprecatedClassMeta__alias"] = alias

        fixed_bases = []

        for base in bases:
            alias = getattr(base, "_DeprecatedClassMeta__alias", None)

            if alias is not None:
                warn(
                    f"{base.__name__} has been renamed to {alias.__name__}, and the "
                    f"alias will be removed in Kedro 0.19.0",
                    DeprecationWarning,
                    stacklevel=2,
                )

            # Avoid duplicate base classes.
            base = alias or base
            if base not in fixed_bases:
                fixed_bases.append(base)

        fixed_bases = tuple(fixed_bases)

        return super().__new__(mcs, name, fixed_bases, classdict, *args, **kwargs)

    def __instancecheck__(cls, instance):
        return any(
            cls.__subclasscheck__(c) for c in [type(instance), instance.__class__]
        )

    def __subclasscheck__(cls, subclass):
        return subclass is cls or issubclass(subclass, getattr(cls, "_DeprecatedClassMeta__alias"))
