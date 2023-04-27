"""``APIDataset`` loads the data from HTTP(S) APIs
and returns them into either as string or json Dict.
It uses the python requests library: https://requests.readthedocs.io/en/latest/
"""

__all__ = ["APIDataSet", "APIDataset"]

from contextlib import suppress

with suppress(ImportError):
    from .api_dataset import APIDataSet, APIDataset
