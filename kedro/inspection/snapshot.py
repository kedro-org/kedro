"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

import inspect
import re
import warnings
from collections.abc import Callable
from functools import partial as _partial
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


def _resolve_project_path(
    project_path: str | Path | None,
    metadata: ProjectMetadata | None,
) -> tuple[Path, ProjectMetadata | None]:
    """Resolve the effective project path."""
    resolved = (
        Path(project_path).expanduser().resolve() if project_path is not None else None
    )
    if metadata is not None:
        if resolved is not None and resolved != metadata.project_path:
            warnings.warn(
                f"Both project_path and metadata were provided but point to different "
                f"directories ({resolved!r} vs "
                f"{metadata.project_path!r}). project_path will be ignored.",
                UserWarning,
                stacklevel=4,
            )
        return metadata.project_path, metadata
    if resolved is not None:
        return resolved, None
    raise ValueError("Either project_path or metadata must be provided.")


def _extract_node_func(func: Callable) -> Callable:
    """Return the callable to use for source inspection."""
    if inspect.ismethod(func):
        func = func.__func__  # type: ignore[union-attr]
    while isinstance(func, _partial):
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


def _get_node_source_snapshot(
    node_name: str,
    pipeline_dict: dict[str, Any],
    project_path: Path,
    *,
    include_code: bool = True,
) -> NodeSourceSnapshot:
    """Resolve source information for a single pipeline node."""
    found_node: Node | None = None
    for pipeline in pipeline_dict.values():
        if pipeline is None:
            continue
        for n in pipeline.nodes:
            if n.name == node_name:
                found_node = n
                break
        if found_node is not None:
            break

    if found_node is None:
        raise KeyError(
            f"No node named {node_name!r} found in any registered pipeline. "
            "Use get_project_snapshot() to list available node names."
        )

    func_name: str | None = found_node._func_name
    source_filepath: str | None = None
    source_line_start: int | None = None
    source_line_end: int | None = None
    code: str | None = None

    resolved_func = _extract_node_func(found_node.func)

    try:
        raw_filepath = Path(inspect.getfile(resolved_func))
        try:
            source_filepath = str(raw_filepath.relative_to(project_path))
        except ValueError:
            # File lives outside the project root (e.g. installed library)
            source_filepath = str(raw_filepath)
    except TypeError:
        pass  # built-in or C-extension: no file available

    try:
        lines, start = inspect.getsourcelines(resolved_func)
        source_line_start = start
        source_line_end = start + len(lines) - 1
        if include_code:
            code = "".join(lines)
    except (OSError, TypeError):
        pass  # dynamically generated, built-in, or otherwise unreadable source

    return NodeSourceSnapshot(
        name=node_name,
        func_name=func_name,
        source_filepath=source_filepath,
        source_line_start=source_line_start,
        source_line_end=source_line_end,
        code=code,
    )


def _build_node_source_snapshot(
    node_name: str,
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    metadata: ProjectMetadata | None = None,
    *,
    include_code: bool = True,
) -> NodeSourceSnapshot:
    """Bootstrap the project and return source information for a single node."""
    effective_project_path, metadata = _resolve_project_path(project_path, metadata)

    if env is not None and not _ENV_RE.match(env):
        raise ValueError(
            f"Invalid env value {env!r}: must contain only letters, digits, hyphens, and underscores."
        )

    if metadata is None:
        metadata = bootstrap_project(effective_project_path)

    return _get_node_source_snapshot(
        node_name=node_name,
        pipeline_dict=dict(pipelines),
        project_path=effective_project_path,
        include_code=include_code,
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
        func_name=node._func_name,
    )


def _build_pipeline_snapshots(
    pipeline_dict: dict[str, Any],
) -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Args:
        pipeline_dict: Dictionary of pipeline name to ``Pipeline`` object,
            as returned by ``dict(kedro.framework.project.pipelines)``.

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
                nodes=[_node_to_snapshot(_node) for _node in pipeline.nodes],
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
    effective_project_path, metadata = _resolve_project_path(project_path, metadata)

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
    pipeline_snapshots = _build_pipeline_snapshots(dict(pipelines))
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
