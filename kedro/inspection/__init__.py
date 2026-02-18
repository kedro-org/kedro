"""Kedro inspection API: dependency-free project snapshot (Kedro-native JSON)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.inspection.lite_shim import safe_context

try:
    from kedro.inspection.models import ProjectSnapshot
    from kedro.inspection.snapshot import build_snapshot
except ImportError as e:
    if "pydantic" in str(e).lower():
        raise ImportError(
            "The inspection API requires pydantic. Install it with: pip install kedro[inspect]"
        ) from e
    raise


class _InspectionCatalog:
    """Minimal catalog for inspection: only config resolution, no data loading.

    Exposes config_resolver so snapshot building can resolve dataset config (type, etc.)
    without ever loading or storing datasets or parameters.
    """

    def __init__(self, config_resolver: Any) -> None:
        self.config_resolver = config_resolver


def _dummy_catalog_for_inspection(context: Any) -> _InspectionCatalog:
    """Build a dummy catalog that only supports config resolution; no data loading.

    Uses the same catalog config and credentials as the project so resolve_pattern()
    works, but no datasets or parameters are ever loaded or stored.
    """
    from kedro.framework.context.context import _convert_paths_to_absolute_posix
    from kedro.io import CatalogConfigResolver

    conf_catalog = context.config_loader["catalog"]
    conf_catalog = _convert_paths_to_absolute_posix(
        project_path=context.project_path, conf_dictionary=conf_catalog
    )
    conf_creds = context._get_config_credentials()
    config_resolver = CatalogConfigResolver(config=conf_catalog, credentials=conf_creds)
    return _InspectionCatalog(config_resolver=config_resolver)


def _read_package_name_from_pyproject(project_path: Path) -> str:
    """Read package_name from project_path/pyproject.toml [tool.kedro]. No Kedro internals."""
    pyproject = Path(project_path) / "pyproject.toml"
    if not pyproject.is_file():
        raise RuntimeError(f"Could not find pyproject.toml in {project_path}")
    try:
        import tomllib
    except ImportError:
        import tomli as tomllib  # type: ignore
    with pyproject.open("rb") as f:
        data = tomllib.load(f)
    try:
        return data["tool"]["kedro"]["package_name"]
    except KeyError as exc:
        raise RuntimeError(
            f"Missing [tool.kedro] package_name in {pyproject}. Add it to pyproject.toml."
        ) from exc


def get_snapshot(
    project_path: str | Path,
    env: str | None = None,
    extra_params: dict[str, Any] | None = None,
    pipeline_id: str | None = None,
) -> ProjectSnapshot:
    """
    Build a Kedro-native project snapshot without requiring project dependencies.

    Uses only public Kedro API: reads package_name from pyproject.toml for safe_context,
    then inside safe_context calls bootstrap_project(project_path), then creates session
    and builds the snapshot. Never calls catalog.get() or materializes datasets.

    Args:
        project_path: Path to the Kedro project root.
        env: Environment name (e.g. "local", "production"). Defaults to "local".
        extra_params: Optional runtime parameters to merge with parameters.yml.
        pipeline_id: If set, only include this pipeline in the snapshot;
            otherwise include all registered pipelines.

    Returns:
        ProjectSnapshot (pipelines, nodes in execution order, datasets, parameters).
        has_missing_deps is True if any pipeline import was mocked.

    Example:
        >>> from kedro.inspection import get_snapshot
        >>> snapshot = get_snapshot("/path/to/my/kedro/project")
        >>> for p in snapshot.pipelines:
        ...     print(p.id, len(p.nodes), "nodes")
    """
    project_path = Path(project_path).expanduser().resolve()
    package_name = _read_package_name_from_pyproject(project_path)
    missing_deps: set[str] = set()
    with safe_context(project_path, package_name) as mocked:
        missing_deps = mocked
        metadata = bootstrap_project(project_path)
        session = KedroSession.create(
            project_path=project_path,
            env=env or "local",
            runtime_params=extra_params or {},
        )
        with session:
            context = session.load_context()
            # Use a dummy catalog (config resolution only, no data/params loading).
            catalog = _dummy_catalog_for_inspection(context)
            snapshot = build_snapshot(
                context,
                metadata,
                has_missing_deps=len(missing_deps) > 0,
                mocked_dependencies=sorted(missing_deps),
                catalog=catalog,
            )
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
        parameters=snapshot.parameters,
        has_missing_deps=snapshot.has_missing_deps,
        mocked_dependencies=snapshot.mocked_dependencies,
    )


# Alias for compatibility with docs
inspect_project = get_snapshot

__all__ = [
    "get_snapshot",
    "inspect_project",
    "safe_context",
    "ProjectSnapshot",
    "build_snapshot",
]
