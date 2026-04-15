"""FastAPI HTTP server factory and route definitions for Kedro."""

from __future__ import annotations

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
import time
import traceback
from typing import TYPE_CHECKING, Any

from fastapi import FastAPI

from kedro import __version__ as kedro_version
from kedro.framework.session.abstract_session import AbstractSession
from kedro.framework.session.service_session import KedroServiceSession
from kedro.framework.startup import bootstrap_project
from kedro.io.core import generate_timestamp
from kedro.server.utils import get_project_path, is_debug_mode
from kedro.server.models import (
    ErrorDetail,
    HealthResponse,
    PipelineExecutionError,
    PipelineExecutionResult,
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
    # # Create and store the session
    # session = KedroServiceSession.create(project_path=project_path)
    # app.state.session = session
    
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
        First run request creates a new KedroServiceSession, and subsequent requests reuse it.
        Args:
            request: Pipeline execution parameters.

        Returns:
            RunResponse with run_id, status, duration, and optional error details.
        """
        project_path = get_project_path()
        
        # create a session and assign to app state if not already created
        if not hasattr(app.state, "session"):
            app.state.session = KedroServiceSession.create(project_path=project_path)
        

        result = execute_pipeline(
            session=app.state.session,
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

def execute_pipeline(
    session: AbstractSession,  # noqa: PLR0913
    *,
    pipeline_names: list[str] | None = None,
    env: str | None = None,
    conf_source: str | None = None,
    params: dict[str, Any] | None = None,
    runner: str | None = None,
    is_async: bool = False,
    tags: list[str] | None = None,
    node_names: list[str] | None = None,
    from_nodes: list[str] | None = None,
    to_nodes: list[str] | None = None,
    from_inputs: list[str] | None = None,
    to_outputs: list[str] | None = None,
    load_versions: dict[str, str] | None = None,
    namespaces: list[str] | None = None,
    only_missing_outputs: bool = False,
) -> PipelineExecutionResult:
    """Execute a Kedro pipeline and return a structured result.

    This is the shared execution core used by both the HTTP and MCP
    server interfaces.  It creates a fresh ``KedroServiceSession``, resolves
    the runner, calls ``session.run()``, and returns a
    :class:`PipelineExecutionResult`.

    Args:
        project_path: Path to the Kedro project root.
        pipeline_names: List of pipeline names (mutually exclusive with
            *pipeline*).  When *pipeline* is given it is normalised into
            this list internally.
        env: Configuration environment (e.g. ``'base'``, ``'local'``).
        conf_source: Path to a custom configuration directory.
        params: Runtime parameters for the pipeline context.
        runner: Runner class name: ``'SequentialRunner'``,
            ``'ParallelRunner'``, ``'ThreadRunner'``.
        is_async: Load/save node inputs and outputs asynchronously.
        tags: Run only nodes with these tags.
        node_names: Run only these specific nodes.
        from_nodes: Start execution from these nodes.
        to_nodes: Stop execution at these nodes.
        from_inputs: Start from nodes that produce these datasets.
        to_outputs: Stop at nodes that produce these datasets.
        load_versions: Pin specific dataset versions (name → timestamp).
        namespaces: Run only nodes within these namespaces.
        only_missing_outputs: Skip nodes whose outputs already exist.

    Returns:
        A :class:`PipelineExecutionResult` with run id, status, duration,
        and optional error details.
    """
    start_time = time.perf_counter()
    debug_mode = is_debug_mode()
    run_id: str | None = generate_timestamp()

    try:
        
        runner_name = runner or "SequentialRunner"
        runner_class = load_obj(runner_name, "kedro.runner")
        runner_obj = runner_class(is_async=is_async)

        session.run(
                run_id=run_id,
                pipeline_names=pipeline_names,
                tags=tuple(tags) if tags else None,
                runner=runner_obj,
                node_names=tuple(node_names) if node_names else None,
                from_nodes=from_nodes,
                to_nodes=to_nodes,
                from_inputs=from_inputs,
                to_outputs=to_outputs,
                load_versions=load_versions,
                namespaces=namespaces,
                only_missing_outputs=only_missing_outputs,
                runtime_params=params,
            )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Pipeline run %s completed in %.2fms", run_id, duration_ms)

        return PipelineExecutionResult(
            run_id=run_id,
            status="success",
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Pipeline run %s failed: %s",
            run_id or "unknown",
            str(exc),
            exc_info=True,
        )

        error = PipelineExecutionError(
            type=type(exc).__qualname__,
            message=str(exc),
            traceback=traceback.format_tb(exc.__traceback__) if debug_mode else None,
        )

        return PipelineExecutionResult(
            run_id=run_id or "unknown",
            status="failure",
            duration_ms=round(duration_ms, 2),
            error=error,
        )