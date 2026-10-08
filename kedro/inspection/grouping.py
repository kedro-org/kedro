"""Checks that a node grouping can run with each group as a separate task.

Deployment platforms run each group returned by `Pipeline.group_nodes_by` as its
own task, usually in its own container. Groups then no longer share memory or
local disk, so a pipeline that runs with `kedro run` can still fail on the
platform. The checks here find those problems from the pipeline structure and
the catalog configuration alone, without loading data or importing dataset
classes.
"""

from __future__ import annotations

import copy
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from graphlib import CycleError, TopologicalSorter
from typing import TYPE_CHECKING, Any, Literal

from kedro.io.cached_dataset import CachedDataset
from kedro.io.core import get_protocol_and_path
from kedro.pipeline.transcoding import _strip_transcoding

if TYPE_CHECKING:
    from collections.abc import Iterable

    from kedro.io import CatalogProtocol
    from kedro.pipeline import GroupedNodes, Pipeline

IssueSeverity = Literal["error", "warning", "info"]
IssueCode = Literal[
    "invalid_grouping",
    "group_cycle",
    "ephemeral_boundary",
    "local_boundary",
    "single_node_groups",
]
GroupingStatus = Literal["passed", "failed"]

_SEVERITY_ORDER: dict[str, int] = {"error": 0, "warning": 1, "info": 2}
_EPHEMERAL_TYPES = frozenset({"MemoryDataset", "SharedMemoryDataset"})
_CACHED_TYPES = frozenset({"CachedDataset"})
# Catalog config keys, and dataset attributes with a leading underscore, that
# hold a dataset's location.
_FILEPATH_KEYS = ("filepath", "path")
# fsspec filesystems that live inside the process, so a file on them is as
# unshared between tasks as a `MemoryDataset`.
_IN_PROCESS_PROTOCOLS = frozenset({"memory"})
# Paths that look local but are shared storage on Databricks, lower-cased.
_SHARED_MOUNT_PREFIXES = ("/dbfs/", "/volumes/", "/workspace/", "dbfs:/")


@dataclass(frozen=True)
class DeploymentGroupingIssue:
    """A problem found when checking a node grouping for deployment.

    Attributes:
        code: Kind of issue, one of `"invalid_grouping"`, `"group_cycle"`,
            `"ephemeral_boundary"`, `"local_boundary"` or `"single_node_groups"`.
        severity: Fixed for each `code`. `"error"` means the pipeline will fail
            with each group run as a separate task, `"warning"` means it may fail
            depending on where the tasks run, and `"info"` is an observation that
            needs no change. Severity only describes the issue: nothing is
            stopped because of it, and the caller decides how to act.
        message: Description of the issue and how to fix it.
        datasets: Names of the datasets involved.
        groups: Names of the groups involved.
        nodes: Names of the nodes involved.
    """

    code: IssueCode
    severity: IssueSeverity
    message: str
    datasets: tuple[str, ...] = ()
    groups: tuple[str, ...] = ()
    nodes: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "code": self.code,
            "severity": self.severity,
            "message": self.message,
            "datasets": list(self.datasets),
            "groups": list(self.groups),
            "nodes": list(self.nodes),
        }


@dataclass(frozen=True)
class DeploymentGroupingResult:
    """Outcome of `validate_deployment_grouping`.

    Truthy when no issue has severity `"error"`, so `if not result:` detects a
    grouping that will fail once deployed.

    Attributes:
        groups: Names of the checked groups.
        issues: Issues found, ordered errors first, then warnings, then info.
    """

    groups: tuple[str, ...]
    issues: tuple[DeploymentGroupingIssue, ...] = field(default_factory=tuple)

    @property
    def errors(self) -> tuple[DeploymentGroupingIssue, ...]:
        """Issues with severity `"error"`."""
        return tuple(issue for issue in self.issues if issue.severity == "error")

    @property
    def warnings(self) -> tuple[DeploymentGroupingIssue, ...]:
        """Issues with severity `"warning"`."""
        return tuple(issue for issue in self.issues if issue.severity == "warning")

    @property
    def status(self) -> GroupingStatus:
        """`"failed"` if there is at least one error, otherwise `"passed"`."""
        return "failed" if self.errors else "passed"

    def __bool__(self) -> bool:
        return not self.errors

    def raise_if_failed(self) -> None:
        """Raise `DeploymentGroupingError` if there is at least one error."""
        if self.errors:
            raise DeploymentGroupingError(self)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""
        return {
            "status": self.status,
            "groups": list(self.groups),
            "issues": [issue.to_dict() for issue in self.issues],
        }


