"""FastAPI HTTP server factory and route definitions for Kedro."""

from __future__ import annotations

import logging
import os
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path
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
    get_project_path,
)

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


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
    app.state.project_path = (
        Path(project_path).resolve() if project_path is not None else get_project_path()
    )

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

    