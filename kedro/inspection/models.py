"""Dataclass models for Kedro inspection snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ProjectMetadataSnapshot:
    """Read-only snapshot of project metadata derived from ``pyproject.toml``.

    Attributes:
        project_name: Human-readable project name.
        package_name: Python package name for the project.
        kedro_version: Kedro package version from project metadata (``pyproject.toml``).
    """

    project_name: str
    package_name: str
    kedro_version: str


@dataclass
class DatasetSnapshot:
    """Read-only snapshot of a catalog dataset entry.

    Attributes:
        name: Dataset name as it appears in the catalog.
        type: Dataset type string (e.g. ``"pandas.CSVDataset"``).
        filepath: File path if present in config, or ``None``.
    """

    name: str
    type: str
    filepath: str | None = None

@dataclass
class NodeSnapshot:
    """Read-only snapshot of a single pipeline node.

    Attributes:
        name: Fully-qualified node name (includes namespace prefix if present).
        namespace: Node namespace, or ``None`` if the node has no namespace.
        tags: Sorted list of tags assigned to the node.
        inputs: Ordered list of input dataset names.
        outputs: Ordered list of output dataset names.
    """

    name: str
    namespace: str | None = None
    tags: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)


@dataclass
class PipelineSnapshot:
    """Read-only snapshot of a registered pipeline.

    Attributes:
        name: Pipeline registry key (e.g. ``"__default__"``, ``"data_science"``).
        nodes: Ordered list of node snapshots in topological execution order.
        inputs: Sorted list of free pipeline inputs.
        outputs: Sorted list of final pipeline outputs.
    """

    name: str
    nodes: list[NodeSnapshot]
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
