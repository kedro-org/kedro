"""Kedro server module for HTTP API access to pipeline execution."""

from __future__ import annotations

__all__ = ["create_app"]


def create_app():
    """Lazy import to avoid loading FastAPI when not needed."""
    from kedro.server.app import create_app as _create_app

    return _create_app()
