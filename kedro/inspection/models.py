"""Pydantic models for Kedro-native project snapshot (inspection API)."""

from __future__ import annotations

from pydantic import BaseModel


class ProjectMetadataSnapshot(BaseModel):
    """Project identity from pyproject.toml [tool.kedro]."""

    project_name: str
    package_name: str
    kedro_version: str


class NodeSnapshot(BaseModel):
    """Serializable view of a Kedro Node. func is omitted (not serializable)."""

    name: str
    namespace: str | None = None
    tags: list[str] = []
    inputs: list[str] = []
    outputs: list[str] = []


class PipelineSnapshot(BaseModel):
    """Serializable view of a registered Pipeline."""

    id: str  # pipeline registry key
    name: str
    nodes: list[NodeSnapshot]
    inputs: list[str] = []  # free inputs of the whole pipeline
    outputs: list[str] = []  # terminal outputs of the whole pipeline
    parameters: list[str] = []
    tags: list[str] = []
    namespace: str | None = None


class DatasetSnapshot(BaseModel):
    """Resolved catalog entry - config only, no data loaded."""

    name: str
    type: str  # e.g. "pandas.CSVDataset"
    filepath: str | None = None  # resolved from config; null for MemoryDataset
    is_pattern: bool = False  # True if this entry is a factory pattern template, not a concrete dataset
    is_free_input: bool | None = (
        None  # None = not computed (Tier 1); True/False set by Tier 2
    )


class ProjectSnapshot(BaseModel):
    """Complete project snapshot. The top-level return type of get_snapshot()."""

    metadata: ProjectMetadataSnapshot
    pipelines: list[PipelineSnapshot]
    datasets: dict[str, DatasetSnapshot]
    parameter_keys: list[str] = []  # parameter names only, not values
    has_missing_deps: bool = False  # only if we take the route of mocking deps
    mocked_dependencies: list[str] = []  # only if we take the route of mocking deps
