"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

import inspect
import re
import warnings
from collections.abc import Callable
from functools import partial
from pathlib import Path
from types import FunctionType
from typing import TYPE_CHECKING, Any, cast

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


def _extract_node_func(func: Callable) -> Callable:
    """Return the callable to use for source inspection."""
    if inspect.ismethod(func):
        func = func.__func__  # type: ignore[union-attr]
    while isinstance(func, partial):
        func = func.func

    unwrapped_func = cast(Callable, inspect.unwrap(func))
    if unwrapped_func is not func:
        return unwrapped_func

    if isinstance(func, FunctionType) and func.__closure__:
        wrapped_func = next(
            (
                cell.cell_contents
                for cell in func.__closure__
                if isinstance(cell.cell_contents, FunctionType)
            ),
            None,
        )
        if wrapped_func is not None and wrapped_func is not func:
            return _extract_node_func(wrapped_func)

    return func


def _extract_node_source(
    node: Node,
    project_path: Path,
) -> NodeSourceSnapshot | None:
    """Extract source location metadata from a live ``Node``.

    Args:
        node: A live Kedro pipeline node.
        project_path: Absolute path to the project root. Source file paths are
            project-relative when possible and omitted for external files.

    Returns:
        Source location metadata, or ``None`` when it cannot be determined.
    """
    func = _extract_node_func(node.func)

    try:
        filepath = str(Path(inspect.getfile(func)).relative_to(project_path))
        lines, start = inspect.getsourcelines(func)
    except (TypeError, OSError, ValueError):
        return None

    return NodeSourceSnapshot(
        filepath=filepath,
        line_start=start,
        line_end=start + len(lines) - 1,
    )


def _node_to_snapshot(
    node: Node,
    project_path: Path | None = None,
) -> NodeSnapshot:
    """Convert a live ``Node`` object to a ``NodeSnapshot``.

    Args:
        node: A Kedro pipeline node.
        project_path: Absolute path to the project root, used to produce
            project-relative source file paths.

    Returns:
        Read-only snapshot of the node's structural metadata.
    """
    source: NodeSourceSnapshot | None = None
    if project_path is not None:
        source = _extract_node_source(node, project_path)
    return NodeSnapshot(
        name=node.name,
        func_name=node._func_name,
        namespace=node.namespace,
        tags=sorted(node.tags),
        inputs=node.inputs,
        outputs=node.outputs,
        source=source,
    )


def _build_pipeline_snapshots(
    pipeline_dict: dict[str, Any],
    project_path: Path | None = None,
) -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Args:
        pipeline_dict: Dictionary of pipeline name to ``Pipeline`` object,
            as returned by ``dict(kedro.framework.project.pipelines)``.
        project_path: Absolute path to the project root, used to produce
            project-relative source file paths.

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
                    _node_to_snapshot(_node, project_path=project_path)
                    for _node in pipeline.nodes
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
        dict(pipelines),
        project_path=effective_project_path,
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
