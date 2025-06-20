"""This module provides metadata for a Kedro project."""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import NamedTuple

import toml

from kedro import __version__ as kedro_version
from kedro.framework.project import configure_project

_PYPROJECT = "pyproject.toml"


class ProjectMetadata(NamedTuple):
    """Structure holding project metadata derived from `pyproject.toml`"""

    config_file: Path
    package_name: str
    project_name: str
    project_path: Path
    source_dir: Path
    kedro_init_version: str
    tools: list
    example_pipeline: str


def _version_mismatch_error(kedro_init_version: str) -> str:
    return (
        f"Your Kedro project version {kedro_init_version} does not match Kedro package "
        f"version {kedro_version} you are running. Make sure to update your project "
        f"template. See https://github.com/kedro-org/kedro/blob/main/RELEASE.md "
        f"for how to migrate your Kedro project."
    )


def _get_project_metadata(project_path: Path) -> ProjectMetadata:
    """Read project metadata from `<project_root>/pyproject.toml` config file,
    under the `[tool.kedro]` section.

    Args:
        project_path: Local path to project root directory to look up `pyproject.toml` in.

    Raises:
        RuntimeError: `pyproject.toml` was not found or the `[tool.kedro]` section
            is missing, or config file cannot be parsed.
        ValueError: If project version is different from Kedro package version.
            Note: Project version is the Kedro version the project was generated with.

    Returns:
        A named tuple that contains project metadata.
    """
    pyproject_toml = project_path / _PYPROJECT

    if not pyproject_toml.is_file():
        raise RuntimeError(
            f"Could not find the project configuration file '{_PYPROJECT}' in {project_path}. "
            f"If you have created your project with Kedro "
            f"version <0.17.0, make sure to update your project template. "
            f"See https://github.com/kedro-org/kedro/blob/main/RELEASE.md"
            f"#migration-guide-from-kedro-016-to-kedro-0170 "
            f"for how to migrate your Kedro project."
        )

    try:
        metadata_dict = toml.load(pyproject_toml)
    except Exception as exc:
        raise RuntimeError(f"Failed to parse '{_PYPROJECT}' file.") from exc

    try:
        metadata_dict = metadata_dict["tool"]["kedro"]
    except KeyError as exc:
        raise RuntimeError(
            f"There's no '[tool.kedro]' section in the '{_PYPROJECT}'. "
            f"Please add '[tool.kedro]' section to the file with appropriate "
            f"configuration parameters."
        ) from exc

    mandatory_keys = ["package_name", "project_name", "kedro_init_version"]
    missing_keys = [key for key in mandatory_keys if key not in metadata_dict]
    if missing_keys:
        raise RuntimeError(f"Missing required keys {missing_keys} from '{_PYPROJECT}'.")

    # check the match for major and minor version (skip patch version)
    if (
        metadata_dict["kedro_init_version"].split(".")[:2]
        != kedro_version.split(".")[:2]
    ):
        raise ValueError(_version_mismatch_error(metadata_dict["kedro_init_version"]))

    # Default settings
    source_dir = Path(metadata_dict.get("source_dir", "src")).expanduser()
    source_dir = (project_path / source_dir).resolve()
    metadata_dict["tools"] = metadata_dict.get("tools")
    metadata_dict["example_pipeline"] = metadata_dict.get("example_pipeline")

    metadata_dict["source_dir"] = source_dir
    metadata_dict["config_file"] = pyproject_toml
    metadata_dict["project_path"] = project_path
    metadata_dict.pop("micropkg", {})  # don't include micro-packaging specs

    try:
        return ProjectMetadata(**metadata_dict)
    except TypeError as exc:
        expected_keys = [*mandatory_keys, "source_dir", "tools", "example_pipeline"]
        raise RuntimeError(
            f"Found unexpected keys in '{_PYPROJECT}'. Make sure "
            f"it only contains the following keys: {expected_keys}."
        ) from exc


def _validate_source_path(source_path: Path, project_path: Path) -> None:
    """Validate the source path exists and is relative to the project path.

    Args:
        source_path: Absolute source path.
        project_path: Path to the Kedro project.

    Raises:
        ValueError: If source_path is not relative to project_path.
        NotADirectoryError: If source_path does not exist.
    """
    try:
        source_path.relative_to(project_path)
    except ValueError as exc:
        raise ValueError(
            f"Source path '{source_path}' has to be relative to "
            f"your project root '{project_path}'."
        ) from exc
    if not source_path.exists():
        raise NotADirectoryError(f"Source path '{source_path}' cannot be found.")


def _add_src_to_path(source_dir: Path, project_path: Path) -> None:
    _validate_source_path(source_dir, project_path)

    if str(source_dir) not in sys.path:
        sys.path.insert(0, str(source_dir))

    python_path = os.getenv("PYTHONPATH", "")
    if str(source_dir) not in python_path:
        sep = os.pathsep if python_path else ""
        os.environ["PYTHONPATH"] = f"{source_dir!s}{sep}{python_path}"


def bootstrap_project(project_path: str | Path) -> ProjectMetadata:
    """Run setup required at the beginning of the workflow
    when running in project mode, and return project metadata.
    """

    project_path = Path(project_path).expanduser().resolve()
    metadata = _get_project_metadata(project_path)
    _add_src_to_path(metadata.source_dir, project_path)
    configure_project(metadata.package_name)
    return metadata
