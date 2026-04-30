"""``kedro.server`` provides an optional HTTP server for triggering Kedro pipelines.

Requires the `server` extra: ``pip install "kedro[server]"``.
"""

from __future__ import annotations

from typing import Any

__all__ = ["create_http_server"]


def create_http_server(**kwargs: Any) -> Any:
    """Create the HTTP server application (lazy import)."""
    try:
        from kedro.server.http_server import create_http_server as _create
    except ModuleNotFoundError as exc:
        if exc.name == "fastapi":  # pragma: no cover
            raise ModuleNotFoundError(
                "The Kedro HTTP server requires optional dependencies. "
                "Install them with `pip install 'kedro[server]'`."
            ) from exc
        raise

    return _create(**kwargs)
