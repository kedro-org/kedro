"""``AbstractDataSet`` implementation to save matplotlib objects as image files."""

__all__ = ["MatplotlibWriter"]

from contextlib import suppress

with suppress(ImportError):
    from .matplotlib_writer import MatplotlibWriter
