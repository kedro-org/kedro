"""``kedro.server`` provides an optional HTTP server for triggering Kedro pipelines.

Requires the `server` extra: ``pip install "kedro[server]"``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

__all__ = ["create_http_server"]


def create_http_server(
    project_path: str | Path | None = None,
    env: str | None = None,
    conf_source: str | None = None,
) -> Any:
    """Create the HTTP server application (lazy import)."""
    try:
        from kedro.server.http_server import create_http_server as _create
    except ModuleNotFoundError as exc:  # pragma: no cover
        if exc.name == "fastapi":
            raise ModuleNotFoundError(
                "The Kedro HTTP server requires optional dependencies. "
                "Install them with `pip install 'kedro[server]'`."
            ) from exc
        raise

    return _create(project_path=project_path, env=env, conf_source=conf_source)
