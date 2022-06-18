# pylint: disable=no-member
import json
import logging
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
TEST_METHOD = "GET"
TEST_HEADERS = {"key": "value"}


class TestAPIDataSet:

    @pytest.mark.parametrize("method", POSSIBLE_METHODS)
    def test_successfully_load_with_response(self, requests_mocker, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS}
        )
        requests_mocker.register_uri(
            method,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA

    def test_successful_json_load_with_response(self, requests_mocker):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"json": TEST_JSON_RESPONSE_DATA, "headers": TEST_HEADERS}
        )
        requests_mocker.register_uri(
            TEST_METHOD,
            TEST_URL,
            headers=TEST_HEADERS,
            text=json.dumps(TEST_JSON_RESPONSE_DATA),
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.json() == TEST_JSON_RESPONSE_DATA

    def test_http_error(self, requests_mocker):
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS}
        )
        requests_mocker.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )

        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.load()

    def test_socket_error(self, requests_mocker):
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS}
        )
        requests_mocker.register_uri(TEST_METHOD, TEST_URL_WITH_PARAMS, exc=socket.error)

        with pytest.raises(DataSetError, match="Failed to connect"):
            api_data_set.load()

    def test_read_only_mode(self):
        """
        Saving is disabled on the data set.
        """
        api_data_set = APIDataSet(url=TEST_URL, method=TEST_METHOD)
        with pytest.raises(DataSetError, match="is a read only data set type"):
            api_data_set.save({})

    def test_exists_http_error(self, requests_mocker):
        """
        In case of an unexpected HTTP error,
        ``exists()`` should not silently catch it.
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS }
        )
        requests_mocker.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.exists()

    def test_exists_ok(self, requests_mocker):
        """
        If the file actually exists and server responds 200,
        ``exists()`` should return True
        """
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS}
        )
        requests_mocker.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        assert api_data_set.exists()
