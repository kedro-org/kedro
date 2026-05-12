"""FastAPI HTTP server factory and route definitions for Kedro."""

from __future__ import annotations

import logging
import os
import threading
import time
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from kedro import __version__ as kedro_version
from kedro.framework.project import settings
from kedro.framework.session.service_session import KedroServiceSession
from kedro.framework.startup import bootstrap_project
from kedro.io.core import generate_timestamp
from kedro.runner import AbstractRunner
from kedro.server.models import (
    ErrorDetail,
    HealthResponse,
    RunRequest,
    RunResponse,
)
from kedro.server.utils import (
    KEDRO_SERVER_CONF_SOURCE,
    KEDRO_SERVER_ENV,
    _resolve_project_path,
)
from kedro.utils import load_obj

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator
    from pathlib import Path

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan context manager for FastAPI application.

    Bootstraps the Kedro project on startup.
    """
    project_path = app.state.project_path
    logger.info("Bootstrapping Kedro project at: %s", project_path)
    bootstrap_project(project_path)

    if settings.SESSION_CLASS is not KedroServiceSession:
        logger.warning(
            "The Kedro HTTP server is designed to work with KedroServiceSession. Not using the `SESSION_CLASS` specified in the settings.",
        )

    logger.info("Kedro server started successfully")

    yield
    logger.info("Kedro server shutting down")
    with app.state.session_lock:
        if hasattr(app.state, "session"):
            app.state.session.close()


def create_http_server(
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
) -> FastAPI:
    """Create and configure the FastAPI HTTP server.

    Programmatic values passed to this factory take precedence over
    environment-variable defaults set by the CLI.

    Args:
        project_path: Optional path to the Kedro project to serve. If not provided,
            it will be resolved from KEDRO_PROJECT_PATH environment variable.
        env: Optional Kedro environment to use. Overrides the KEDRO_SERVER_ENV environment variable if provided.
        conf_source: Optional configuration source to use. Overrides the KEDRO_SERVER_CONF_SOURCE environment variable if provided.
    Returns:
        Configured FastAPI application instance.
    """
    resolved_env = env if env is not None else os.environ.get(KEDRO_SERVER_ENV)
    resolved_conf_source = (
        conf_source
        if conf_source is not None
        else os.environ.get(KEDRO_SERVER_CONF_SOURCE)
    )

    app = FastAPI(
        title="Kedro Server",
        description="HTTP API for running Kedro pipelines",
        version=kedro_version,
        lifespan=lifespan,
    )
    app.state.default_env = resolved_env
    app.state.default_conf_source = resolved_conf_source
    app.state.project_path = _resolve_project_path(project_path)
    app.state.session_lock = threading.Lock()

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        """Health check endpoint.

        Returns server status and Kedro version information.
        """
        return HealthResponse(
            status="healthy",
            kedro_version=kedro_version,
        )

    @app.post("/run", response_model=RunResponse, tags=["pipeline"])
    def run_pipeline(request: RunRequest) -> RunResponse:
        """Execute a Kedro pipeline.

        This endpoint accepts a `RunRequest` with parameters for pipeline execution,
        runs the pipeline using the session, and returns a `RunResponse` with the result.
        First run request creates a new `KedroServiceSession`, and subsequent requests reuse it.

        Args:
            request: Pipeline execution parameters.

        Returns:
            `RunResponse` with run_id, status, duration, and optional error details.
        """
        with app.state.session_lock:
            if not hasattr(app.state, "session"):
                app.state.session = KedroServiceSession.create(
                    project_path=app.state.project_path,
                    env=app.state.default_env,
                    conf_source=app.state.default_conf_source,
                )

        return _execute_pipeline(session=app.state.session, request=request)

    return app


def _execute_pipeline(
    session: KedroServiceSession,
    *,
    request: RunRequest,
) -> RunResponse:
    """Execute a Kedro pipeline and return a structured result.

    It receives a `KedroServiceSession` and a `RunRequest` as input, resolves
    the runner, calls ``session.run()``, and returns a
    `RunResponse`.

    Args:
        session: Kedro service session to use for pipeline execution.
        request: Pipeline execution parameters.

    Returns:
        A `RunResponse` with run id, status, duration,
        and optional error details.
    """
    run_id: str = generate_timestamp()
    start_time = time.perf_counter()

    try:
        runner_name = request.runner or "SequentialRunner"
        runner_class = load_obj(runner_name, "kedro.runner")
        if not (
            isinstance(runner_class, type) and issubclass(runner_class, AbstractRunner)
        ):
            raise ValueError(
                f"Runner '{runner_name}' is not a subclass of AbstractRunner. "
                "Only AbstractRunner subclasses are permitted."
            )
        runner_obj = runner_class(is_async=request.is_async)

        session.run(
            run_id=run_id,
            pipeline_names=request.pipeline_names,
            tags=tuple(request.tags) if request.tags else None,
            runner=runner_obj,
            node_names=tuple(request.node_names) if request.node_names else None,
            from_nodes=request.from_nodes,
            to_nodes=request.to_nodes,
            from_inputs=request.from_inputs,
            to_outputs=request.to_outputs,
            load_versions=request.load_versions,
            namespaces=request.namespaces,
            only_missing_outputs=request.only_missing_outputs,
            runtime_params=request.params,
        )

        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.info("Pipeline run %s completed in %.2fms", run_id, duration_ms)
        return RunResponse(
            run_id=run_id,
            status="success",
            duration_ms=round(duration_ms, 2),
        )

    except Exception as exc:
        duration_ms = (time.perf_counter() - start_time) * 1000
        logger.error(
            "Pipeline run %s failed: %s",
            run_id,
            str(exc),
            exc_info=True,
        )

        error_detail = ErrorDetail(
            type=type(exc).__qualname__,
            message=str(exc),
        )

        return RunResponse(
            run_id=run_id,
            status="failure",
            duration_ms=round(duration_ms, 2),
            error=error_detail,
        )
