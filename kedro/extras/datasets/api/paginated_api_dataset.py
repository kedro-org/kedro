"""``PaginatedAPIDataSet`` loads the data from HTTP(S) APIs while traversing pagination.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""
import copy
from typing import Any, Dict, Iterable, Iterator, List, Union

import jmespath
import requests
from requests.auth import AuthBase

from kedro.extras.datasets.api import APIDataSet
from kedro.io.core import DataSetError


class PaginatedAPIDataSet(APIDataSet):
    """``PaginatedJSONAPIDataSet`` loads the data from HTTP(S) APIs while traversing pagination.
    It uses the python requests library: https://requests.readthedocs.io/en/master/

    Implement logic to find in _get_next_page().

    """

    # pylint: disable=too-many-arguments
    def __init__(
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
        # multiple keys possible to access link to next page in nested json
        # separate keys with ".", like "key1.key2"
        # TODO: set a value or set to None?
        path_to_next_page: str = "next",
    ):
        super().__init__(
            url, method, data, params, headers, auth, json, timeout, credentials
        )
        self.path_to_next_page = path_to_next_page

        # init session
        self._session = requests.Session()
        self._session.auth = self._request_args.pop("auth", None)
        headers = self._request_args.pop("headers", None)
        if headers:
            self._session.headers.update(headers)

    def _get_next_page(self, response: requests.Response) -> Union[str, None]:
        raise NotImplementedError

    def _execute_request(self) -> requests.Response:
        try:
            response = self._session.request(**self._request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise DataSetError("Failed to fetch data", exc) from exc
        except OSError as exc:
            raise DataSetError("Failed to connect to the remote server") from exc
        return response

    def _load(self) -> Iterator[requests.Response]:  # type: ignore
        # TODO: method overrides super class method, returns other type: iterator

        # make a copy of the request arguments from init
        request_args = copy.deepcopy(self._request_args)

        while self._request_args["url"]:
            response = self._execute_request()
            yield response
            self._request_args["url"] = self._get_next_page(response)

            # params are only needed for first request
            self._request_args.pop("params", None)

        # TODO: An exception can be raised earlier, so the connection might not be closed
        self._session.close()
        # restore original state
        self._request_args = request_args


class PaginatedJSONAPIDataSet(PaginatedAPIDataSet):
    """``PaginatedJSONAPIDataSet`` loads the data from HTTP(S) APIs.
    It uses the python requests library: https://requests.readthedocs.io/en/master/

    Example:
    ::

        >>> from kedro.extras.datasets.api import PaginatedAPIDataSet
        >>>
        >>>
        >>> data_set = PaginatedAPIDataSet(
        >>>     url="https://pokeapi.co/api/v2/pokemon",
        >>>     path_to_next_page="next",
        >>>     params={
        >>>         "limit": 500
        >>>     }
        >>> )
        >>> for r in data_set.load()
        >>>     print(r)

    """

    def _get_next_page(self, response: requests.Response) -> Union[str, None]:
        return jmespath.search(self.path_to_next_page, response.json())