class DeploymentGroupingError(Exception):
    """Raised by `DeploymentGroupingResult.raise_if_failed` when a grouping has errors.

    Attributes:
        result: The result that contained the errors.
    """

    def __init__(self, result: DeploymentGroupingResult):
        self.result = result
        details = "\n".join(f"- {issue.message}" for issue in result.errors)
        super().__init__(f"Node grouping failed validation:\n{details}")


@dataclass(frozen=True)
class _DatasetInfo:
    """What the check needs to know about a catalog dataset."""

    type: str
    ephemeral: bool
    filepath: str | None = None


@dataclass
class _DatasetBoundary:
    """A dataset produced in one group and read in at least one other.

    Attributes:
        dataset: Dataset name without any transcoding suffix.
        producer_group: Name of the group whose node produces the dataset.
        catalog_names: Every name the dataset is written or read under across
            the boundary. A transcoded dataset has several, such as `df@spark`
            and `df@pandas`, and each has its own catalog entry.
        consumer_groups: Names of the other groups whose nodes read the dataset.
    """

    dataset: str
    producer_group: str
    catalog_names: set[str]
    consumer_groups: set[str] = field(default_factory=set)


def _type_name(dataset_type: Any) -> str:
    if isinstance(dataset_type, type):
        return f"{dataset_type.__module__}.{dataset_type.__qualname__}"
    return str(dataset_type)


def _is_kedro_io_type(type_name: str, class_names: frozenset[str]) -> bool:
    """Whether `type_name` names one of `class_names` from `kedro.io`.

    Catalog entries may spell a type as `MemoryDataset`, `kedro.io.MemoryDataset`
    or `kedro.io.memory_dataset.MemoryDataset`.
    """
    module, _, class_name = type_name.rpartition(".")
    return class_name in class_names and (
        module in ("", "kedro.io") or module.startswith("kedro.io.")
    )


def _is_in_process_path(filepath: str | None) -> bool:
    if filepath is None:
        return False
    protocol, _ = get_protocol_and_path(filepath)
    return protocol in _IN_PROCESS_PROTOCOLS


def _describe_dataset_object(dataset: Any) -> _DatasetInfo:
    if isinstance(dataset, CachedDataset):
        return _describe_dataset_object(dataset._dataset)
    filepath = next(
        (
            str(getattr(dataset, f"_{key}"))
            for key in _FILEPATH_KEYS
            if getattr(dataset, f"_{key}", None) is not None
        ),
        None,
    )
    protocol = getattr(dataset, "_protocol", None)
    if filepath is not None and protocol and protocol != "file":
        filepath = f"{protocol}://{filepath}"
    return _DatasetInfo(
        type=_type_name(type(dataset)),
        ephemeral=bool(getattr(dataset, "_EPHEMERAL", False))
        or _is_in_process_path(filepath),
        filepath=filepath,
    )


def _describe_dataset_config(config: dict[str, Any]) -> _DatasetInfo:
    type_name = _type_name(config.get("type", ""))
    if _is_kedro_io_type(type_name, _CACHED_TYPES):
        wrapped = config.get("dataset")
        if isinstance(wrapped, dict):
            return _describe_dataset_config(wrapped)
        return _describe_dataset_object(wrapped)
    filepath = next(
        (str(config[key]) for key in _FILEPATH_KEYS if config.get(key)), None
    )
    return _DatasetInfo(
        type=type_name,
        ephemeral=_is_kedro_io_type(type_name, _EPHEMERAL_TYPES)
        or _is_in_process_path(filepath),
        filepath=filepath,
    )


