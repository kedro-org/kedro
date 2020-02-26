# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""``CSVHTTPDataSet`` loads the data from HTTP(S) and parses as Pandas dataframe.
Does not support versioning or data uploading.
"""
import copy
import socket
from io import BytesIO
from typing import Any, Dict, Optional, Tuple, Union

import pandas as pd
import requests
from requests.auth import AuthBase

from kedro.io.core import (
    AbstractDataSet,
    DataSetError,
    DataSetNotFoundError,
    deprecation_warning,
)


class CSVHTTPDataSet(AbstractDataSet):
    """``CSVHTTPDataSet`` loads the data from HTTP(S) and parses as Pandas dataframe.
    Does not support versioning or data uploading.

    Example:
    ::

        >>> from kedro.io import CSVHTTPDataSet
        >>>
        >>>
        >>> data_set = CSVHTTPDataSet(
        >>>     fileurl="https://people.sc.fsu.edu/~jburkardt/data/csv/cities.csv",
        >>>     auth=None,
        >>>     load_args=None)
        >>> data = data_set.load()
    """

    def __init__(
        self,
        fileurl: str,
        auth: Optional[Union[Tuple[str], AuthBase]] = None,
        load_args: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Creates a new instance of ``CSVHTTPDataSet`` pointing to a concrete
        csv file over HTTP(S).

        Args:
            fileurl: A URL to fetch the CSV file.
            auth: Anything ``requests.get`` accepts. Normally it's either
            ``('login', 'password')``, or ``AuthBase`` instance for more complex cases.
            load_args: Pandas options for loading csv files.
                Here you can find all available arguments:
                https://pandas.pydata.org/pandas-docs/stable/generated/pandas.read_csv.html
                All defaults are preserved.

        """
        deprecation_warning(self.__class__.__name__)
        super().__init__()
        self._fileurl = fileurl
        self._auth_backend = auth
        self._load_args = copy.deepcopy(load_args or {})

    def _describe(self) -> Dict[str, Any]:
        return dict(fileurl=self._fileurl, load_args=self._load_args)

    def _execute_request(self):
        try:
            response = requests.get(self._fileurl, auth=self._auth_backend)
            response.raise_for_status()
        except requests.exceptions.HTTPError as exc:
            if (
                exc.response.status_code
                == requests.codes.NOT_FOUND  # pylint: disable=no-member
            ):
                raise DataSetNotFoundError(
                    "The server returned 404 for {}".format(self._fileurl)
                )
            raise DataSetError("Failed to fetch data")
        except socket.error:
            raise DataSetError("Failed to connect to the remote server")

        return response

    def _load(self) -> pd.DataFrame:
        response = self._execute_request()
        return pd.read_csv(BytesIO(response.content), **self._load_args)

    def _save(self, data: pd.DataFrame) -> None:
        raise DataSetError(
            "{} is a read only data set type".format(self.__class__.__name__)
        )

    def _exists(self) -> bool:
        try:
            response = self._execute_request()
        except DataSetNotFoundError:
            return False

        # NOTE: we don't access the actual content here, which might be large.
        return response.status_code == requests.codes.OK  # pylint: disable=no-member
