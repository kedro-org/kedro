"""Dataclass models for Kedro inspection snapshots."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Matches URI credentials
_CREDENTIAL_RE = re.compile(r"(://)[^@\s]*:[^@\s]*(@)")


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

    @classmethod
    def from_config(cls, name: str, config: dict) -> DatasetSnapshot:
        """Construct a ``DatasetSnapshot`` from a raw catalog config entry."""
        filepath = config.get("filepath")
        if filepath:
            filepath = _CREDENTIAL_RE.sub(r"\1<redacted>\2", filepath)
        return cls(
            name=name,
            type=config.get("type", ""),
            filepath=filepath,
        )


@dataclass
class NodeSourceSnapshot:
    """Source location metadata for a pipeline node's underlying function.

    All fields may be ``None`` when the information cannot be determined (e.g.
    built-in functions, dynamically created callables).

    Attributes:
        func_name: Readable name of the function (from ``Node._func_name``).
        filepath: Path to the source file. Project-relative when the file is
            within the project root, absolute otherwise.
        line_start: 1-based line number of the first line of the function
            definition.
        line_end: 1-based line number of the last line of the function
            definition.
        code: Full source text of the function. Only populated when
            ``include_source="full"`` is requested; ``None`` for ``"refs"``.
    """

    func_name: str | None = None
    filepath: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    code: str | None = None


@dataclass
class NodeSnapshot:
    """Read-only snapshot of a single pipeline node.

    Attributes:
        name: Fully-qualified node name (includes namespace prefix if present).
        func_name: Readable name of the node's underlying function (e.g.
            ``"split_data"``). For auto-named nodes this gives a clean label
            without the hash suffix; for explicitly named nodes it is the
            function name independent of the node name. Always populated.
        namespace: Node namespace, or ``None`` if the node has no namespace.
        tags: Sorted list of tags assigned to the node.
        inputs: Ordered list of input dataset names.
        outputs: Ordered list of output dataset names.
        source: Source location metadata for the node's underlying function, or
            ``None`` when ``include_source=False`` (the default).
    """

    name: str
    func_name: str | None = None
    namespace: str | None = None
    tags: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    source: NodeSourceSnapshot | None = None


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


@dataclass
class ProjectSnapshot:
    """Read-only snapshot of an entire Kedro project.

    Attributes:
        metadata: Snapshot of the project's metadata (name, package, Kedro version).
        pipelines: Ordered list of snapshots for every registered pipeline.
        datasets: Mapping from dataset name to its snapshot, including entries
            resolved from factory patterns.
        parameters: Sorted list of parameter key strings (values are not stored).
    """

    metadata: ProjectMetadataSnapshot
    pipelines: list[PipelineSnapshot]
    datasets: dict[str, DatasetSnapshot]
    parameters: list[str]