def _describe_dataset(catalog: CatalogProtocol, name: str) -> _DatasetInfo:
    """Describe a dataset the way the catalog would resolve it at run time.

    Dataset objects added to the catalog directly are inspected as they are.
    Everything else is resolved from configuration: explicit entries, dataset
    factory patterns, a user catch-all pattern, and finally the catalog's
    runtime default, which is an in-memory dataset.
    """
    datasets = getattr(catalog, "_datasets", {})
    if name in datasets:
        return _describe_dataset_object(datasets[name])

    lazy_datasets = getattr(catalog, "_lazy_datasets", {})
    if name in lazy_datasets:
        return _describe_dataset_config(lazy_datasets[name].config)

    resolver = getattr(catalog, "config_resolver", None)
    if resolver is None:
        if name in catalog:
            return _describe_dataset_object(catalog[name])
        return _DatasetInfo(type="kedro.io.MemoryDataset", ephemeral=True)

    pattern = (
        resolver.match_dataset_pattern(name)
        or resolver.match_user_catch_all_pattern(name)
        or resolver.match_runtime_pattern(name)
    )
    config = resolver._resolve_dataset_config(
        name, pattern, copy.deepcopy(resolver._get_pattern_config(pattern))
    )
    return _describe_dataset_config(config)


def _is_local_path(filepath: str) -> bool:
    if filepath.lower().startswith(_SHARED_MOUNT_PREFIXES):
        return False
    protocol, _ = get_protocol_and_path(filepath)
    return protocol == "file"


def _quoted(names: Iterable[str]) -> str:
    return ", ".join(f"'{name}'" for name in names)


def _groups_phrase(groups: list[str]) -> str:
    noun = "group" if len(groups) == 1 else "groups"
    return f"{noun} {_quoted(groups)}"


def _check_structure(
    pipeline: Pipeline, groups: list[GroupedNodes]
) -> list[DeploymentGroupingIssue]:
    """Check that `groups` assigns every pipeline node to exactly one group."""
    issues = []

    repeated_names = sorted(
        name for name, count in Counter(g.name for g in groups).items() if count > 1
    )
    if repeated_names:
        issues.append(
            DeploymentGroupingIssue(
                code="invalid_grouping",
                severity="error",
                message=(
                    f"Group names {_quoted(repeated_names)} are used more than once. "
                    "Each group becomes one task, so group names must be unique."
                ),
                groups=tuple(repeated_names),
            )
        )

    empty = sorted(g.name for g in groups if not g.nodes)
    if empty:
        issues.append(
            DeploymentGroupingIssue(
                code="invalid_grouping",
                severity="error",
                message=f"Groups {_quoted(empty)} contain no nodes.",
                groups=tuple(empty),
            )
        )

    membership: dict[str, set[str]] = defaultdict(set)
    for group in groups:
        for node_name in group.nodes:
            membership[node_name].add(group.name)
    pipeline_nodes = {node.name for node in pipeline.nodes}

    unknown = sorted(set(membership) - pipeline_nodes)
    if unknown:
        issues.append(
            DeploymentGroupingIssue(
                code="invalid_grouping",
                severity="error",
                message=f"Nodes {_quoted(unknown)} are in a group but not in the pipeline.",
                nodes=tuple(unknown),
            )
        )

    repeated_nodes = sorted(
        name for name, owners in membership.items() if len(owners) > 1
    )
    if repeated_nodes:
        owners = sorted(
            {owner for name in repeated_nodes for owner in membership[name]}
        )
        issues.append(
            DeploymentGroupingIssue(
                code="invalid_grouping",
                severity="error",
                message=(
                    f"Nodes {_quoted(repeated_nodes)} are in more than one group, "
                    "so they would run more than once."
                ),
                groups=tuple(owners),
                nodes=tuple(repeated_nodes),
            )
        )

    missing = sorted(pipeline_nodes - set(membership))
    if missing:
        issues.append(
            DeploymentGroupingIssue(
                code="invalid_grouping",
                severity="error",
                message=(
                    f"Nodes {_quoted(missing)} are not in any group, so they would never run."
                ),
                nodes=tuple(missing),
            )
        )

    return issues


