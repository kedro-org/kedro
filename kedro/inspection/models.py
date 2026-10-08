"""Dataclass models for Kedro inspection snapshots."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from kedro.io.core import _redact_url_credentials


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
            filepath = _redact_url_credentials(filepath)
        return cls(
            name=name,
            type=config.get("type", ""),
            filepath=filepath,
        )


@dataclass
class NodeSourceSnapshot:
    """Source location metadata for a pipeline node's underlying function.

    Attributes:
        filepath: Project-relative path to the source file.
        line_start: 1-based line number of the first line of the definition.
        line_end: 1-based line number of the last line of the definition.
    """

    filepath: str
    line_start: int
    line_end: int


@dataclass
class NodeSnapshot:
    """Read-only snapshot of a single pipeline node.

    Attributes:
        name: Fully-qualified node name (includes namespace prefix if present).
        func_name: Readable name of the node's underlying function.
        namespace: Node namespace, or ``None`` if the node has no namespace.
        tags: Sorted list of tags assigned to the node.
        inputs: Ordered list of input dataset names.
        outputs: Ordered list of output dataset names.
        source: Source location of the node's underlying function, or ``None``
            when the location cannot be resolved or lies outside the project.
    """

    name: str
    func_name: str = field(kw_only=True)
    namespace: str | None = None
    tags: list[str] = field(default_factory=list)
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    source: NodeSourceSnapshot | None = None


@dataclass
class GroupSnapshot:
    """Read-only snapshot of a group of nodes that can be deployed as one task.

    Groups come from `Pipeline.group_nodes_by`. With the default `"namespace"`
    strategy, nodes that share a top-level namespace form one group and a node
    without a namespace is a group of its own. `get_project_snapshot` takes a
    `group_by` argument to use another strategy.

    Use `dependencies` to order groups. Groups are listed in the order of their
    first node in the pipeline's execution order, which is not itself a valid
    order in which to run the groups.

    Two shapes of pipeline produce groups that need care:

    - A namespace interrupted by a node outside it, such as
      `a.first -> middle -> a.last`, gives groups that depend on each other in
      a cycle, so no order exists to run them as separate tasks. Kedro warns
      when such a pipeline is created, but the snapshot itself does not flag
      it. `validate_deployment_grouping` reports it as an error.
    - A node without a namespace whose name equals a namespace, such as a node
      `a` next to a node `a.other`, is merged into that namespace's group with
      type `"nodes"`.

    Attributes:
        name: Group name. With the `"namespace"` strategy this is the top-level
            namespace, or the node name for a node without a namespace.
        type: `"namespace"` for a group built from a namespace, `"nodes"` for a
            group built from a node without a namespace.
        nodes: Names of the nodes in the group, in execution order.
        dependencies: Names of the groups whose outputs this group reads, so
            that must run before it.
        inputs: Sorted names of the datasets and parameters the group reads but
            does not produce: free pipeline inputs and outputs of other groups.
        outputs: Sorted names of the datasets the group produces that are read
            by another group or are final pipeline outputs. Datasets used only
            inside the group are not listed.
    """

    name: str
    type: Literal["namespace", "nodes"]
    nodes: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
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
        group_by: Strategy of `Pipeline.group_nodes_by` that produced `groups`:
            `"namespace"` groups nodes by top-level namespace, `"none"` makes
            every node a group of its own.
        groups: Node groups that can each be deployed as one task.
    """

    name: str
    nodes: list[NodeSnapshot]
    inputs: list[str] = field(default_factory=list)
    outputs: list[str] = field(default_factory=list)
    group_by: Literal["namespace", "none"] = "namespace"
    groups: list[GroupSnapshot] = field(default_factory=list)


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
