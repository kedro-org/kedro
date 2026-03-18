"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from kedro.framework.project import pipelines
from kedro.framework.startup import bootstrap_project
from kedro.inspection.helper import (
    _get_parameter_keys,
    _make_config_loader,
    _resolve_factory_patterns,
)
from kedro.inspection.models import (
    NodeSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    DatasetSnapshot, 
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)
from kedro.config import MissingConfigException

if TYPE_CHECKING:
    from kedro.config import AbstractConfigLoader
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

def _build_dataset_snapshots(
    config_loader: AbstractConfigLoader,
) -> dict[str, DatasetSnapshot]:
    """Build a ``DatasetSnapshot`` for every entry in the catalog configuration.

    Args:
        config_loader: Config loader instance.

    Returns:
        Mapping of dataset name to its snapshot.
    """
    try:
        conf_catalog: dict[str, Any] = config_loader["catalog"]
    except (KeyError, MissingConfigException):
        return {}

    return {
        ds_name: DatasetSnapshot(
            name=ds_name,
            type=ds_config.get("type", ""),
            filepath=ds_config.get("filepath"),
        )
        for ds_name, ds_config in conf_catalog.items()
        if not ds_name.startswith("_")  # skip YAML interpolation anchors
    }


def _build_project_snapshot(
    project_path: str | Path, env: str | None = None
) -> ProjectSnapshot:
    """Build a ``ProjectSnapshot`` for the Kedro project at project_path.

    Args:
        project_path: Path to the project root directory (the directory that
            contains ``pyproject.toml``).
        env: Optional run environment override (e.g. ``"staging"``).
            When ``None`` the default run environment from the project
            settings is used.

    Returns:
        A fully populated ``ProjectSnapshot``.
    """
    project_path = Path(project_path)

    metadata = bootstrap_project(project_path)
    config_loader = _make_config_loader(project_path, env=env)

    metadata_snapshot = _build_project_metadata_snapshot(metadata)
    pipeline_snapshots = _build_pipeline_snapshots()
    dataset_snapshots = _build_dataset_snapshots(config_loader)

    # [TODO: Need to confirm with the team if we should resolve it or
    # keep patterns as is for snapshot as patterns are runtime resolutions]
    dataset_snapshots = _resolve_factory_patterns(dataset_snapshots, pipeline_snapshots)

    parameter_keys = _get_parameter_keys(config_loader)

    return ProjectSnapshot(
        metadata=metadata_snapshot,
        pipelines=pipeline_snapshots,
        datasets=dataset_snapshots,
        parameters=parameter_keys,
    )