def _find_dataset_boundaries(
    pipeline: Pipeline, node_to_group: dict[str, str]
) -> list[_DatasetBoundary]:
    """Find datasets produced in one group and used in another.

    Transcoded names such as `df@spark` and `df@pandas` refer to one dataset, so
    they are matched on the name without the transcoding suffix. Every spelling
    used across the boundary is kept, since each has its own catalog entry.
    """
    producers: dict[str, tuple[str, str]] = {}
    for node in pipeline.nodes:
        for output in node.outputs:
            producers[_strip_transcoding(output)] = (node_to_group[node.name], output)

    boundaries: dict[str, _DatasetBoundary] = {}
    for node in pipeline.nodes:
        group = node_to_group[node.name]
        for input_ in node.inputs:
            dataset = _strip_transcoding(input_)
            if dataset not in producers:
                continue
            producer, output = producers[dataset]
            if producer == group:
                continue
            boundary = boundaries.setdefault(
                dataset,
                _DatasetBoundary(
                    dataset=dataset, producer_group=producer, catalog_names={output}
                ),
            )
            boundary.catalog_names.add(input_)
            boundary.consumer_groups.add(group)

    return [boundaries[dataset] for dataset in sorted(boundaries)]


def _check_cycles(
    group_names: Iterable[str], boundaries: list[_DatasetBoundary]
) -> list[DeploymentGroupingIssue]:
    graph: dict[str, set[str]] = {name: set() for name in sorted(group_names)}
    for boundary in boundaries:
        for consumer in boundary.consumer_groups:
            graph[consumer].add(boundary.producer_group)

    try:
        tuple(TopologicalSorter(graph).static_order())
    except CycleError as exc:
        cycle = [str(name) for name in exc.args[1]]
        return [
            DeploymentGroupingIssue(
                code="group_cycle",
                severity="error",
                message=(
                    f"Groups {' -> '.join(cycle)} depend on each other in a cycle, "
                    "so they cannot run as separate tasks in any order. This usually "
                    "means a namespace is interrupted by a node outside it. Move that "
                    "node into the namespace, or split the namespace in two."
                ),
                groups=tuple(dict.fromkeys(cycle)),
            )
        ]
    return []


def _check_dataset_boundaries(
    catalog: CatalogProtocol, boundaries: list[_DatasetBoundary]
) -> list[DeploymentGroupingIssue]:
    issues = []
    for boundary in boundaries:
        consumers = sorted(boundary.consumer_groups)
        involved = (boundary.producer_group, *consumers)
        described = {
            name: _describe_dataset(catalog, name)
            for name in sorted(boundary.catalog_names)
        }
        passage = f"is passed from group '{boundary.producer_group}' to {_groups_phrase(consumers)}"

        in_memory = [name for name, info in described.items() if info.ephemeral]
        if in_memory:
            issues.append(
                DeploymentGroupingIssue(
                    code="ephemeral_boundary",
                    severity="error",
                    message=(
                        f"Dataset {_quoted(in_memory)} {passage} but is only kept in "
                        "memory, so it will not exist when the receiving group runs "
                        "as a separate task. Add a catalog entry that saves it to "
                        "shared storage, or move the nodes that use it into group "
                        f"'{boundary.producer_group}'."
                    ),
                    datasets=tuple(in_memory),
                    groups=involved,
                )
            )
            continue

        local = [
            (name, info.filepath)
            for name, info in described.items()
            if info.filepath and _is_local_path(info.filepath)
        ]
        if local:
            paths = ", ".join(f"'{filepath}'" for _, filepath in local)
            issues.append(
                DeploymentGroupingIssue(
                    code="local_boundary",
                    severity="warning",
                    message=(
                        f"Dataset {_quoted(name for name, _ in local)} {passage} and "
                        f"is saved to local path {paths}. Local disk is not shared "
                        "between tasks that run on different machines. Use shared "
                        "storage such as S3, ADLS, GCS or a Databricks volume if the "
                        "groups run on separate machines."
                    ),
                    datasets=tuple(name for name, _ in local),
                    groups=involved,
                )
            )
    return issues


