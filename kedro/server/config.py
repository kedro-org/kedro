"""Server configuration and settings resolution."""

from __future__ import annotations

import os
from pathlib import Path

# Environment variable name for project path
KEDRO_PROJECT_PATH_ENV = "KEDRO_PROJECT_PATH"

# Default server settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000
DEFAULT_MCP_PORT = 8001


class ServerSettingsError(Exception):
    """Raised when server settings are invalid or missing."""

    pass


def get_project_path() -> Path:
    """Resolve the Kedro project path from environment variable.

    The server must be started via `kedro server start` which sets
    KEDRO_PROJECT_PATH. This ensures the server is always associated
    with a valid Kedro project.

    Returns:
        Path to the Kedro project root.

    Raises:
        ServerSettingsError: If KEDRO_PROJECT_PATH is not set.
    """
    project_path = os.environ.get(KEDRO_PROJECT_PATH_ENV)

    if not project_path:
        raise ServerSettingsError(
            f"Environment variable '{KEDRO_PROJECT_PATH_ENV}' is not set. "
            "The Kedro server must be started using 'kedro server start' command "
            "from within a Kedro project directory."
        )

    path = Path(project_path).resolve()

    if not path.exists():
        raise ServerSettingsError(
            f"Project path '{path}' does not exist. "
            "Make sure you're running the server from a valid Kedro project."
        )

    return path


def is_debug_mode() -> bool:
    """Check if server is running in debug mode.

    Debug mode enables additional error information like stack traces.

    Returns:
        True if KEDRO_SERVER_DEBUG is set to a truthy value.
    """
    debug_env = os.environ.get("KEDRO_SERVER_DEBUG", "").lower()
    return debug_env in ("1", "true", "yes")
