"""``APIDataSet`` loads the data from HTTP(S) APIs.
It uses the python requests library: https://requests.readthedocs.io/en/latest/
"""
from typing import Any, Dict, List, NoReturn, Tuple, Union

import requests
from requests import Session, sessions
from requests.auth import AuthBase

from kedro.io.core import AbstractDataSet, DataSetError

# NOTE: kedro.extras.datasets will be removed in Kedro 0.19.0.
# Any contribution to datasets should be made in kedro-datasets
# in kedro-plugins (https://github.com/kedro-org/kedro-plugins)


class APIDataSet(AbstractDataSet[None, requests.Response]):
    """``APIDataSet`` loads the data from HTTP(S) APIs.
    It uses the python requests library: https://requests.readthedocs.io/en/latest/

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog.html#use-the-data-catalog-with-the-yaml-api>`_:

    .. code-block:: yaml

        usda:
          type: api.APIDataSet
          url: https://quickstats.nass.usda.gov
          params:
            key: SOME_TOKEN,
            format: JSON,
            commodity_desc: CORN,
            statisticcat_des: YIELD,
            agg_level_desc: STATE,
            year: 2000

    Example usage for the
    `Python API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog.html#use-the-data-catalog-with-the-code-api>`_:
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
        credentials: Union[Tuple[str, str], List[str], AuthBase] = None,
    ) -> None:
        """Creates a new instance of ``APIDataSet`` to fetch data from an API endpoint.

        Args:
            url: The API URL endpoint.
            method: The Method of the request, GET, POST, PUT, DELETE, HEAD, etc...
            load_args: Additional parameters to be fed to requests.request.
                https://requests.readthedocs.io/en/latest/api/#requests.request
            credentials: Allows specifying secrets in credentials.yml.
                Expected format is ``('login', 'password')`` if given as a tuple or list.
                An ``AuthBase`` instance can be provided for more complex cases.
        Raises:
            ValueError: if both ``auth`` in ``load_args`` and ``credentials`` are specified.
        """
        super().__init__()

        self._load_args = load_args or {}
        self._load_args_auth = self._load_args.pop("auth", None)

        if credentials is not None and self._load_args_auth is not None:
            raise ValueError("Cannot specify both auth and credentials.")

        self._auth = credentials or self._load_args_auth

        if "cert" in self._load_args:
            self._load_args["cert"] = self._convert_type(self._load_args["cert"])

        if "timeout" in self._load_args:
            self._load_args["timeout"] = self._convert_type(self._load_args["timeout"])

        self._request_args: Dict[str, Any] = {
            "url": url,
            "method": method,
            "auth": self._convert_type(self._auth),
            **self._load_args,
        }

    @staticmethod
    def _convert_type(value: Any):
        """
        From the Data Catalog, iterables are provided as Lists.
        However, for some parameters in the Python requests library,
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

    def _save(self, data: None) -> NoReturn:
        raise DataSetError(f"{self.__class__.__name__} is a read only data set type")

    def _exists(self) -> bool:
        with sessions.Session() as session:
            response = self._execute_request(session)
        return response.ok
