"""Builder functions for constructing Kedro inspection snapshots."""

from __future__ import annotations

import inspect
import re
import warnings
from functools import partial
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal

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


_VALID_INCLUDE_SOURCE = frozenset({False, "refs", "full"})


def _extract_node_source(
    node: Node,
    project_path: Path,
    include_source: Literal["refs", "full"],
) -> NodeSourceSnapshot:
    """Extract source location metadata from a live ``Node``.

    Unwraps partials, bound methods, and ``__wrapped__`` decorators before
    calling ``inspect`` so that line numbers refer to the function definition
    rather than a generated wrapper.

    Args:
        node: A live Kedro pipeline node.
        project_path: Absolute path to the project root, used to produce
            project-relative file paths.
        include_source: ``"refs"`` populates location fields only;
            ``"full"`` additionally populates ``code``.

    Returns:
        A ``NodeSourceSnapshot`` with all available source metadata.
    """
    func_name: str | None = node._func_name

    func = node.func
    # Unwrap partial to reach the underlying callable
    while isinstance(func, partial):
        func = func.func
    # Unwrap bound methods
    if inspect.ismethod(func):
        func = func.__func__
    # Follow __wrapped__ chains left by functools.wraps
    try:
        func = inspect.unwrap(func)
    except Exception:  # noqa: BLE001
        pass

    filepath: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code: str | None = None

    try:
        raw_filepath = inspect.getfile(func)
        try:
            filepath = str(Path(raw_filepath).relative_to(project_path))
        except ValueError:
            filepath = raw_filepath
    except (TypeError, OSError):
        pass

    try:
        lines, start = inspect.getsourcelines(func)
        line_start = start
        line_end = start + len(lines) - 1
        if include_source == "full":
            code = "".join(lines)
    except (OSError, TypeError):
        pass

    return NodeSourceSnapshot(
        func_name=func_name,
        filepath=filepath,
        line_start=line_start,
        line_end=line_end,
        code=code,
    )


def _node_to_snapshot(
    node: Node,
    project_path: Path | None = None,
    include_source: Literal[False, "refs", "full"] = False,
) -> NodeSnapshot:
    """Convert a live ``Node`` object to a ``NodeSnapshot``.

    Args:
        node: A Kedro pipeline node.
        project_path: Absolute path to the project root. Required when
            *include_source* is not ``False`` to produce project-relative
            file paths.
        include_source: Controls source metadata population.
            ``False`` (default) omits all source fields.
            ``"refs"`` populates ``func_name``, ``source_filepath``,
            ``source_line_start``, and ``source_line_end``.
            ``"full"`` additionally populates ``source_code``.

    Returns:
        Read-only snapshot of the node's structural metadata.
    """
    source: NodeSourceSnapshot | None = None
    if include_source and project_path is not None:
        source = _extract_node_source(node, project_path, include_source)  # type: ignore[arg-type]
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
    include_source: Literal[False, "refs", "full"] = False,
) -> list[PipelineSnapshot]:
    """Build a ``PipelineSnapshot`` for every registered pipeline.

    Args:
        pipeline_dict: Dictionary of pipeline name to ``Pipeline`` object,
            as returned by ``dict(kedro.framework.project.pipelines)``.
        project_path: Absolute path to the project root, forwarded to
            ``_node_to_snapshot`` when *include_source* is not ``False``.
        include_source: Source metadata mode forwarded to each
            ``_node_to_snapshot`` call. See ``_node_to_snapshot`` for details.

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
                    _node_to_snapshot(
                        _node,
                        project_path=project_path,
                        include_source=include_source,
                    )
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
    include_source: Literal[False, "refs", "full"] = False,
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

    Raises:
        ValueError: If *include_source* is not one of ``False``, ``"refs"``,
            or ``"full"``.
    """
    if include_source not in _VALID_INCLUDE_SOURCE:
        raise ValueError(
            f"include_source must be False, 'refs', or 'full'; got {include_source!r}."
        )

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
        include_source=include_source,
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
