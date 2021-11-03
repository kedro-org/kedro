"""``APIDataSet`` loads the data from HTTP(S) APIs
and returns them into either as string or json Dict.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""

__all__ = ["APIDataSet"]

from contextlib import suppress

with suppress(ImportError):
    from .api_dataset import APIDataSet
