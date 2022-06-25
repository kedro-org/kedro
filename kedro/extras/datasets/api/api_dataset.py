"""``APIDataSet`` loads the data from HTTP(S) APIs.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""
from typing import Any, Dict, Iterable, List

import requests
from requests import Session, sessions

from kedro.io.core import AbstractDataSet, DataSetError


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
        >>>     },
        >>>     credentials=("username", "password")
        >>> )
        >>> data = data_set.load()
    """

    def __init__(
        self,
        url: str,
        method: str = "GET",
        load_args: Dict[str, Any] = None,
        credentials: Iterable[str] = None,
    ) -> None:
        """Creates a new instance of ``APIDataSet`` to fetch data from an API endpoint.

        Args:
            url: The API URL endpoint.
            method: The Method of the request, GET, POST, PUT, DELETE, HEAD, etc...
            load_args: Additional parameters to be fed to requests.request.
                https://docs.python-requests.org/en/latest/api/
            credentials: Allows specifying secrets in credentials.yml.
                Expected format is ``('login', 'password')``.
        Raises:
            ValueError: if both ``auth`` in ``load_args`` and ``credentials`` are specified.
        """
        super().__init__()

        self._load_args = load_args or {}
        self._load_args_auth = self._load_args.pop("auth", None)

        if credentials is not None and self._load_args_auth is not None:
            raise ValueError("Cannot specify both auth and credentials.")

        self._auth = credentials or self._load_args_auth
        self._cert = self._load_args.pop("cert", None)
        self._timeout = self._load_args.pop("timeout", None)

        self._request_args: Dict[str, Any] = {
            "url": url,
            "method": method,
            "auth": self._convert_type(self._auth),
            "cert": self._convert_type(self._cert),
            "timeout": self._convert_type(self._timeout),
            **self._load_args,
        }

    @staticmethod
    def _convert_type(value: Any):
        """
            From the Catalog, iterations are provided as lists.
            However, for some Parameters in the python Requests library,
            only Tuples are allowed.
        """
        if isinstance(value, List):
            return tuple(value)
        return value

    def _describe(self) -> Dict[str, Any]:
        # prevent auth from logging
        request_args_cp = self._request_args.copy()
        request_args_cp.pop("auth", None)
        return request_args_cp

    def _execute_request(self, session: Session) -> requests.Response:
        try:
            response = session.request(**self._request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise DataSetError("Failed to fetch data", exc) from exc
        except OSError as exc:
            raise DataSetError("Failed to connect to the remote server") from exc

        return response

    def _load(self) -> requests.Response:
        with sessions.Session() as session:
            return self._execute_request(session)

    def _save(self, data: Any) -> None:
        raise DataSetError(f"{self.__class__.__name__} is a read only data set type")

    def _exists(self) -> bool:
        with sessions.Session() as session:
            response = self._execute_request(session)
        return response.ok
