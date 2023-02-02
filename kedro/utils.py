"""This module provides a set of helper functions being used across different components
of kedro package.
"""
import importlib
import tarfile
import zipfile
from pathlib import Path
from typing import Any


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


def _is_within_directory(directory, target):
    abs_directory = directory.resolve()
    abs_target = target.resolve()
    return (abs_directory in abs_target.parents) or (abs_directory == abs_target)


def safe_extract(archive, path):
    """Safely extract tar or zip files."""
    if isinstance(archive, tarfile.TarFile):
        for member in archive.getnames():
            member_path = Path(path) / member
            if not _is_within_directory(Path(path), member_path):
                raise Exception("Failed to safely extract tar file.")
    if isinstance(archive, zipfile.ZipFile):
        for member in archive.namelist():
            member_path = Path(path) / member
            if not _is_within_directory(Path(path), member_path):
                raise Exception("Failed to safely extract zip file.")
    archive.extractall(path)
