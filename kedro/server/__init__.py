from __future__ import annotations

__all__ = ["create_http_server"]


def create_http_server():
    """Create the HTTP server application (lazy import)."""
    from kedro.server.http_server import create_http_server as _create

    return _create()
