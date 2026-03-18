"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

from typing import TYPE_CHECKING

from kedro.framework.project import pipelines
from kedro.inspection.models import (
    NodeSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
)

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata
    from kedro.pipeline.node import Node


def _build_project_metadata_snapshot(
    metadata: ProjectMetadata,
) -> ProjectMetadataSnapshot:
    """Build `ProjectMetadataSnapshot` from `ProjectMetadata` NamedTuple.

    Args:
        metadata: Project metadata NamedTuple.

    Returns:
        Read-only snapshot of the project's metadata.
    """
    return ProjectMetadataSnapshot(
        project_name=metadata.project_name,
        package_name=metadata.package_name,
        kedro_version=metadata.kedro_init_version,
    )


def _node_to_snapshot(node: Node) -> NodeSnapshot:
    """Convert a live ``Node`` object to a ``NodeSnapshot``.

    Args:
        node: A Kedro pipeline node.

    Returns:
        Read-only snapshot of the node's structural metadata.
    """
    return NodeSnapshot(
        name=node.name,
        namespace=node.namespace,
        tags=sorted(node.tags),
        inputs=node.inputs,
        outputs=node.outputs,
    )


def _build_pipeline_snapshots() -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Returns:
        List of pipeline snapshots in registry iteration order.
    """
    snapshots = []
    for pipeline_id, pipeline in pipelines.items():
        if pipeline is None:
            continue
        snapshots.append(
            PipelineSnapshot(
                name=pipeline_id,
                nodes=[_node_to_snapshot(_node) for _node in pipeline.nodes],
                inputs=sorted(pipeline.inputs()),
                outputs=sorted(pipeline.outputs()),
            )
        )
    return snapshots
