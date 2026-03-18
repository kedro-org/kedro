"""This module implements the abstract session class."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AbstractSession(ABC):
    """``AbstractSession`` is the base class for all Kedro session implementations.

    Subclasses must implement the ``create``, ``close``, and ``run`` methods.
    """

    @classmethod
    @abstractmethod
    def create(
        cls,
    ) -> AbstractSession:
        """Create a new instance of the session."""
        ...

    @abstractmethod
    def close(self) -> None:
        """Close the current session."""
        ...

    @abstractmethod
    def run(self) -> dict[str, Any]:
        """Run the pipeline."""
        ...

    def __enter__(self) -> AbstractSession:
        return self

    def __exit__(self, _exc_type: Any, _exc_value: Any, _tb: Any) -> None:
        self.close()


class KedroSessionError(Exception):
    """``KedroSessionError`` raised by ``KedroSession``
    in the case that multiple runs are attempted in one session.
    """

    pass
