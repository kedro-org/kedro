"""CLI commands for Kedro server."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

import click

from kedro.framework.cli.utils import CONTEXT_SETTINGS, KedroCliError
from kedro.framework.startup import bootstrap_project
from kedro.server.config import (
    DEFAULT_HOST,
    DEFAULT_MCP_PORT,
    DEFAULT_PORT,
    KEDRO_PROJECT_PATH_ENV,
)
from kedro.utils import find_kedro_project

if TYPE_CHECKING:
    from pathlib import Path

    from kedro.framework.startup import ProjectMetadata


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
def server_group() -> None:
    """Commands for running Kedro as a server."""


# ──── HTTP sub-group ──────────────────────────────────────────────────────────


@server_group.group(name="http")
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
            "Install them with: pip install kedro[server]"
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
        "kedro.server.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


# ──── MCP sub-group ───────────────────────────────────────────────────────────


@server_group.group(name="mcp")
def mcp_group() -> None:
    """MCP (Model Context Protocol) server commands."""


@mcp_group.command(name="start", context_settings=CONTEXT_SETTINGS)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "sse", "streamable-http"]),
    default="stdio",
    help="MCP transport type. Default: stdio",
)
@click.option(
    "--host",
    "-h",
    type=str,
    default=DEFAULT_HOST,
    help=f"Host for SSE/HTTP transport. Default: {DEFAULT_HOST}",
)
@click.option(
    "--port",
    "-p",
    type=int,
    default=DEFAULT_MCP_PORT,
    help=f"Port for SSE/HTTP transport. Default: {DEFAULT_MCP_PORT}",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="Enable debug mode. Includes stack traces in error responses.",
)
@click.pass_obj
def mcp_start(
    metadata: ProjectMetadata | None,
    transport: str,
    host: str,
    port: int,
    debug: bool,
) -> None:
    """Start the Kedro MCP server.

    The MCP server exposes Kedro pipelines as tools that AI agents can
    discover and invoke via the Model Context Protocol.

    \b
    Tools:
      list_pipelines    - List registered pipelines
      get_pipeline_info - Get pipeline node details
      run_pipeline      - Execute a pipeline
      list_datasets     - List catalog datasets

    \b
    Examples:
      kedro server mcp start
      kedro server mcp start --transport sse --port 8001
      kedro server mcp start --transport streamable-http --port 8001
    """
    try:
        from mcp.server.fastmcp import FastMCP  # noqa: F401
    except ImportError as exc:
        raise KedroCliError(
            "Kedro MCP server requires the 'mcp' package. "
            "Install it with: pip install kedro[mcp]"
        ) from exc

    project_path = _resolve_project_path(metadata)

    # Set environment variables for the server process
    os.environ[KEDRO_PROJECT_PATH_ENV] = str(project_path)

    if debug:
        os.environ["KEDRO_SERVER_DEBUG"] = "1"

    from kedro.server.mcp_server import create_mcp_server

    # Host/port are baked into the FastMCP constructor;
    # run() only takes transport (and optionally mount_path).
    server = create_mcp_server(host=host, port=port)

    if transport == "stdio":
        # For stdio, output goes to stderr to avoid interfering with the protocol
        click.echo(
            f"Starting Kedro MCP server (stdio) for project at: {project_path}",
            err=True,
        )
        server.run(transport="stdio")
    elif transport == "sse":
        click.echo(f"Starting Kedro MCP server (SSE) for project at: {project_path}")
        click.echo(f"Server running at: http://{host}:{port}/sse")
        click.echo("Press CTRL+C to stop")
        server.run(transport="sse")
    else:
        click.echo(
            f"Starting Kedro MCP server (streamable-http) "
            f"for project at: {project_path}"
        )
        click.echo(f"Server running at: http://{host}:{port}/mcp")
        click.echo("Press CTRL+C to stop")
        server.run(transport="streamable-http")
