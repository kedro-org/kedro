"""Pydantic models for Kedro-native project snapshot (inspection API)."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ProjectMetadataSnapshot(BaseModel):
    """Kedro project identity and layout — from pyproject.toml / settings.

    project_name comes from [tool.kedro] project_name in pyproject.toml.
    """

    project_name: str
    project_path: str
    package_name: str
    kedro_version: str
    source_dir: str
    environments: list[str]
    config_paths: list[str]


class NodeSnapshot(BaseModel):
    """
    Serializable snapshot of a Kedro Node; fields match the Node constructor API.
    See: https://docs.kedro.org/en/stable/api/pipeline/kedro.pipeline.node/

    Node(func, inputs, outputs, *, name=None, tags=None, confirms=None, namespace=None, preview_fn=None)
    We omit func and preview_fn (not serializable). inputs/outputs are normalized to list[str].
    """

    name: str
    namespace: str | None = None
    tags: list[str] = []
    inputs: list[str] = []
    outputs: list[str] = []
    confirms: list[str] = []


class PipelineSnapshot(BaseModel):
    """
    Serializable snapshot of a Kedro Pipeline; fields match the Pipeline constructor API.
    See: https://docs.kedro.org/en/stable/api/pipeline/kedro.pipeline.Pipeline/

    Pipeline(nodes, *, inputs=None, outputs=None, parameters=None, tags=None,
             namespace=None, prefix_datasets_with_namespace=True)
    We add id and name (pipeline id/name in registry). Collection fields are list[str] for JSON.
    """

    id: str
    name: str
    nodes: list[NodeSnapshot]
    inputs: list[str] = []
    outputs: list[str] = []
    parameters: list[str] = []
    tags: list[str] = []
    namespace: str | None = None
    prefix_datasets_with_namespace: bool = True


class DatasetConfigSnapshot(BaseModel):
    """Resolved catalog entry for one dataset: type string only (no materialization)."""

    name: str
    type: str
    is_free_input: bool = False


class ProjectSnapshot(BaseModel):
    """
    Complete snapshot of a Kedro project using only Kedro-native concepts:
    pipelines, nodes (with inputs/outputs), catalog dataset types, and parameters.
    """

    metadata: ProjectMetadataSnapshot
    pipelines: list[PipelineSnapshot]
    datasets: dict[str, DatasetConfigSnapshot]
    parameters: dict[str, Any]
    has_missing_deps: bool = False
    mocked_dependencies: list[str] = []
