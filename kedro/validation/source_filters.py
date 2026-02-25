"""Source filters for type extraction from different source types."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceFilter(ABC):
    """Abstract base class for source-specific filtering and key extraction."""

    @abstractmethod
    def should_process(self, source_name: str) -> bool:
        """Determine if this filter should process the given source name."""

    @abstractmethod
    def extract_key(self, source_name: str) -> str:
        """Extract the key from the source name."""

    @abstractmethod
    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate appropriate log message for this source type."""


class ParameterSourceFilter(SourceFilter):
    """Filter for parameter sources (``params:*``)."""

    def should_process(self, source_name: str) -> bool:
        """Check if source is a parameter source."""
        return isinstance(source_name, str) and source_name.startswith("params:")

    def extract_key(self, source_name: str) -> str:
        """Extract parameter key from ``params:key`` format."""
        return source_name.split(":", 1)[1]

    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate parameter-specific log message."""
        return f"Found parameter requirement: {key} -> {type_name}"
