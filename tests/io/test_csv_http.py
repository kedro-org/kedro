# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
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

# pylint: disable=no-member,unused-argument
import socket

import pytest
import requests

from kedro.io import CSVHTTPDataSet, DataSetError
from kedro.io.core import DataSetNotFoundError

TEST_FILE_URL = "http://example.com/test.csv"
TEST_SAMPLE_CSV_DATA = """
"Index", "Mass (kg)", "Spring 1 (m)", "Spring 2 (m)"
 1, 0.00, 0.050, 0.050
 2, 0.49, 0.066, 0.066
 3, 0.98, 0.087, 0.080
 4, 1.47, 0.116, 0.108
 5, 1.96, 0.142, 0.138
 6, 2.45, 0.166, 0.158
 7, 2.94, 0.193, 0.174
 8, 3.43, 0.204, 0.192
 9, 3.92, 0.226, 0.205
10, 4.41, 0.238, 0.232"""


@pytest.fixture
def sample_remote_csv_file(requests_mock):
    return requests_mock.get(
        TEST_FILE_URL, content=TEST_SAMPLE_CSV_DATA.encode("utf-8")
    )


@pytest.fixture
def csv_data_set():
    return CSVHTTPDataSet(fileurl=TEST_FILE_URL)


class TestCSVHTTPDataSet:
    def test_successfully_load(self, csv_data_set, sample_remote_csv_file):
        """
        Test that given the right URL returning good CSV content,
        we parse it successfully.
        """
        df = csv_data_set.load()

        # Just check we'ce successfully loaded the data.
        assert len(df) == 10

    def test_resource_not_found(self, csv_data_set, requests_mock):
        """
        The server responds with 404,
        we should raise a specific exception in this case.
        """
        requests_mock.get(
            TEST_FILE_URL,
            content=b"Nope, not found",
            status_code=requests.codes.NOT_FOUND,
        )
        with pytest.raises(DataSetNotFoundError, match="The server returned 404 for"):
            csv_data_set.load()

    def test_http_error(self, csv_data_set, requests_mock):
        """
        In case of an unexpected HTTP error, we re-raise DataSetError.
        """
        requests_mock.get(
            TEST_FILE_URL,
            content=b"You shall not pass",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            csv_data_set.load()

    def test_socket_error(self, csv_data_set, requests_mock):
        """
        If failed to connect completely and a socket error is raised,
        re-raise DataSetError.
        """
        requests_mock.get(TEST_FILE_URL, exc=socket.error)
        with pytest.raises(DataSetError, match="Failed to connect"):
            csv_data_set.load()

    def test_read_only_mode(self, csv_data_set):
        """
        Saving is disabled on the data set.
        """
        with pytest.raises(DataSetError, match="is a read only data set type"):
            csv_data_set.save({})

    def test_exists_not_found(self, csv_data_set, requests_mock):
        """
        The remote server returns 404, we should report that it doesn't exist.
        """
        requests_mock.get(
            TEST_FILE_URL,
            content=b"Nope, not found",
            status_code=requests.codes.NOT_FOUND,
        )
        assert not csv_data_set.exists()

    def test_exists_http_error(self, csv_data_set, requests_mock):
        """
        In case of an unexpected HTTP error,
        ``exists()`` should not silently catch it.
        """
        requests_mock.get(
            TEST_FILE_URL,
            content=b"You shall not pass",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            csv_data_set.exists()

    def test_exists_ok(self, csv_data_set, sample_remote_csv_file):
        """
        If the file actually exists and server responds 200,
        ``exists()`` should return True
        """
        assert csv_data_set.exists()