def _check_single_node_groups(
    groups: list[GroupedNodes],
) -> list[DeploymentGroupingIssue]:
    single = [g for g in groups if len(g.nodes) == 1]
    if not single:
        return []
    names = tuple(g.name for g in single)
    return [
        DeploymentGroupingIssue(
            code="single_node_groups",
            severity="info",
            message=(
                f"{len(names)} group(s) contain a single node and each run as a "
                f"separate task: {_quoted(names)}. Nodes in the same namespace run "
                "together in one task."
            ),
            groups=names,
            nodes=tuple(g.nodes[0] for g in single),
        )
    ]


def validate_deployment_grouping(
    pipeline: Pipeline,
    catalog: CatalogProtocol,
    groups: list[GroupedNodes] | None = None,
    group_by: str | None = "namespace",
) -> DeploymentGroupingResult:
    """Check that a node grouping can run with each group as a separate task.

    Deployment platforms such as Airflow or Databricks run each group from
    `Pipeline.group_nodes_by` as its own task, usually in its own container, so
    groups do not share memory or local disk. This function reports the
    problems that only appear once that happens:

    - `invalid_grouping` (error): only for `groups` passed in. A node is in no
      group, in more than one group or not in the pipeline, a group is empty, or
      a group name is repeated. The remaining checks are skipped.
    - `group_cycle` (error): groups depend on each other in a loop, usually
      because a namespace is interrupted by a node outside it.
    - `ephemeral_boundary` (error): a dataset produced in one group and used in
      another is only kept in memory.
    - `local_boundary` (warning): a dataset passed between groups is saved to
      local disk. Databricks shared paths such as `/dbfs/` and `/Volumes/` are
      not reported.
    - `single_node_groups` (info): groups that contain one node.

    Datasets are resolved the way the catalog resolves them at run time,
    including dataset factories and catch-all patterns, but from configuration
    only: no data is loaded and no dataset class is imported. The function
    never raises for issues it finds; call `raise_if_failed` on the result to
    raise.

    Args:
        pipeline: The pipeline to deploy.
        catalog: The catalog the deployed pipeline will use.
        groups: Groups to check. Defaults to `pipeline.group_nodes_by(group_by)`.
        group_by: Grouping strategy passed to `Pipeline.group_nodes_by` when
            `groups` is not given.

    Returns:
        A `DeploymentGroupingResult`, truthy when no errors were found.

    Example:
    ```python
        from kedro.inspection import validate_deployment_grouping

        result = validate_deployment_grouping(pipeline, catalog)
        if not result:
            for issue in result.errors:
                print(issue.message)
    ```
    """
    if groups is None:
        groups = pipeline.group_nodes_by(group_by)
    group_names = tuple(g.name for g in groups)

    structural = _check_structure(pipeline, groups)
    if structural:
        return DeploymentGroupingResult(groups=group_names, issues=tuple(structural))

    node_to_group = {node_name: g.name for g in groups for node_name in g.nodes}
    boundaries = _find_dataset_boundaries(pipeline, node_to_group)
    issues = [
        *_check_cycles(group_names, boundaries),
        *_check_dataset_boundaries(catalog, boundaries),
        *_check_single_node_groups(groups),
    ]
    issues.sort(key=lambda issue: _SEVERITY_ORDER[issue.severity])
    return DeploymentGroupingResult(groups=group_names, issues=tuple(issues))
