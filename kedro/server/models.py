"""Pydantic models for Kedro server request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RunRequest(BaseModel):
    """Request model for pipeline execution.

    Mirrors the parameters available in `kedro run` CLI command.
    Parameter order matches the CLI definition in project.py.
    """

    # Pipeline selection
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
        description="Runner to use. Options: 'SequentialRunner', 'ParallelRunner', 'ThreadRunner'.",
    )
    is_async: bool = Field(
        default=False,
        description="Load and save node inputs and outputs asynchronously with threads.",
    )
    env: str | None = Field(
        default=None,
        description="Kedro configuration environment to use.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Construct the pipeline using only nodes which have this tag attached.",
    )
    load_versions: dict[str, str] | None = Field(
        default=None,
        description="Specify a particular dataset version (timestamp) for loading.",
    )
    pipeline: str | None = Field(
        default=None,
        description="Name of the registered pipeline to run. If not set, '__default__' pipeline is run.",
    )
    pipelines: list[str] | None = Field(
        default=None,
        description="List of registered pipeline names to run. Cannot be used together with 'pipeline'.",
    )
    namespaces: list[str] | None = Field(
        default=None,
        description="Run only nodes within these namespaces.",
    )
    conf_source: str | None = Field(
        default=None,
        description="Path of a directory where project configuration is stored.",
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description="Extra parameters to pass to the context initialiser.",
    )
    only_missing_outputs: bool = Field(
        default=False,
        description="Run only nodes with missing outputs. Skip nodes whose outputs already exist and are persisted.",
    )


class ErrorDetail(BaseModel):
    """Structured error information."""

    type: str = Field(description="Exception type name.")
    message: str = Field(description="Error message.")
    traceback: list[str] | None = Field(
        default=None,
        description="Stack trace lines (only included in debug mode).",
    )


class RunResponse(BaseModel):
    """Response model for pipeline execution."""

    run_id: str = Field(description="Unique identifier for this pipeline run.")
    status: str = Field(description="Run status: 'success' or 'failed'.")
    duration_ms: float = Field(description="Total execution time in milliseconds.")
    error: ErrorDetail | None = Field(
        default=None,
        description="Error details if status is 'failed'.",
    )


class HealthResponse(BaseModel):
    """Response model for health check endpoint."""

    status: str = Field(default="healthy", description="Server health status.")
    kedro_version: str = Field(description="Kedro version.")
    project_path: str | None = Field(
        default=None,
        description="Path to the Kedro project being served.",
    )
