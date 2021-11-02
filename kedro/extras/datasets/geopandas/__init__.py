"""``GeoJSONLocalDataset`` is an ``AbstractVersionedDataSet`` to save and load GeoJSON files.
"""
__all__ = ["GeoJSONDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .geojson_dataset import GeoJSONDataSet
