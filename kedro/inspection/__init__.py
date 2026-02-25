"""Kedro inspection API — project snapshot (Kedro-native JSON)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:
    from kedro.inspection.models import ProjectSnapshot
    from kedro.inspection.snapshot import build_snapshot
except ImportError as e:
    if "pydantic" in str(e).lower():
        raise ImportError(
            "The inspection API requires pydantic. Install it with: pip install kedro[inspect]"
        ) from e
    raise


def get_snapshot(
    project_path: str | Path,
    env: str | None = None,
    pipeline_id: str | None = None,
) -> ProjectSnapshot:
    """Build a Kedro-native project snapshot.

    Requires project dependencies to be installed. Delegates to build_snapshot()
    which uses bootstrap_project + _ProjectPipelines directly (no KedroSession
    or KedroContext).

    Args:
        project_path: Path to the Kedro project root.
        env: Environment name (e.g. "local", "production"). Defaults to "local".
        pipeline_id: If set, only include this pipeline in the snapshot.

    Returns:
        ProjectSnapshot with pipelines, nodes, datasets, and parameter_keys.

    Example:
        >>> from kedro.inspection import get_snapshot
        >>> snapshot = get_snapshot("/path/to/my/kedro/project")
        >>> for p in snapshot.pipelines:
        ...     print(p.id, len(p.nodes), "nodes")
    """
    project_path = Path(project_path).expanduser().resolve()
    snapshot = build_snapshot(project_path=project_path, env=env or "local")

    if pipeline_id is not None:
        snapshot = _filter_pipeline(snapshot, pipeline_id)
    return snapshot


def _filter_pipeline(snapshot: ProjectSnapshot, pipeline_id: str) -> ProjectSnapshot:
    """Return a new snapshot containing only the given pipeline."""
    pipelines = [p for p in snapshot.pipelines if p.id == pipeline_id]
    if not pipelines:
        return snapshot
    ds_names = set()
    for p in pipelines:
        for n in p.nodes:
            ds_names.update(n.inputs)
            ds_names.update(n.outputs)
    datasets = {k: v for k, v in snapshot.datasets.items() if k in ds_names}
    return ProjectSnapshot(
        metadata=snapshot.metadata,
        pipelines=pipelines,
        datasets=datasets,
        parameter_keys=snapshot.parameter_keys,
        has_missing_deps=snapshot.has_missing_deps,
        mocked_dependencies=snapshot.mocked_dependencies,
    )


__all__ = [
    "get_snapshot",
    "ProjectSnapshot",
    "build_snapshot",
]
