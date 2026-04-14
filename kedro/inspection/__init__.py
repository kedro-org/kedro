"""Kedro inspection API for read-only project snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro.inspection.snapshot import _build_project_snapshot

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.inspection.models import ProjectSnapshot

__all__ = [
    "get_project_snapshot",
]


def get_project_snapshot(
    project_path: str | Path,
    env: str | None = None,
) -> ProjectSnapshot:
    """Return a read-only snapshot of the Kedro project at *project_path*.

    This is the primary entry point for the inspection API. It initialises
    the project, loads configuration and pipelines, and assembles a
    ``ProjectSnapshot`` without executing any pipeline nodes or writing data.

    Args:
        project_path: Path to the project root directory (the directory that
            contains ``pyproject.toml``).
        env: Optional run environment override (e.g. ``"staging"``). When
            ``None``, the project's default run environment is used.

    Returns:
        A fully populated ``ProjectSnapshot``.
    """
    return _build_project_snapshot(project_path=project_path, env=env)
