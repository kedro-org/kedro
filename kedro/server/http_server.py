"""FastAPI HTTP server factory and route definitions for Kedro."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastapi import FastAPI

from kedro import __version__ as kedro_version
from kedro.framework.startup import bootstrap_project
from kedro.server.models import (
    HealthResponse,
)
from kedro.server.utils import (
    KEDRO_SERVER_CONF_SOURCE,
    KEDRO_SERVER_ENV,
    _resolve_project_path,
)

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
    logger.info("Kedro server started successfully")

    yield
    # Cleanup on shutdown (if needed in future)
    logger.info("Kedro server shutting down")


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

    @app.get("/health", response_model=HealthResponse, tags=["health"])
    async def health() -> HealthResponse:
        """Health check endpoint.

        Returns server status and Kedro version information.
        """
        project_path = app.state.project_path
        return HealthResponse(
            status="healthy",
            kedro_version=kedro_version,
            project_path=str(project_path),
        )

    return app
