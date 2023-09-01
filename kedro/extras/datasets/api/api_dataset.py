"""``APIDataSet`` loads the data from HTTP(S) APIs.
It uses the python requests library: https://requests.readthedocs.io/en/latest/
"""
from typing import Any, Dict, Iterable, List, NoReturn, Union

import requests
from requests.auth import AuthBase

from kedro.io.core import AbstractDataset, DatasetError

# NOTE: kedro.extras.datasets will be removed in Kedro 0.19.0.
# Any contribution to datasets should be made in kedro-datasets
# in kedro-plugins (https://github.com/kedro-org/kedro-plugins)


class APIDataSet(AbstractDataset[None, requests.Response]):
    """``APIDataSet`` loads the data from HTTP(S) APIs.
    It uses the python requests library: https://requests.readthedocs.io/en/latest/

    Example usage for the
    `YAML API <https://kedro.readthedocs.io/en/stable/data/\
    data_catalog_yaml_examples.html>`_:


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
    advanced_data_catalog_usage.html>`_:
    ::

        >>> from kedro.extras.datasets.api import APIDataSet
        >>>
        >>>
        >>> data_set = APIDataSet(
        >>>     url="https://quickstats.nass.usda.gov",
        >>>     params={
        >>>         "key": "SOME_TOKEN",
        >>>         "format": "JSON",
        >>>         "commodity_desc": "CORN",
        >>>         "statisticcat_des": "YIELD",
        >>>         "agg_level_desc": "STATE",
        >>>         "year": 2000
        >>>     }
        >>> )
        >>> data = data_set.load()
    """

    def __init__(  # noqa: too-many-arguments
        self,
        url: str,
        method: str = "GET",
        data: Any = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, Any] = None,
        auth: Union[Iterable[str], AuthBase] = None,
        json: Union[List, Dict[str, Any]] = None,
        timeout: int = 60,
        credentials: Union[Iterable[str], AuthBase] = None,
    ) -> None:
        """Creates a new instance of ``APIDataSet`` to fetch data from an API endpoint.

        Args:
            url: The API URL endpoint.
            method: The Method of the request, GET, POST, PUT, DELETE, HEAD, etc...
            data: The request payload, used for POST, PUT, etc requests
                https://requests.readthedocs.io/en/latest/user/quickstart/#more-complicated-post-requests
            params: The url parameters of the API.
                https://requests.readthedocs.io/en/latest/user/quickstart/#passing-parameters-in-urls
            headers: The HTTP headers.
                https://requests.readthedocs.io/en/latest/user/quickstart/#custom-headers
            auth: Anything ``requests`` accepts. Normally it's either ``('login', 'password')``,
                or ``AuthBase``, ``HTTPBasicAuth`` instance for more complex cases. Any
                iterable will be cast to a tuple.
            json: The request payload, used for POST, PUT, etc requests, passed in
                to the json kwarg in the requests object.
                https://requests.readthedocs.io/en/latest/user/quickstart/#more-complicated-post-requests
            timeout: The wait time in seconds for a response, defaults to 1 minute.
                https://requests.readthedocs.io/en/latest/user/quickstart/#timeouts
            credentials: same as ``auth``. Allows specifying ``auth`` secrets in
                credentials.yml.

        Raises:
            ValueError: if both ``credentials`` and ``auth`` are specified.
        """
        super().__init__()

        if credentials is not None and auth is not None:
            raise ValueError("Cannot specify both auth and credentials.")

        auth = credentials or auth

        if isinstance(auth, Iterable):
            auth = tuple(auth)

        self._request_args: Dict[str, Any] = {
            "url": url,
            "method": method,
            "data": data,
            "params": params,
            "headers": headers,
            "auth": auth,
            "json": json,
            "timeout": timeout,
        }

    def _describe(self) -> Dict[str, Any]:
        return {**self._request_args}

    def _execute_request(self) -> requests.Response:
        try:
            response = requests.request(**self._request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise DatasetError("Failed to fetch data", exc) from exc
        except OSError as exc:
            raise DatasetError("Failed to connect to the remote server") from exc

        return response

    def _load(self) -> requests.Response:
        return self._execute_request()

    def _save(self, data: None) -> NoReturn:
        raise DatasetError(f"{self.__class__.__name__} is a read only data set type")

    def _exists(self) -> bool:
        response = self._execute_request()

        return response.ok
