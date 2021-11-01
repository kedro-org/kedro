"""``AbstractDataSet`` implementation to load/save image data."""

__all__ = ["ImageDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .image_dataset import ImageDataSet
