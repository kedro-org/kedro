# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""``APIDataSet`` loads the data from HTTP(S) APIs.
It uses the python requests library: https://requests.readthedocs.io/en/master/
"""
import socket
from typing import Any, Dict, List, Tuple, Union

import requests
from requests.auth import AuthBase

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
        >>>     url="https://quickstats.nass.usda.gov"
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

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        url: str,
        method: str = "GET",
        data: Any = None,
        params: Dict[str, Any] = None,
        headers: Dict[str, Any] = None,
        auth: Union[Tuple[str], AuthBase] = None,
        json: Union[List, Dict[str, Any]] = None,
        timeout: int = 60,
    ) -> None:
        """Creates a new instance of ``APIDataSet`` to fetch data from an API endpoint.

        Args:
            url: The API URL endpoint.
            method: The Method of the request, GET, POST, PUT, DELETE, HEAD, etc...
            data: The request payload, used for POST, PUT, etc requests
                https://requests.readthedocs.io/en/master/user/quickstart/#more-complicated-post-requests
            params: The url parameters of the API.
                https://requests.readthedocs.io/en/master/user/quickstart/#passing-parameters-in-urls
            headers: The HTTP headers.
                https://requests.readthedocs.io/en/master/user/quickstart/#custom-headers
            auth: Anything ``requests`` accepts. Normally it's either ``('login', 'password')``,
                or ``AuthBase``, ``HTTPBasicAuth`` instance for more complex cases.
            json: The request payload, used for POST, PUT, etc requests, passed in
                to the json kwarg in the requests object.
                https://requests.readthedocs.io/en/master/user/quickstart/#more-complicated-post-requests
            timeout: The wait time in seconds for a response, defaults to 1 minute.
                https://requests.readthedocs.io/en/master/user/quickstart/#timeouts

        """
        super().__init__()
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
        return dict(**self._request_args)

    def _execute_request(self) -> requests.Response:
        try:
            response = requests.request(**self._request_args)
            response.raise_for_status()
        except requests.exceptions.HTTPError as err:
            raise DataSetError("Failed to fetch data", err) from err
        except socket.error as err:
            raise DataSetError("Failed to connect to the remote server") from err

        return response

    def _load(self) -> requests.Response:
        return self._execute_request()

    def _save(self, data: Any) -> None:
        raise DataSetError(
            "{} is a read only data set type".format(self.__class__.__name__)
        )

    def _exists(self) -> bool:
        response = self._execute_request()

        return response.ok
