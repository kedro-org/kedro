"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

import functools
import inspect
import re
import warnings
from pathlib import Path
from typing import TYPE_CHECKING, Any

from kedro.config import MissingConfigException
from kedro.framework.project import pipelines
from kedro.framework.startup import bootstrap_project
from kedro.inspection.helper import (
    _get_parameter_keys,
    _make_config_loader,
    _resolve_factory_patterns,
)
from kedro.inspection.models import (
    DatasetSnapshot,
    NodeSnapshot,
    NodeSourceSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata
    from kedro.pipeline.node import Node


_ENV_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def _get_source_callable(func: Any) -> Any:
    """Return the callable whose source best represents a node function."""
    source_func = inspect.unwrap(func)
    while isinstance(source_func, functools.partial):
        source_func = inspect.unwrap(source_func.func)
    return source_func


def _format_source_filepath(source_file: str, project_path: Path | None) -> str:
    source_path = Path(source_file).resolve()
    if project_path is None:
        return str(source_path)

    try:
        return str(source_path.relative_to(project_path.resolve()))
    except ValueError:
        return str(source_path)


def _get_node_source_snapshot(
    node: Node, project_path: Path | None = None
) -> NodeSourceSnapshot | None:
    """Build a source-location snapshot for a node function when inspectable."""
    try:
        source_func = _get_source_callable(node.func)
        if getattr(source_func, "__name__", None) == "<lambda>":
            return None
        source_file = inspect.getsourcefile(source_func)
        if source_file is None:
            return None
        source_lines, line_start = inspect.getsourcelines(source_func)
    except (OSError, TypeError, ValueError):
        return None

    return NodeSourceSnapshot(
        filepath=_format_source_filepath(source_file, project_path),
        line_start=line_start,
        line_end=line_start + len(source_lines) - 1,
    )


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


def _build_dataset_snapshots(
    catalog_config: dict[str, Any],
) -> dict[str, DatasetSnapshot]:
    """Build a ``DatasetSnapshot`` for every entry in the catalog configuration.

    Args:
        catalog_config: Raw catalog configuration dict.

    Returns:
        Mapping of dataset name to its snapshot.
    """
    return {
        ds_name: DatasetSnapshot.from_config(ds_name, ds_config)
        for ds_name, ds_config in catalog_config.items()
        if not ds_name.startswith("_")
        and isinstance(ds_config, dict)  # skip YAML anchors and non-dict entries
    }


def _node_to_snapshot(node: Node, project_path: Path | None = None) -> NodeSnapshot:
    """Convert a live ``Node`` object to a ``NodeSnapshot``.

    Args:
        node: A Kedro pipeline node.
        project_path: Project root path used to relativise source file paths.

    Returns:
        Read-only snapshot of the node's structural metadata.
    """
    return NodeSnapshot(
        name=node.name,
        func_name=node._func_name,  # Matches Node.__str__ and registry describe.
        namespace=node.namespace,
        tags=sorted(node.tags),
        inputs=node.inputs,
        outputs=node.outputs,
        source=_get_node_source_snapshot(node, project_path),
    )


def _build_pipeline_snapshots(
    pipeline_dict: dict[str, Any], project_path: Path | None = None
) -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Args:
        pipeline_dict: Dictionary of pipeline name to ``Pipeline`` object,
            as returned by ``dict(kedro.framework.project.pipelines)``.
        project_path: Project root path used to relativise source file paths.

    Returns:
        List of pipeline snapshots in registry iteration order.
    """
    snapshots = []
    for pipeline_id, pipeline in pipeline_dict.items():
        if pipeline is None:
            continue
        snapshots.append(
            PipelineSnapshot(
                name=pipeline_id,
                nodes=[
                    _node_to_snapshot(_node, project_path) for _node in pipeline.nodes
                ],
                inputs=sorted(pipeline.inputs()),
                outputs=sorted(pipeline.outputs()),
            )
        )
    return snapshots


def _build_project_snapshot(
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    metadata: ProjectMetadata | None = None,
) -> ProjectSnapshot:
    """Build a ``ProjectSnapshot`` for the Kedro project at project_path.

    Args:
        project_path: Path to the project root directory (the directory that
            contains ``pyproject.toml``). Optional when *metadata* is provided;
            if both are given and point to different directories a warning is
            emitted and *metadata.project_path* takes precedence.
        env: Optional run environment override (e.g. ``"staging"``).
            When ``None`` the default run environment from the project
            settings is used.
        conf_source: Optional path to the configuration directory.
            When ``None``, defaults to ``<project_path>/<settings.CONF_SOURCE>``.
        metadata: Optional pre-computed ``ProjectMetadata`` returned by a prior
            ``bootstrap_project`` call. When provided, ``bootstrap_project`` is
            skipped entirely.

    Returns:
        A fully populated ``ProjectSnapshot``.
    """
    resolved_project_path = (
        Path(project_path).expanduser().resolve() if project_path is not None else None
    )
    if metadata is not None:
        if (
            resolved_project_path is not None
            and resolved_project_path != metadata.project_path
        ):
            warnings.warn(
                f"Both project_path and metadata were provided but point to different "
                f"directories ({resolved_project_path!r} vs "
                f"{metadata.project_path!r}). project_path will be ignored.",
                UserWarning,
                stacklevel=3,
            )
        effective_project_path = metadata.project_path
    elif resolved_project_path is not None:
        effective_project_path = resolved_project_path
    else:
        raise ValueError("Either project_path or metadata must be provided.")

    if env is not None and not _ENV_RE.match(env):
        raise ValueError(
            f"Invalid env value {env!r}: must contain only letters, digits, hyphens, and underscores."
        )

    if metadata is None:
        metadata = bootstrap_project(effective_project_path)
    config_loader = _make_config_loader(
        effective_project_path, env=env, conf_source=conf_source
    )

    try:
        conf_catalog: dict[str, Any] = config_loader["catalog"]
    except (KeyError, MissingConfigException):
        conf_catalog = {}

    metadata_snapshot = _build_project_metadata_snapshot(metadata)
    pipeline_snapshots = _build_pipeline_snapshots(
        dict(pipelines), effective_project_path
    )
    dataset_snapshots = _build_dataset_snapshots(conf_catalog)

    # resolve factory patterns
    dataset_snapshots = _resolve_factory_patterns(
        conf_catalog, dataset_snapshots, pipeline_snapshots
    )

    parameter_keys = _get_parameter_keys(config_loader)

    return ProjectSnapshot(
        metadata=metadata_snapshot,
        pipelines=pipeline_snapshots,
        datasets=dataset_snapshots,
        parameters=parameter_keys,
    )
