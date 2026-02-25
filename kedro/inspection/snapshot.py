"""Build ProjectSnapshot without KedroSession or KedroContext.

Two-tier approach:

  Tier 1 — no user dependencies:
    build_metadata_snapshot()  reads pyproject.toml via bootstrap_project
    build_catalog_snapshot()   reads catalog.yml + parameters.yml via OmegaConfigLoader

  Tier 2 — requires user deps installed:
    build_pipeline_snapshots() executes register_pipelines() via _ProjectPipelines;
                                requires configure_project() to have been called first.

  build_snapshot() orchestrates both tiers into a full ProjectSnapshot.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any

from kedro import __version__ as kedro_version
from kedro.framework.project import pipelines as _global_pipelines
from kedro.framework.startup import bootstrap_project
from kedro.inspection.models import (
    DatasetSnapshot,
    NodeSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)

if TYPE_CHECKING:
    from kedro.config import OmegaConfigLoader
    from kedro.framework.startup import ProjectMetadata
    from kedro.io import CatalogConfigResolver
    from kedro.pipeline.node import Node


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _is_parameter(name: str) -> bool:
    return name == "parameters" or name.startswith("params:")


def _is_factory_pattern(key: str) -> bool:
    return "{" in key


def _make_config_loader(project_path: Path, env: str) -> OmegaConfigLoader:
    from kedro.config import OmegaConfigLoader
    from kedro.framework.project import settings

    conf_source = str(project_path / getattr(settings, "CONF_SOURCE", "conf"))
    loader_args = getattr(settings, "CONFIG_LOADER_ARGS", None) or {}
    return OmegaConfigLoader(
        conf_source=conf_source,
        env=env,
        base_env=loader_args.get("base_env", "base"),
        default_run_env=loader_args.get("default_run_env", "local"),
    )


def _node_to_snapshot(node: Node) -> NodeSnapshot:
    return NodeSnapshot(
        name=node.name,
        namespace=node.namespace or None,
        tags=list(node.tags),
        inputs=list(node.inputs),
        outputs=list(node.outputs),
    )


def _enrich_datasets_from_pipelines(
    datasets: dict[str, DatasetSnapshot],
    pipeline_snapshots: list[PipelineSnapshot],
    resolver: CatalogConfigResolver,
) -> None:
    """Tier 2 second pass — two responsibilities:

    1. Add datasets referenced in pipeline node I/O but absent from catalog.yml
       (factory-matched datasets, MemoryDatasets).
    2. Set is_free_input on all datasets — True if consumed but not produced by
       any node across all pipelines.
    """
    free_inputs: set[str] = set()
    for p in pipeline_snapshots:
        free_inputs.update(p.inputs)

    for p in pipeline_snapshots:
        for node in p.nodes:
            for ds_name in node.inputs + node.outputs:
                if _is_parameter(ds_name) or ds_name in datasets:
                    continue
                try:
                    resolved = resolver.resolve_pattern(ds_name) or {}
                except Exception:
                    resolved = {}
                datasets[ds_name] = DatasetSnapshot(
                    name=ds_name,
                    type=resolved.get("type", "MemoryDataset"),
                    filepath=resolved.get("filepath"),
                    is_free_input=ds_name in free_inputs,
                )

    for ds_name, ds in list(datasets.items()):
        if ds_name in free_inputs and not ds.is_free_input:
            datasets[ds_name] = ds.model_copy(update={"is_free_input": True})


# ---------------------------------------------------------------------------
# Public builders — Tier 1 (no user dependencies)
# ---------------------------------------------------------------------------


def build_metadata_snapshot(metadata: ProjectMetadata) -> ProjectMetadataSnapshot:
    """Build from the ProjectMetadata namedtuple returned by bootstrap_project.

    No file I/O — converts the already-parsed namedtuple into a snapshot model.
    """
    return ProjectMetadataSnapshot(
        project_name=metadata.project_name,
        package_name=metadata.package_name,
        kedro_version=kedro_version,
    )


def build_catalog_snapshot(
    project_path: Path,
    env: str,
) -> tuple[dict[str, DatasetSnapshot], list[str]]:
    """Build dataset snapshots and parameter keys from config files only.

    Reads catalog.yml and parameters.yml via OmegaConfigLoader + CatalogConfigResolver.
    No pipeline code is imported. Factory-matched and MemoryDataset entries that are
    only discoverable from pipeline node I/O are not included here.

    Requires configure_project() to have been called (via bootstrap_project) so that
    settings.CONF_SOURCE is available.

    Returns:
        Tuple of (datasets dict, parameter_keys list).
    """
    from kedro.io import CatalogConfigResolver

    loader = _make_config_loader(project_path, env)

    try:
        catalog_config: dict[str, Any] = loader["catalog"]
    except Exception:
        catalog_config = {}

    resolver = CatalogConfigResolver(config=catalog_config)
    datasets: dict[str, DatasetSnapshot] = {}

    for ds_name, raw_config in catalog_config.items():
        if ds_name.startswith("_"):
            continue
        raw = raw_config if isinstance(raw_config, dict) else {}
        if _is_factory_pattern(ds_name):
            # Include the pattern template as-is — concrete instances are only
            # resolvable once pipeline node I/O names are known (Tier 2).
            datasets[ds_name] = DatasetSnapshot(
                name=ds_name,
                type=raw.get("type", "Unknown"),
                filepath=raw.get("filepath"),
                is_pattern=True,
            )
        else:
            try:
                resolved = resolver.resolve_pattern(ds_name) or {}
            except Exception:
                resolved = raw
            datasets[ds_name] = DatasetSnapshot(
                name=ds_name,
                type=resolved.get("type", raw.get("type", "Unknown")),
                filepath=resolved.get("filepath"),
                is_pattern=False,
            )

    try:
        params = loader["parameters"]
        parameter_keys = sorted(params.keys()) if isinstance(params, dict) else []
    except Exception:
        parameter_keys = []

    return datasets, parameter_keys


# ---------------------------------------------------------------------------
# Public builders — Tier 2 (requires user deps)
# ---------------------------------------------------------------------------


def build_pipeline_snapshots() -> list[PipelineSnapshot]:
    """Build pipeline and node snapshots by executing register_pipelines().

    Accesses the global _ProjectPipelines instance. Triggers _load_data() on
    first call, which executes register_pipelines() and imports all user pipeline
    modules — user dependencies must be installed.

    Requires configure_project() to have been called (via bootstrap_project).
    """
    snapshots = []
    for pipe_id, pipeline in _global_pipelines.items():
        if pipeline is None:
            continue
        node_snapshots = [_node_to_snapshot(n) for n in pipeline.nodes]
        snapshots.append(
            PipelineSnapshot(
                id=pipe_id,
                name=pipe_id,
                nodes=node_snapshots,
                inputs=sorted(pipeline.inputs()),
                outputs=sorted(pipeline.outputs()),
            )
        )
    return snapshots


# ---------------------------------------------------------------------------
# Full snapshot — orchestrates both tiers
# ---------------------------------------------------------------------------


def build_snapshot(
    project_path: Path | str,
    env: str = "local",
    has_missing_deps: bool = False,
    mocked_dependencies: list[str] | None = None,
) -> ProjectSnapshot:
    """Build a complete ProjectSnapshot.

    Calls bootstrap_project() then runs both tiers:
      Tier 1: metadata, datasets, parameter_keys (no user deps)
      Tier 2: pipelines, nodes, is_free_input enrichment (user deps required)

    Args:
        project_path: Path to the Kedro project root.
        env: Kedro environment name (default: "local").
        has_missing_deps: Pass True if caller used dependency mocking.
        mocked_dependencies: Names of mocked modules, if any.

    Returns:
        ProjectSnapshot
    """
    from kedro.io import CatalogConfigResolver

    project_path = Path(project_path).expanduser().resolve()
    metadata = bootstrap_project(project_path)

    # Tier 1
    loader = _make_config_loader(project_path, env)
    try:
        catalog_config: dict[str, Any] = loader["catalog"]
    except Exception:
        catalog_config = {}
    resolver = CatalogConfigResolver(config=catalog_config)
    metadata_snapshot = build_metadata_snapshot(metadata)
    datasets, parameter_keys = build_catalog_snapshot(project_path, env)

    # Tier 2
    pipeline_snapshots = build_pipeline_snapshots()
    _enrich_datasets_from_pipelines(datasets, pipeline_snapshots, resolver)

    return ProjectSnapshot(
        metadata=metadata_snapshot,
        pipelines=pipeline_snapshots,
        datasets=datasets,
        parameter_keys=parameter_keys,
        has_missing_deps=has_missing_deps,
        mocked_dependencies=mocked_dependencies or [],
    )
