# pylint: disable=no-member
import json
import socket

import pytest
import requests
import requests_mock

from kedro.extras.datasets.api import APIDataSet
from kedro.io.core import DataSetError

POSSIBLE_METHODS = ["GET", "OPTIONS", "HEAD", "POST", "PUT", "PATCH", "DELETE"]

TEST_URL = "http://example.com/api/test"
TEST_TEXT_RESPONSE_DATA = "This is a response."
TEST_JSON_RESPONSE_DATA = [{"key": "value"}]

TEST_PARAMS = {"param": "value"}
TEST_URL_WITH_PARAMS = TEST_URL + "?param=value"

TEST_HEADERS = {"key": "value"}


@pytest.mark.parametrize("method", POSSIBLE_METHODS)
class TestAPIDataSet:
    @pytest.fixture
    def requests_mocker(self):
        with requests_mock.Mocker() as mock:
            yield mock

    def test_successfully_load_with_response(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA

    def test_successful_json_load_with_response(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=method,
            json=TEST_JSON_RESPONSE_DATA,
            headers=TEST_HEADERS,
        )
        requests_mocker.register_uri(
            method,
            TEST_URL,
            headers=TEST_HEADERS,
            text=json.dumps(TEST_JSON_RESPONSE_DATA),
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.json() == TEST_JSON_RESPONSE_DATA

    def test_http_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )

        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.load()

    def test_socket_error(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(method, TEST_URL_WITH_PARAMS, exc=socket.error)

        with pytest.raises(DataSetError, match="Failed to connect"):
            api_data_set.load()

    def test_read_only_mode(self, method):
        """
        Saving is disabled on the data set.
        """
        api_data_set = APIDataSet(url=TEST_URL, method=method)
        with pytest.raises(DataSetError, match="is a read only data set type"):
            api_data_set.save({})

    def test_exists_http_error(self, requests_mocker, method):
        """
        In case of an unexpected HTTP error,
        ``exists()`` should not silently catch it.
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.exists()

    def test_exists_ok(self, requests_mocker, method):
        """
        If the file actually exists and server responds 200,
        ``exists()`` should return True
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, params=TEST_PARAMS, headers=TEST_HEADERS
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        assert api_data_set.exists()
