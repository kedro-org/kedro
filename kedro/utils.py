"""This module provides a set of helper functions being used across different components
of kedro package.
"""
import importlib
import os
from pathlib import Path
from typing import Any, Union

_PYPROJECT = "pyproject.toml"


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
    return getattr(module_obj, obj_name)


def _is_databricks() -> bool:
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def _is_project(project_path: Union[str, Path]) -> bool:
    metadata_file = Path(project_path).expanduser().resolve() / _PYPROJECT
    if not metadata_file.is_file():
        return False

    try:
        return "[tool.kedro]" in metadata_file.read_text(encoding="utf-8")
    except Exception:  # noqa: broad-except
        return False


def _find_kedro_project(current_dir: Path) -> Any:  # pragma: no cover
    paths_to_check = [current_dir] + list(current_dir.parents)
    for parent_dir in paths_to_check:
        if _is_project(parent_dir):
            return parent_dir
    return None
