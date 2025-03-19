"""This module provides a set of helper functions being used across different components
of kedro package.
"""

import importlib
import logging
import os
import re
from pathlib import Path
from typing import Any, Optional, Union
from urllib.parse import urlsplit

_PYPROJECT = "pyproject.toml"

# Protocols
HTTP_PROTOCOLS = ("http", "https")
CLOUD_PROTOCOLS = (
    "abfs",
    "abfss",
    "adl",
    "gcs",
    "gdrive",
    "gs",
    "oci",
    "oss",
    "s3",
    "s3a",
    "s3n",
)
PROTOCOL_DELIMITER = "://"


def _parse_filepath(filepath: str) -> dict[str, str]:
    """Split filepath on protocol and path. Based on `fsspec.utils.infer_storage_options`.

    Args:
        filepath: Either local absolute file path or URL (s3://bucket/file.csv)

    Returns:
        Parsed filepath.
    """
    if (
        re.match(r"^[a-zA-Z]:[\\/]", filepath)
        or re.match(r"^[a-zA-Z0-9]+://", filepath) is None
    ):
        return {"protocol": "file", "path": filepath}

    parsed_path = urlsplit(filepath)
    protocol = parsed_path.scheme or "file"

    if protocol in HTTP_PROTOCOLS:
        return {"protocol": protocol, "path": filepath}

    path = parsed_path.path
    if protocol == "file":
        windows_path = re.match(r"^/([a-zA-Z])[:|]([\\/].*)$", path)
        if windows_path:
            path = ":".join(windows_path.groups())

    if parsed_path.query:
        path = f"{path}?{parsed_path.query}"
    if parsed_path.fragment:
        path = f"{path}#{parsed_path.fragment}"

    options = {"protocol": protocol, "path": path}

    if parsed_path.netloc and protocol in CLOUD_PROTOCOLS:
        host_with_port = parsed_path.netloc.rsplit("@", 1)[-1]
        host = host_with_port.rsplit(":", 1)[0]
        options["path"] = host + options["path"]
        # - Azure Data Lake Storage Gen2 URIs can store the container name in the
        #   'username' field of a URL (@ syntax), so we need to add it to the path
        # - Oracle Cloud Infrastructure (OCI) Object Storage filesystem (ocifs) also
        #   uses the @ syntax for I/O operations: "oci://bucket@namespace/path_to_file"
        if protocol in ["abfss", "oci"] and parsed_path.username:
            options["path"] = parsed_path.username + "@" + options["path"]

    return options


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


def is_kedro_project(project_path: Union[str, Path]) -> bool:
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


def find_kedro_project(current_dir: Path) -> Any:  # pragma: no cover
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
        if is_kedro_project(parent_dir):
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
