"""This module provides a set of helper functions being used across different components
of kedro package.
"""

import importlib
import logging
import os
from pathlib import Path
from typing import Any, Optional, Union

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
    """Evaluate if the current run environment is Databricks or not.

    Useful to tailor environment-dependent activities like Kedro magic commands
    or logging features that Databricks doesn't support.

    Returns:
        True if run environment is Databricks, otherwise False.
    """
    return "DATABRICKS_RUNTIME_VERSION" in os.environ


def _is_project(project_path: Union[str, Path]) -> bool:
    """Evaluate if a given path is a root directory of a Kedro project or not.

    Args:
        project_path: Path to be tested for being a root of a Kedro project.

    Returns:
        True if a given path is a root directory of a Kedro project, otherwise False.
    """
    metadata_file = Path(project_path).expanduser().resolve() / _PYPROJECT
    if not metadata_file.is_file():
        return False

    try:
        return "[tool.kedro]" in metadata_file.read_text(encoding="utf-8")
    except Exception:
        return False


def _find_kedro_project(current_dir: Path) -> Any:  # pragma: no cover
    """Given a path, find a Kedro project associated with it.

    Can be:
        - Itself, if a path is a root directory of a Kedro project.
        - One of its parents, if self is not a Kedro project but one of the parent path is.
        - None, if neither self nor any parent path is a Kedro project.

    Returns:
        Kedro project associated with a given path,
        or None if no relevant Kedro project is found.
    """
    paths_to_check = [current_dir, *list(current_dir.parents)]
    for parent_dir in paths_to_check:
        if _is_project(parent_dir):
            return parent_dir
    return None


def _has_rich_handler(logger: Optional[logging.Logger] = None) -> bool:
    """Returns true if the logger has a RichHandler attached."""
    if not logger:
        logger = logging.getLogger()  # User root by default
    try:
        from rich.logging import RichHandler
    except ImportError:
        return False
    return any(isinstance(handler, RichHandler) for handler in logger.handlers)


def _format_rich(value: str, markup: str) -> str:
    """Format string with rich markup"""
    return f"[{markup}]{value}[/{markup}]"
