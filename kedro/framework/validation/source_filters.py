"""Source filters for generic type extraction from different source types."""

from __future__ import annotations

from abc import ABC, abstractmethod


class SourceFilter(ABC):
    """Abstract base class for source-specific filtering and key extraction."""

    @abstractmethod
    def should_process(self, source_name: str) -> bool:
        """Determine if this filter should process the given source name.

        Args:
            source_name: The source identifier to check

        Returns:
            True if this filter should process the source, False otherwise
        """
        pass

    @abstractmethod
    def extract_key(self, source_name: str) -> str:
        """Extract the key from the source name.

        Args:
            source_name: The source identifier to extract key from

        Returns:
            The extracted key
        """
        pass

    @abstractmethod
    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate appropriate log message for this source type.

        Args:
            key: The extracted key
            type_name: The type name found

        Returns:
            Log message string
        """
        pass


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


class DatasetSourceFilter(SourceFilter):
    """Filter for dataset sources (future implementation)."""

    def should_process(self, source_name: str) -> bool:
        """Check if source is a dataset source."""
        # Future: check for dataset patterns like "dataset:" prefix
        return isinstance(source_name, str) and not source_name.startswith("params:")

    def extract_key(self, source_name: str) -> str:
        """Extract dataset key from dataset:key format."""
        # Future: extract dataset key
        return source_name

    def get_log_message(self, key: str, type_name: str) -> str:
        """Generate dataset-specific log message."""
        return f"Found dataset requirement: {key} -> {type_name}"
