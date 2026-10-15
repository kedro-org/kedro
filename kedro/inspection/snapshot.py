"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

import inspect
import re
import warnings
from collections import defaultdict
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast, get_args

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
    GroupSnapshot,
    NodeSnapshot,
    NodeSourceSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)
from kedro.pipeline.transcoding import _strip_transcoding

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata
    from kedro.pipeline import Pipeline
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


def _resolve_node_source(
    func: Any,
    resolved_project_path: Path,
) -> NodeSourceSnapshot | None:
    """Resolve source location metadata for a node's underlying function.

    Args:
        func: The node's underlying callable.
        resolved_project_path: Absolute, resolved path to the project root.

    Returns:
        Source location metadata, or ``None`` when the location cannot be
        determined (for example, lambdas, ``functools.partial``, built-ins,
        unreadable source files, or files outside the project root).
    """
    if (
        isinstance(func, partial)
        or inspect.isbuiltin(func)
        or getattr(func, "__name__", None) == "<lambda>"
    ):
        return None

    func = inspect.unwrap(func)

    try:
        source_file = inspect.getsourcefile(func)
    except (OSError, TypeError):
        return None

    if source_file is None:
        return None

    resolved_path = Path(source_file).resolve()
    if not resolved_path.is_relative_to(resolved_project_path):
        return None

    filepath = resolved_path.relative_to(resolved_project_path).as_posix()

    try:
        source_lines, line_start = inspect.getsourcelines(func)
    except (OSError, TypeError):
        return None

    line_end = line_start + len(source_lines) - 1

    return NodeSourceSnapshot(
        filepath=filepath,
        line_start=line_start,
        line_end=line_end,
    )


def _node_to_snapshot(node: Node, resolved_project_path: Path) -> NodeSnapshot:
    """Convert a live ``Node`` object to a ``NodeSnapshot``.

    Args:
        node: A Kedro pipeline node.
        resolved_project_path: Absolute, resolved path to the project root.

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
        source=_resolve_node_source(node.func, resolved_project_path),
    )


def _build_group_snapshots(
    pipeline: Pipeline, group_by: str | None = "namespace"
) -> list[GroupSnapshot]:
    """Build a `GroupSnapshot` for each group of nodes in `pipeline`.

    A group's inputs are the datasets and parameters it reads but does not
    produce. Its outputs are the datasets it produces that another group reads
    or that no node reads, which makes them final pipeline outputs.

    Transcoded names such as `df@spark` and `df@pandas` refer to one dataset,
    so they are matched on the name without the transcoding suffix and
    reported the way the group's own nodes spell them.

    Args:
        pipeline: A Kedro pipeline.
        group_by: Grouping strategy passed to `Pipeline.group_nodes_by`.

    Returns:
        Group snapshots in the order returned by `Pipeline.group_nodes_by`.
    """
    groups = pipeline.group_nodes_by(group_by)
    nodes_by_name = {node.name: node for node in pipeline.nodes}
    group_of = {name: group.name for group in groups for name in group.nodes}

    readers: dict[str, set[str]] = defaultdict(set)
    for node in pipeline.nodes:
        for input_ in node.inputs:
            readers[_strip_transcoding(input_)].add(group_of[node.name])

    snapshots = []
    for group in groups:
        group_nodes = [nodes_by_name[name] for name in group.nodes]
        produced = {
            _strip_transcoding(output)
            for node in group_nodes
            for output in node.outputs
        }
        inputs = {
            input_
            for node in group_nodes
            for input_ in node.inputs
            if _strip_transcoding(input_) not in produced
        }
        outputs = set()
        for node in group_nodes:
            for output in node.outputs:
                read_by = readers.get(_strip_transcoding(output), set())
                if not read_by or read_by - {group.name}:
                    outputs.add(output)

        snapshots.append(
            GroupSnapshot(
                name=group.name,
                type=cast(Literal["namespace", "nodes"], group.type),
                nodes=list(group.nodes),
                dependencies=list(group.dependencies),
                inputs=sorted(inputs),
                outputs=sorted(outputs),
            )
        )
    return snapshots


GroupBy = Literal["namespace", "none"]


def _normalise_group_by(group_by: str | None) -> GroupBy:
    """Return the canonical name of a grouping strategy.

    `Pipeline.group_nodes_by` accepts `None` and `"none"` for the same strategy
    and compares names case-insensitively, so every spelling of a strategy maps
    to one name, which is what `PipelineSnapshot.group_by` records.

    Raises:
        ValueError: If `group_by` is not a supported strategy.
    """
    name = "none" if group_by is None else group_by
    if not isinstance(name, str) or name.lower() not in get_args(GroupBy):
        raise ValueError(
            f"Unsupported group_by strategy: {group_by!r}. "
            "Expected 'namespace', 'none' or None."
        )
    return cast(GroupBy, name.lower())


def _build_pipeline_snapshots(
    pipeline_dict: dict[str, Any],
    project_path: Path,
    group_by: str | None = "namespace",
) -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Args:
        pipeline_dict: Dictionary of pipeline name to ``Pipeline`` object,
            as returned by ``dict(kedro.framework.project.pipelines)``.
        project_path: Absolute path to the project root directory.
        group_by: Grouping strategy used to build each pipeline's `groups`.

    Returns:
        List of pipeline snapshots in registry iteration order.
    """
    group_by = _normalise_group_by(group_by)
    resolved_project_path = project_path.resolve()
    snapshots = []
    for pipeline_id, pipeline in pipeline_dict.items():
        if pipeline is None:
            continue
        snapshots.append(
            PipelineSnapshot(
                name=pipeline_id,
                nodes=[
                    _node_to_snapshot(_node, resolved_project_path)
                    for _node in pipeline.nodes
                ],
                inputs=sorted(pipeline.inputs()),
                outputs=sorted(pipeline.outputs()),
                group_by=group_by,
                groups=_build_group_snapshots(pipeline, group_by),
            )
        )
    return snapshots


def _build_project_snapshot(  # noqa: PLR0913
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    metadata: ProjectMetadata | None = None,
    runtime_params: dict[str, Any] | None = None,
    group_by: str | None = "namespace",
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
        runtime_params: Optional dictionary of runtime parameters forwarded to
            the config loader for ``${runtime_params:...}`` interpolation.
        group_by: Grouping strategy used to build each pipeline's `groups`.

    Returns:
        A fully populated ``ProjectSnapshot``.

    Raises:
        ValueError: If `group_by` is not a supported strategy. Raised before
            the project is bootstrapped or any configuration is loaded.
    """
    group_by = _normalise_group_by(group_by)
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
        effective_project_path,
        env=env,
        conf_source=conf_source,
        runtime_params=runtime_params,
    )

    try:
        conf_catalog: dict[str, Any] = config_loader["catalog"]
    except (KeyError, MissingConfigException):
        conf_catalog = {}

    metadata_snapshot = _build_project_metadata_snapshot(metadata)
    pipeline_snapshots = _build_pipeline_snapshots(
        dict(pipelines), effective_project_path, group_by
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
