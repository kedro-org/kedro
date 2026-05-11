import os
import warnings

import click

from kedro.framework.cli.utils import (
    CONTEXT_SETTINGS,
    KedroCliError,
    validate_conf_source,
)
from kedro.framework.startup import ProjectMetadata
from kedro.server.utils import (
    DEFAULT_HOST,
    DEFAULT_HTTP_PORT,
    KEDRO_PROJECT_PATH_ENV,
    KEDRO_SERVER_CONF_SOURCE,
    KEDRO_SERVER_ENV,
)


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
    help="Enable auto-reload for development. Server restarts on code changes. Should not be used in production.",
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
def server_start(  # noqa: PLR0913
    metadata: ProjectMetadata,
    host: str,
    port: int,
    reload: bool,
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
      kedro server start --reload
    """
    try:
        import fastapi  # noqa: F401
        import uvicorn

    except ImportError as exc:
        raise KedroCliError(
            "Kedro HTTP server requires 'fastapi', 'pydantic', and 'uvicorn' packages. "
            "Install them with: uv pip install 'kedro[server]'"
        ) from exc

    project_path = metadata.project_path

    if reload:
        warnings.warn(
            "--reload enables Uvicorn's auto-reload mode which is intended for "
            "development only. Do not use it in production.",
            UserWarning,
            stacklevel=1,
        )

    # Unset env and conf-source to avoid re-using them from previous runs if not provided in the current command
    if KEDRO_SERVER_ENV in os.environ:
        del os.environ[KEDRO_SERVER_ENV]
    if KEDRO_SERVER_CONF_SOURCE in os.environ:
        del os.environ[KEDRO_SERVER_CONF_SOURCE]

    os.environ[KEDRO_PROJECT_PATH_ENV] = str(project_path)
    if env:
        os.environ[KEDRO_SERVER_ENV] = env

    if conf_source:
        os.environ[KEDRO_SERVER_CONF_SOURCE] = conf_source

    uvicorn.run(
        "kedro.server.http_server:create_http_server",
        factory=True,
        host=host,
        port=port,
        reload=reload,
        reload_dirs=[str(project_path)] if reload else None,
        log_level="info",
    )
