"""Source filters for generic type extraction from different source types."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceFilter(ABC):
    """Abstract base class for source-specific filtering and key extraction.

    Provides an extensible design for filtering and extracting type information
    from different source types (e.g. parameters, datasets).
    """

    @abstractmethod
    def should_process(self, source_name: str) -> bool:
        """Determine if this filter should process the given source name.

        Args:
            source_name: The source identifier to check.

        Returns:
            True if this filter should process the source, False otherwise.
        """

    @abstractmethod
    def extract_key(self, source_name: str) -> str:
        """Extract the key from the source name.

        Args:
            source_name: The source identifier to extract key from.

        Returns:
            The extracted key.
        """

    @abstractmethod
    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate appropriate log message for this source type.

        Args:
            key: The extracted key.
            type_name: The type name found.

        Returns:
            Log message string.
        """


class ParameterSourceFilter(SourceFilter):
    """Filter for parameter sources (params:*)."""

    def should_process(self, source_name: str) -> bool:
        """Check if source is a parameter source."""
        return isinstance(source_name, str) and source_name.startswith("params:")

    def extract_key(self, source_name: str) -> str:
        """Extract parameter key from params:key format."""
        return source_name.split(":", 1)[1]

    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate parameter-specific log message."""
        return f"Found parameter requirement: {key} -> {type_name}"
