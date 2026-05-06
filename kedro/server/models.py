"""Pydantic models and dataclasses for Kedro server request/response schemas."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


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
