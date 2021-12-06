"""``AbstractDataSet`` implementation to save and load NetworkX graphs in JSON
, GraphML and GML formats using ``NetworkX``."""

__all__ = ["GMLDataSet", "GraphMLDataSet", "JSONDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .gml_dataset import GMLDataSet

with suppress(ImportError):
    from .graphml_dataset import GraphMLDataSet

with suppress(ImportError):
    from .json_dataset import JSONDataSet
