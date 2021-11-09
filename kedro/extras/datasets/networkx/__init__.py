"""``AbstractDataSet`` implementation to save and load NetworkX graphs in JSON
format using ``NetworkX``."""

__all__ = ["NetworkXDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .networkx_dataset import NetworkXDataSet
