"""``PaginatedAPIDataSet`` loads the data from HTTP(S) APIs while traversing pagination.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""
import copy
import logging
from typing import Any, Dict, Iterable, Iterator, List, Union

import jmespath
import requests
from requests.auth import AuthBase

from kedro.extras.datasets.api import APIDataSet
from kedro.io.core import DataSetError

logger = logging.getLogger(__name__)


def log_url(response: requests.Response, *args, **kwargs):
    logger.debug("Response URL: %s", response.url)


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
        self._session.auth = self._request_args["auth"]
        self._session.hooks["response"].append(log_url)

        # update session headers with provided headers
        # requests' default headers:
        # {'User-Agent': 'python-requests/2.27.1', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'Connection': 'keep-alive'}
        if self._request_args["headers"]:
            self._session.headers.update(self._request_args["headers"])

        self._initial_request_args = {
            # used in every request
            "timeout": timeout,
            # used in initial request
            "url": url,
            "method": method,
            "params": params,
            "data": data,
            "json": json,
        }
        self._current_request_args = copy.deepcopy(self._initial_request_args)

    def _get_next_page(self, response: requests.Response) -> Union[str, None]:
        raise NotImplementedError

    def _execute_request(self) -> requests.Response:
        try:
            response = self._session.request(**self._current_request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            raise DataSetError("Failed to fetch data", exc) from exc
        except OSError as exc:
            raise DataSetError("Failed to connect to the remote server") from exc
        finally:
            self._session.close()
        return response

    def _execute_paginated_requests(self) -> Iterator[requests.Response]:  # type: ignore

        # to be able to call .load() multiple times
        # otherwise iterator is exhausted after first call
        self._current_request_args = copy.deepcopy(self._initial_request_args)

        # execute initial request
        response = self._execute_request()
        yield response

        # there might be:
        # a) only a single page -> no next url link found
        # b) a wrong path_to_next_page -> no next url link found
        url = self._get_next_page(response)
        if url is None:
            logger.debug(
                "No next page link found with path_to_next_page %s",
                self.path_to_next_page,
            )

        # remove keys from requests args, that are only needed for initial request
        # TODO: "method"
        # Is it possible to "post" multiple times to follow pagination?
        # Possible 1 POST query request, followed by a series of "GET" requests
        for key in ("url", "params", "data", "json"):
            self._current_request_args.pop(key)

        # handle pagination
        self._current_request_args["url"] = url
        while self._current_request_args["url"]:
            response = self._execute_request()
            yield response
            self._current_request_args["url"] = self._get_next_page(response)
        self._session.close()

    def _load(self) -> Iterator[requests.Response]:  # type: ignore
        return self._execute_paginated_requests()


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
        >>> for response in data_set.load()
        >>>     print(response)

    """

    def _get_next_page(self, response: requests.Response) -> Union[str, None]:
        return jmespath.search(self.path_to_next_page, response.json())
