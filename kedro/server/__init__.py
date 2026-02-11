"""Kedro server module for HTTP and MCP access to pipeline execution."""

from __future__ import annotations

__all__ = ["create_app", "create_mcp_server"]


def create_app():
    """Create the HTTP server application (lazy import)."""
    from kedro.server.app import create_app as _create_app

    return _create_app()


def create_mcp_server(**kwargs):
    """Create the MCP server (lazy import)."""
    from kedro.server.mcp_server import create_mcp_server as _create_mcp_server

    return _create_mcp_server(**kwargs)
