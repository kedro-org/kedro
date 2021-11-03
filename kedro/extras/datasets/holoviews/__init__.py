"""``AbstractDataSet`` implementation to save Holoviews objects as image files."""

__all__ = ["HoloviewsWriter"]

from contextlib import suppress

with suppress(ImportError):
    from .holoviews_writer import HoloviewsWriter
