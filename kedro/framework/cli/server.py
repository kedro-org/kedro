import os
from pathlib import Path

import click

from kedro.framework.cli.utils import CONTEXT_SETTINGS, KedroCliError, validate_conf_source
from kedro.framework.startup import ProjectMetadata, bootstrap_project
from kedro.server.utils import (
    DEFAULT_HOST,
    DEFAULT_HTTP_PORT,
    KEDRO_PROJECT_PATH_ENV,
)
from kedro.utils import find_kedro_project


def _resolve_project_path(metadata: ProjectMetadata | None) -> Path:
    """Resolve and validate the Kedro project path.

    If metadata is provided (normal CLI flow), uses its project_path.
    Otherwise, discovers the project path from the current directory.

    Args:
        metadata: Project metadata from Kedro CLI, or None.

    Returns:
        Resolved path to the Kedro project.

    Raises:
        KedroCliError: If no Kedro project can be found.
    """
    if metadata:
        return metadata.project_path

    project_path = find_kedro_project()
    if not project_path:
        raise KedroCliError(
            "Could not find a Kedro project. "
            "Make sure you're in a Kedro project directory."
        )
    bootstrap_project(project_path)
    return project_path


@click.group(name="server")
def server_cli() -> None:
    """Commands for running Kedro as a server."""


@server_cli.command(name="start", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--host",
    "-H",
    type=str,
    default=DEFAULT_HOST,
    help=f"Host to bind the server to. Default: {DEFAULT_HOST}",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=DEFAULT_HTTP_PORT,
    help=f"Port to bind the server to. Default: {DEFAULT_HTTP_PORT}",
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
@click.option(
    "--env",
    "-e",
    type=str,
    default=None,
    help="Kedro configuration environment for server sessions.",
)
@click.option(
    "--conf-source",
    callback=validate_conf_source,
    help="Path of a directory where project configuration is stored.",
)
@click.pass_obj
def http_start(
    metadata: ProjectMetadata | None,
    host: str,
    port: int,
    reload: bool,
    debug: bool,
    env: str | None,
    conf_source: str | None,
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
            "Kedro HTTP server requires 'uvicorn' and 'fastapi' packages. "
            "Install them with: pip install kedro[server]"
        ) from exc

    project_path = _resolve_project_path(metadata)

    # Set environment variables for the server process
    os.environ[KEDRO_PROJECT_PATH_ENV] = str(project_path)

    if debug:
        os.environ["KEDRO_SERVER_DEBUG"] = "1"

    if env:
        os.environ["KEDRO_SERVER_ENV"] = env

    if conf_source:
        os.environ["KEDRO_SERVER_CONF_SOURCE"] = conf_source

    click.echo(f"Starting Kedro HTTP server for project at: {project_path}")
    click.echo(f"Server running at: http://{host}:{port}")
    click.echo("Press CTRL+C to stop")
    click.echo()

    # Start uvicorn programmatically
    uvicorn.run(
        "kedro.server.http_server:create_http_server",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )
