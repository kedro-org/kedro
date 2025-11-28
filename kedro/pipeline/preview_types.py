"""This module provides types and classes for node preview functionality."""

from __future__ import annotations

from typing import Any, Literal


class PreviewPayload:
    """Preview payload containing kind, content and optional meta."""

    def __init__(
        self,
        kind: Literal["mermaid", "json", "text", "image", "plotly", "table", "custom"],
        content: str,
        meta: dict[str, Any] | None = None,
    ):
        self.kind = kind
        self.content = content
        self.meta = meta
