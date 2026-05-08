"""Pydantic models for Kedro server request/response schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RunRequest(BaseModel):
    """Request model for pipeline execution.

    This model captures the parameters that can be sent in a request to the `/run` endpoint of the Kedro HTTP server.
    Unlike the `kedro run` CLI command, `conf_source` and `env` are not included in this request model, as they are
    expected to be set at the server level (e.g. via environment variables or server configuration) rather than per request.
    """

    from_inputs: list[str] | None = Field(
        default=None,
        description="A list of dataset names which should be used as a starting point.",
    )
    to_outputs: list[str] | None = Field(
        default=None,
        description="A list of dataset names which should be used as an end point.",
    )
    from_nodes: list[str] | None = Field(
        default=None,
        description="A list of node names which should be used as a starting point.",
    )
    to_nodes: list[str] | None = Field(
        default=None,
        description="A list of node names which should be used as an end point.",
    )
    node_names: list[str] | None = Field(
        default=None,
        description="Run only nodes with specified names.",
    )
    runner: str | None = Field(
        default=None,
        description="Runner to use. Any importable subclass of `kedro.runner.AbstractRunner`.",
    )
    is_async: bool = Field(
        default=False,
        description="Load and save node inputs and outputs asynchronously with threads.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Construct the pipeline using only nodes which have this tag attached.",
    )
    load_versions: dict[str, str] | None = Field(
        default=None,
        description="Specify a particular dataset version for loading.",
    )
    pipeline_names: list[str] | None = Field(
        default=None,
        description="List of registered pipeline names to run.",
    )
    namespaces: list[str] | None = Field(
        default=None,
        description="Run only nodes within these namespaces.",
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description="Extra parameters to pass to the context at runtime.",
    )
    only_missing_outputs: bool = Field(
        default=False,
        description="Run only nodes with missing outputs. Skip nodes whose outputs already exist and are persisted.",
    )
    model_config = ConfigDict(
        extra="forbid"
    )  # Forbid extra fields to prevent silent errors (conf_source and env should not be included in the request)


class ErrorDetail(BaseModel):
    """Structured error information."""

    type: str = Field(description="Exception type name.")
    message: str = Field(description="Error message.")
    traceback: list[str] | None = Field(
        default=None,
        description="Stack trace lines, if available. Only included for errors raised during pipeline execution.",
    )


class RunResponse(BaseModel):
    """Response model for pipeline execution."""

    run_id: str = Field(description="Unique identifier for this pipeline run.")
    status: Literal["success", "failure"] = Field(description="Run status.")
    duration_ms: float = Field(description="Total execution time in milliseconds.")
    error: ErrorDetail | None = Field(
        default=None,
        description="Error details if status is 'failure'.",
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: Literal["healthy", "unhealthy"] = Field(
        default="healthy", description="Server health status."
    )
    kedro_version: str = Field(description="Kedro version.")
    project_path: str | None = Field(
        default=None,
        description="Path to the Kedro project being served.",
    )


class NodeSnapshotResponse(BaseModel):
    """Response model for a single pipeline node snapshot."""

    name: str = Field(description="Fully-qualified node name.")
    namespace: str | None = Field(default=None, description="Node namespace, if any.")
    tags: list[str] = Field(
        default_factory=list, description="Tags assigned to the node."
    )
    inputs: list[str] = Field(default_factory=list, description="Input dataset names.")
    outputs: list[str] = Field(
        default_factory=list, description="Output dataset names."
    )


class PipelineSnapshotResponse(BaseModel):
    """Response model for a registered pipeline snapshot."""

    name: str = Field(description="Pipeline registry key.")
    nodes: list[NodeSnapshotResponse] = Field(
        default_factory=list, description="Nodes in topological execution order."
    )
    inputs: list[str] = Field(default_factory=list, description="Free pipeline inputs.")
    outputs: list[str] = Field(
        default_factory=list, description="Final pipeline outputs."
    )


class DatasetSnapshotResponse(BaseModel):
    """Response model for a catalog dataset snapshot."""

    name: str = Field(description="Dataset name as it appears in the catalog.")
    type: str = Field(description="Dataset type string.")
    filepath: str | None = Field(
        default=None, description="File path if present, with credentials redacted."
    )


class ProjectMetadataSnapshotResponse(BaseModel):
    """Response model for project metadata snapshot."""

    project_name: str = Field(description="Human-readable project name.")
    package_name: str = Field(description="Python package name.")
    kedro_version: str = Field(description="Kedro version from project metadata.")


class SnapshotResponse(BaseModel):
    """Response model for the project snapshot endpoint."""

    status: Literal["success", "failure"] = Field(description="Snapshot status.")
    metadata: ProjectMetadataSnapshotResponse | None = Field(
        default=None, description="Project metadata snapshot."
    )
    pipelines: list[PipelineSnapshotResponse] | None = Field(
        default=None, description="Registered pipeline snapshots."
    )
    datasets: dict[str, DatasetSnapshotResponse] | None = Field(
        default=None, description="Catalog dataset snapshots keyed by dataset name."
    )
    parameters: list[str] | None = Field(
        default=None, description="Sorted list of top-level parameter keys."
    )
    error: ErrorDetail | None = Field(
        default=None, description="Error details if status is 'failure'."
    )
