"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro.inspection.models import ProjectMetadataSnapshot

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata


def _build_project_metadata_snapshot(
    metadata: ProjectMetadata,
) -> ProjectMetadataSnapshot:
    """Build a :class:`ProjectMetadataSnapshot` from a :class:`ProjectMetadata` namedtuple.

    Performs no file I/O; all information is taken directly from *metadata*,
    which is produced by :func:`kedro.framework.startup.bootstrap_project`.

    Args:
        metadata: Project metadata namedtuple returned by ``bootstrap_project()``.

    Returns:
        Read-only snapshot of the project's identity metadata.
    """
    return ProjectMetadataSnapshot(
        project_name=metadata.project_name,
        package_name=metadata.package_name,
        kedro_version=metadata.kedro_init_version,
    )
