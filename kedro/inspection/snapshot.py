"""Build ProjectSnapshot from a loaded Kedro context (no catalog materialization)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kedro import __version__ as kedro_version
from kedro.framework.project import settings
from kedro.inspection.models import (
    DatasetConfigSnapshot,
    NodeSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.context import KedroContext
    from kedro.framework.startup import ProjectMetadata
    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node


def _metadata_from_kedro(
    metadata: ProjectMetadata, project_path: Path
) -> ProjectMetadataSnapshot:
    """Convert framework ProjectMetadata to inspection ProjectMetadataSnapshot."""
    conf_source = str(project_path / getattr(settings, "CONF_SOURCE", "conf"))
    loader_args = getattr(settings, "CONFIG_LOADER_ARGS", None) or {}
    base_env = loader_args.get("base_env", "base") or "base"
    default_env = loader_args.get("default_run_env", "local") or "local"
    return ProjectMetadataSnapshot(
        project_name=metadata.project_name,
        project_path=str(metadata.project_path.resolve()),
        package_name=metadata.package_name,
        kedro_version=kedro_version,
        source_dir=str(metadata.source_dir),
        environments=[base_env, default_env],
        config_paths=[conf_source],
    )


def _node_to_snapshot(node: Node) -> NodeSnapshot:
    """Convert a Kedro Node to NodeSnapshot (fields match Node API)."""
    return NodeSnapshot(
        name=node.name,
        namespace=node.namespace or None,
        tags=list(node.tags),
        inputs=list(node.inputs),
        outputs=list(node.outputs),
        confirms=list(node.confirms),
    )


def _build_pipeline_snapshot(
    pipeline_id: str,
    pipeline: Pipeline,
    catalog: Any,
) -> tuple[PipelineSnapshot, dict[str, DatasetConfigSnapshot]]:
    """
    Build PipelineSnapshot and dataset configs for one pipeline.
    Uses pipeline.nodes for execution order; never calls catalog.get().
    """
    free_inputs = set(pipeline.inputs())
    node_snapshots: list[NodeSnapshot] = []
    datasets: dict[str, DatasetConfigSnapshot] = {}
    for node in pipeline.nodes:
        node_snapshots.append(_node_to_snapshot(node))
        for ds_name in node.inputs + node.outputs:
            if ds_name in datasets:
                continue
            is_param = ds_name.startswith("params:") or ds_name == "parameters"
            if is_param:
                continue
            try:
                resolved = catalog.config_resolver.resolve_pattern(ds_name)
            except Exception:
                resolved = {}
            ds_type = resolved.get("type", "Unknown")
            datasets[ds_name] = DatasetConfigSnapshot(
                name=ds_name,
                type=ds_type,
                is_free_input=ds_name in free_inputs,
            )
    pipe_snapshot = PipelineSnapshot(
        id=pipeline_id,
        name=pipeline_id,
        nodes=node_snapshots,
        inputs=sorted(pipeline.inputs()),
        outputs=sorted(pipeline.outputs()),
    )
    return pipe_snapshot, datasets


def build_snapshot(
    context: KedroContext,
    metadata: ProjectMetadata,
    has_missing_deps: bool = False,
    mocked_dependencies: list[str] | None = None,
    catalog: CatalogProtocol | None = None,
) -> ProjectSnapshot:
    """
    Build a ProjectSnapshot from a loaded context.
    Does not call catalog.get() or materialize any dataset.

    If catalog is provided (e.g. by inspection to avoid loading params into
    MemoryDataset), it is used instead of context.catalog.
    """
    from kedro.framework.project import pipelines as project_pipelines

    project_path = context.project_path
    catalog = catalog if catalog is not None else context.catalog
    params = context.params
    all_datasets: dict[str, DatasetConfigSnapshot] = {}
    pipeline_snapshots: list[PipelineSnapshot] = []
    for pipe_id, pipeline in project_pipelines.items():
        if pipeline is None:
            continue
        pipe_snap, ds_map = _build_pipeline_snapshot(pipe_id, pipeline, catalog)
        pipeline_snapshots.append(pipe_snap)
        for name, ds_config in ds_map.items():
            if name not in all_datasets:
                all_datasets[name] = ds_config
    pydantic_metadata = _metadata_from_kedro(metadata, project_path)
    return ProjectSnapshot(
        metadata=pydantic_metadata,
        pipelines=pipeline_snapshots,
        datasets=all_datasets,
        parameters=params or {},
        has_missing_deps=has_missing_deps,
        mocked_dependencies=mocked_dependencies or [],
    )
