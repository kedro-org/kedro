"""Kedro inspection API for read-only project snapshot."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro.inspection.snapshot import (
    _build_node_source_snapshot,
    _build_project_snapshot,
)

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.startup import ProjectMetadata
    from kedro.inspection.models import NodeSourceSnapshot, ProjectSnapshot

__all__ = [
    "get_node_source",
    "get_project_snapshot",
]


def get_project_snapshot(
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    metadata: ProjectMetadata | None = None,
) -> ProjectSnapshot:
    """Return a read-only snapshot of the Kedro project.

    This is the primary entry point for the inspection API. It initialises
    the project, loads configuration and pipelines, and assembles a
    ``ProjectSnapshot`` without executing any pipeline nodes or writing data.

    At least one of *project_path* or *metadata* must be supplied.  When both
    are given and point to different directories, *metadata.project_path* takes
    precedence and a ``UserWarning`` is emitted.

    Args:
        project_path: Path to the project root directory (the directory that
            contains ``pyproject.toml``). Optional when *metadata* is provided.
        env: Optional run environment override (e.g. ``"staging"``). When
            ``None``, the project's default run environment is used.
        conf_source: Optional path to the configuration directory. When
            ``None``, defaults to ``<project_path>/<settings.CONF_SOURCE>``.
        metadata: Optional pre-computed ``ProjectMetadata`` returned by a prior
            ``bootstrap_project`` call. When provided, ``bootstrap_project`` is
            skipped. Pass this when calling ``get_project_snapshot`` repeatedly
            in the same process to avoid redundant initialisation.

            For example, in a long-running server the project is bootstrapped
            once at startup and the result is forwarded to every snapshot call::

                # --- server startup ---
                metadata = bootstrap_project(project_path)

                # --- per-request snapshot (bootstrap_project not called again) ---
                snapshot = get_project_snapshot(metadata=metadata)

            The same pattern applies to programmatic callers that need multiple
            snapshots across different environments::

                from kedro.framework.startup import bootstrap_project
                from kedro.inspection import get_project_snapshot

                metadata = bootstrap_project(project_path)
                snapshot_default = get_project_snapshot(metadata=metadata)
                snapshot_staging = get_project_snapshot(env="staging", metadata=metadata)

    Returns:
        A fully populated ``ProjectSnapshot``.
    """
    return _build_project_snapshot(
        project_path=project_path,
        env=env,
        conf_source=conf_source,
        metadata=metadata,
    )


def get_node_source(
    node_name: str,
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    metadata: ProjectMetadata | None = None,
    *,
    include_code: bool = True,
) -> NodeSourceSnapshot:
    """Return source information for a single pipeline node on demand.

    At least one of *project_path* or *metadata* must be supplied.  When both
    are given and point to different directories, *metadata.project_path* takes
    precedence and a ``UserWarning`` is emitted.

    Args:
        node_name: Fully-qualified name of the node to inspect, as returned by
            :attr:`kedro.pipeline.node.Node.name` or listed in
            ``get_project_snapshot().pipelines[i].nodes[j].name``.
        project_path: Path to the project root directory (the directory that
            contains ``pyproject.toml``). Optional when *metadata* is provided.
        env: Optional run environment override (e.g. ``"staging"``).
        conf_source: Optional path to the configuration directory.
        metadata: Optional pre-computed ``ProjectMetadata`` returned by a prior
            ``bootstrap_project`` call.
        include_code: When ``True`` (default) the ``code`` field of the returned
            snapshot contains the source text. Pass ``False`` to retrieve only
            file-path and line-range metadata.

    Returns:
        A :class:`~kedro.inspection.models.NodeSourceSnapshot` for the node.

    Raises:
        KeyError: When no node named *node_name* exists in any registered
            pipeline.
        ValueError: When neither *project_path* nor *metadata* is provided,
            or *env* contains invalid characters.
    """
    return _build_node_source_snapshot(
        node_name=node_name,
        project_path=project_path,
        env=env,
        conf_source=conf_source,
        metadata=metadata,
        include_code=include_code,
    )
