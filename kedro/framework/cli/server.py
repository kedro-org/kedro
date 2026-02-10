"""CLI commands for Kedro server."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from kedro.framework.cli.utils import CONTEXT_SETTINGS, KedroCliError
from kedro.framework.startup import bootstrap_project
from kedro.server.config import DEFAULT_HOST, DEFAULT_PORT, KEDRO_PROJECT_PATH_ENV
from kedro.utils import find_kedro_project

if TYPE_CHECKING:
    from kedro.framework.startup import ProjectMetadata


@click.group(name="server")
def server_group() -> None:
    """Commands for running Kedro as an HTTP server."""
    pass


@server_group.command(name="start", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--host",
    "-h",
    type=str,
    default=DEFAULT_HOST,
    help=f"Host to bind the server to. Default: {DEFAULT_HOST}",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=DEFAULT_PORT,
    help=f"Port to bind the server to. Default: {DEFAULT_PORT}",
)
@click.option(
    "--reload",
    is_flag=True,
    default=False,
    help="Enable auto-reload for development. Server restarts on code changes.",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug mode. Includes stack traces in error responses.",
)
@click.pass_obj
def start(
    metadata: ProjectMetadata | None,
    host: str,
    port: int,
    reload: bool,
    debug: bool,
) -> None:
    """Start the Kedro HTTP server.

    The server exposes pipeline execution via HTTP endpoints, allowing
    external systems to trigger Kedro pipelines programmatically.

    \b
    Endpoints:
      GET  /health  - Health check
      POST /run     - Execute a pipeline

    \b
    Examples:
      kedro server start
      kedro server start --host 0.0.0.0 --port 8080
      kedro server start --reload --debug
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise KedroCliError(
            "Kedro server requires 'uvicorn' and 'fastapi' packages. "
            "Install them with: pip install uvicorn fastapi"
        ) from exc

    # Resolve project path
    if metadata:
        project_path = metadata.project_path
    else:
        project_path = find_kedro_project()
        if not project_path:
            raise KedroCliError(
                "Could not find a Kedro project. "
                "Make sure you're in a Kedro project directory."
            )
        # Bootstrap if we found the project ourselves
        bootstrap_project(project_path)

    # Set environment variables for the server process
    os.environ[KEDRO_PROJECT_PATH_ENV] = str(project_path)

    if debug:
        os.environ["KEDRO_SERVER_DEBUG"] = "1"

    click.echo(f"Starting Kedro server for project at: {project_path}")
    click.echo(f"Server running at: http://{host}:{port}")
    click.echo("Press CTRL+C to stop")
    click.echo()

    # Start uvicorn programmatically
    uvicorn.run(
        "kedro.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
