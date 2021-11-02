"""``AbstractDataSet`` implementations to load/save a plotly figure from/to a JSON
file."""

__all__ = ["PlotlyDataSet", "JSONDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .plotly_dataset import PlotlyDataSet
with suppress(ImportError):
    from .json_dataset import JSONDataSet
