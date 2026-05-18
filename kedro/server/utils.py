"""Server configuration and settings resolution."""

from __future__ import annotations

import os
from pathlib import Path

# Environment variable name for project path
KEDRO_PROJECT_PATH_ENV = "KEDRO_PROJECT_PATH"
KEDRO_SERVER_ENV = "KEDRO_SERVER_ENV"
KEDRO_SERVER_CONF_SOURCE = "KEDRO_SERVER_CONF_SOURCE"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_HTTP_PORT = 8000


class ServerSettingsError(Exception):
    """Raised when server settings are invalid or missing."""

    pass


def _resolve_project_path(project_path: str | Path | None = None) -> Path:
    """Resolve the Kedro project path from environment variable or function argument.

    The project path is expected to be set in the environment variable `KEDRO_PROJECT_PATH`,
    if not provided programmatically. This function validates that the path exists and is a directory.

    Args:
        project_path: Optional path to the Kedro project. If not provided, it will be resolved from the `KEDRO_PROJECT_PATH` environment variable.

    Returns:
        Path to the Kedro project root.

    Raises:
        ServerSettingsError: If neither ``KEDRO_PROJECT_PATH`` nor ``project_path`` is
            provided, or if the resolved path does not exist.
    """
    raw_path = (
        project_path
        if project_path is not None
        else os.environ.get(KEDRO_PROJECT_PATH_ENV)
    )

    if not raw_path:
        raise ServerSettingsError(
            f"Environment variable '{KEDRO_PROJECT_PATH_ENV}' is not set or passed as an argument. "
            "The Kedro server must be started from within a Kedro project directory."
        )

    path = Path(raw_path).resolve()

    if not path.exists():
        raise ServerSettingsError(
            f"Project path '{path}' does not exist. "
            "Make sure you're running the server from a valid Kedro project."
        )

    return path
