"""Dataclass models for Kedro inspection snapshots."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ProjectMetadataSnapshot:
    """Read-only snapshot of project metadata derived from ``pyproject.toml``.

    Attributes:
        project_name: Human-readable project name.
        package_name: Python package name for the project.
        kedro_version: Kedro package version currently running.
    """

    project_name: str
    package_name: str
    kedro_version: str


@dataclass
class DatasetSnapshot:
    """Read-only snapshot of a catalog dataset entry.

    Attributes:
        name: Dataset name as it appears in the catalog.
        type: Dataset type string (e.g. ``"pandas.CSVDataset"``).
        filepath: File path if present in config, or ``None``.
    """

    name: str
    type: str
    filepath: str | None = None
