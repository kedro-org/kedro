"""FastAPI HTTP server factory and route definitions for Kedro."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from kedro import __version__ as kedro_version
from kedro.framework.startup import bootstrap_project
from kedro.server.config import get_project_path
from kedro.server.models import (
    ErrorDetail,
    HealthResponse,
    RunRequest,
    RunResponse,
)
from kedro.server.runner import execute_pipeline

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.

    Bootstraps the Kedro project on startup.
    """
    project_path = get_project_path()
    logger.info("Bootstrapping Kedro project at: %s", project_path)
    bootstrap_project(project_path)
    logger.info("Kedro server started successfully")
    yield
    # Cleanup on shutdown (if needed in future)
    logger.info("Kedro server shutting down")


def create_http_server() -> FastAPI:
    """Create and configure the FastAPI HTTP server.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="Kedro Server",
        description="HTTP API for running Kedro pipelines",
        version=kedro_version,
        lifespan=lifespan,
    )

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        """Health check endpoint.

        Returns server status and Kedro version information.
        """
        try:
            project_path = get_project_path()
            return HealthResponse(
                status="healthy",
                kedro_version=kedro_version,
                project_path=str(project_path),
            )
        except Exception:
            return HealthResponse(
                status="healthy",
                kedro_version=kedro_version,
                project_path=None,
            )

    @app.post("/run", response_model=RunResponse, tags=["pipeline"])
    async def run_pipeline(request: RunRequest) -> RunResponse:
        """Execute a Kedro pipeline.

        This endpoint mirrors the behavior of `kedro run` CLI command.
        Each request creates a fresh KedroSession and executes the pipeline
        synchronously.

        Args:
            request: Pipeline execution parameters.

        Returns:
            RunResponse with run_id, status, duration, and optional error details.
        """
        project_path = get_project_path()

        result = execute_pipeline(
            project_path,
            pipeline=request.pipeline,
            pipeline_names=request.pipelines,
            env=request.env,
            conf_source=request.conf_source,
            params=request.params,
            runner=request.runner,
            is_async=request.is_async,
            tags=request.tags,
            node_names=request.node_names,
            from_nodes=request.from_nodes,
            to_nodes=request.to_nodes,
            from_inputs=request.from_inputs,
            to_outputs=request.to_outputs,
            load_versions=request.load_versions,
            namespaces=request.namespaces,
            only_missing_outputs=request.only_missing_outputs,
        )

        error_detail = None
        if result.error:
            error_detail = ErrorDetail(
                type=result.error.type,
                message=result.error.message,
                traceback=result.error.traceback,
            )

        return RunResponse(
            run_id=result.run_id,
            status=result.status,
            duration_ms=result.duration_ms,
            error=error_detail,
        )

    return app
