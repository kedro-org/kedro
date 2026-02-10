"""FastAPI application factory and route definitions for Kedro server."""

from __future__ import annotations

import logging
import time
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI, HTTPException

from kedro import __version__ as kedro_version
from kedro.framework.session import KedroSession
from kedro.framework.startup import bootstrap_project
from kedro.server.config import get_project_path, is_debug_mode
from kedro.server.models import (
    ErrorDetail,
    HealthResponse,
    RunRequest,
    RunResponse,
)
from kedro.utils import load_obj

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


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

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
        start_time = time.perf_counter()
        run_id: str | None = None
        debug_mode = is_debug_mode()

        # Validate that pipeline and pipelines are not both set
        if request.pipeline and request.pipelines:
            raise HTTPException(
                status_code=400,
                detail="Cannot specify both 'pipeline' and 'pipelines'. Use one or the other.",
            )

        try:
            # Load runner class (default to SequentialRunner if not specified)
            runner_name = request.runner or "SequentialRunner"
            runner_class = load_obj(runner_name, "kedro.runner")
            runner_obj = runner_class(is_async=request.is_async)

            # Create a fresh session for this request
            with KedroSession.create(
                project_path=project_path,
                env=request.env,
                conf_source=request.conf_source,
                runtime_params=request.params,
            ) as session:
                run_id = session.session_id

                logger.info(
                    "Starting pipeline run %s (pipeline=%s, env=%s)",
                    run_id,
                    request.pipeline or "__default__",
                    request.env,
                )

                # Execute the pipeline with all provided parameters
                session.run(
                    pipeline_name=request.pipeline,
                    pipeline_names=request.pipelines,
                    tags=tuple(request.tags) if request.tags else None,
                    runner=runner_obj,
                    node_names=tuple(request.node_names)
                    if request.node_names
                    else None,
                    from_nodes=request.from_nodes,
                    to_nodes=request.to_nodes,
                    from_inputs=request.from_inputs,
                    to_outputs=request.to_outputs,
                    load_versions=request.load_versions,
                    namespaces=request.namespaces,
                    only_missing_outputs=request.only_missing_outputs,
                )

            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.info(
                "Pipeline run %s completed successfully in %.2fms", run_id, duration_ms
            )

            return RunResponse(
                run_id=run_id,
                status="success",
                duration_ms=duration_ms,
            )

        except Exception as exc:
            duration_ms = (time.perf_counter() - start_time) * 1000
            exc_type = type(exc)
            exc_module = (
                [] if exc_type.__module__ == "builtins" else [exc_type.__module__]
            )
            exc_module.append(exc_type.__qualname__)

            logger.error(
                "Pipeline run %s failed after %.2fms: %s",
                run_id or "unknown",
                duration_ms,
                str(exc),
                exc_info=True,
            )

            error_detail = ErrorDetail(
                type=".".join(exc_module),
                message=str(exc),
                traceback=traceback.format_tb(exc.__traceback__)
                if debug_mode
                else None,
            )

            return RunResponse(
                run_id=run_id or "unknown",
                status="failed",
                duration_ms=duration_ms,
                error=error_detail,
            )

    return app
