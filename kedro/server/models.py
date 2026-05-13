"""Pydantic models for Kedro server request/response schemas."""

from __future__ import annotations

import re
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from kedro.inspection.models import (  # noqa: TCH001
    DatasetSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
)

# Matches a valid Python dotted identifier, e.g. "SequentialRunner" or
# "mypackage.runners.MyRunner".  Prevents passing arbitrary strings to
# importlib.import_module before the AbstractRunner subclass check runs.
_RUNNER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*$")


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

    @field_validator("runner")
    @classmethod
    def _validate_runner_format(cls, v: str | None) -> str | None:
        if v is not None and not _RUNNER_PATTERN.match(v):
            raise ValueError(
                f"runner '{v}' is not a valid Python dotted identifier. "
                "Expected a class name or dotted module path, e.g. 'SequentialRunner' "
                "or 'mypackage.runners.MyRunner'."
            )
        return v

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


class SnapshotResponse(BaseModel):
    """Response model for the project snapshot endpoint."""

    status: Literal["success", "failure"] = Field(description="Snapshot status.")
    metadata: ProjectMetadataSnapshot | None = Field(
        default=None, description="Project metadata snapshot."
    )
    pipelines: list[PipelineSnapshot] | None = Field(
        default=None, description="Registered pipeline snapshots."
    )
    datasets: dict[str, DatasetSnapshot] | None = Field(
        default=None, description="Catalog dataset snapshots keyed by dataset name."
    )
    parameters: list[str] | None = Field(
        default=None, description="Sorted list of top-level parameter keys."
    )
    error: ErrorDetail | None = Field(
        default=None, description="Error details if status is 'failure'."
    )
