"""Kedro server module for HTTP and MCP access to pipeline execution."""

from __future__ import annotations

__all__ = ["create_http_server", "create_mcp_server"]


def create_http_server():
    """Create the HTTP server application (lazy import)."""
    from kedro.server.http_server import create_http_server as _create

    return _create()


def create_mcp_server(**kwargs):
    """Create the MCP server (lazy import)."""
    from kedro.server.mcp_server import create_mcp_server as _create

    return _create(**kwargs)
