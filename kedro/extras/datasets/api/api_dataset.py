"""``APIDataSet`` loads the data from HTTP(S) APIs.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""
from copy import deepcopy
from typing import Any, Dict

import requests

from kedro.extras.datasets.api.BaseAuthFactory import BaseAuthFactory
from kedro.io.core import AbstractDataSet, DataSetError

_DEFAULT_CREDENTIALS = {}


class APIDataSet(AbstractDataSet):
    """``APIDataSet`` loads the data from HTTP(S) APIs.
    It uses the python requests library: https://requests.readthedocs.io/en/master/

    Example:
    ::

        >>> from kedro.extras.datasets.api import APIDataSet
        >>>
        >>>
        >>> data_set = APIDataSet(
        >>>     url="https://quickstats.nass.usda.gov",
        >>>     load_args={
        >>>         "params": {
        >>>             "key": "SOME_TOKEN",
        >>>             "format": "JSON",
        >>>             "commodity_desc": "CORN",
        >>>             "statisticcat_des": "YIELD",
        >>>             "agg_level_desc": "STATE",
        >>>             "year": 2000
        >>>         }
        >>>     }
        >>> )
        >>> data = data_set.load()
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        load_args: Dict[str, Any] = None,
        auth: Dict[str, Any] = None,
        credentials: Dict[str, Any] = None
    ) -> None:
        """Creates a new instance of ``APIDataSet`` to fetch data from an API endpoint.

        Args:
            url: The API URL endpoint.
            method: The Method of the request, GET, POST, PUT, DELETE, HEAD, etc...
            load_args: Additional parameters to be fed to requests.request.
                https://docs.python-requests.org/en/latest/api/
            auth: provide arguments to construct a Requests `BaseAuth` object.
            credentials: Allows specifying secrets in credentials.yml.
        """
        super().__init__()

        self._credentials = deepcopy(_DEFAULT_CREDENTIALS)
        if credentials is not None:
            self._credentials.update(credentials)

        self._auth = None

        if auth is not None:
            if 'type' not in auth:
                raise DataSetError("'type' is missing from Authenticator configuration")
            auth_type = auth.pop('type')
            self._auth = BaseAuthFactory.create(auth_type, **auth, **credentials)

        self._request_args: Dict[str, Any] = {
            "url": url,
            "method": method,
            "auth": self._auth,
            **load_args
        }

    def _describe(self) -> Dict[str, Any]:
        return dict(**self._request_args)

    def _execute_request(self) -> requests.Response:
        try:
            response = requests.request(**self._request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise DataSetError("Failed to fetch data", exc) from exc
        except OSError as exc:
            raise DataSetError("Failed to connect to the remote server") from exc

        return response

    def _load(self) -> requests.Response:
        return self._execute_request()

    def _save(self, data: Any) -> None:
        raise DataSetError(f"{self.__class__.__name__} is a read only data set type")

    def _exists(self) -> bool:
        response = self._execute_request()
        return response.ok
