import os

import click

from kedro.framework.cli.utils import CONTEXT_SETTINGS, KedroCliError
from kedro.framework.startup import bootstrap_project, ProjectMetadata
from kedro.server.utils import (
    DEFAULT_HOST,
    DEFAULT_HTTP_PORT,
    KEDRO_PROJECT_PATH_ENV,
)
from kedro.utils import find_kedro_project
from pathlib import Path

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


# ──── HTTP sub-group ──────────────────────────────────────────────────────────


@server_cli.group(name="http")
def http_group() -> None:
    """HTTP server commands."""


@http_group.command(name="start", context_settings=CONTEXT_SETTINGS)
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
@click.pass_obj
def http_start(
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
      kedro server http start
      kedro server http start --host 0.0.0.0 --port 8080
      kedro server http start --reload --debug
    """
    try:
        import uvicorn
    except ImportError as exc:
        raise KedroCliError(
            "Kedro HTTP server requires 'uvicorn' and 'fastapi' packages. "
            "Install them with: pip install kedro[http]"
        ) from exc

    project_path = _resolve_project_path(metadata)

    # Set environment variables for the server process
    os.environ[KEDRO_PROJECT_PATH_ENV] = str(project_path)

    if debug:
        os.environ["KEDRO_SERVER_DEBUG"] = "1"

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
