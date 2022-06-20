# pylint: disable=no-member
import base64
import json
import socket

import pytest
import requests

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
    def test_successfully_load_with_response(self, requests_mock, method):
        api_data_set = APIDataSet(
            url=TEST_URL, method=method, load_args={"params": TEST_PARAMS}
        )
        requests_mock.register_uri(
            method, TEST_URL_WITH_PARAMS, text=TEST_TEXT_RESPONSE_DATA
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA

    def test_headers_in_request(self, requests_mock):
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"headers": TEST_HEADERS}
        )
        requests_mock.register_uri(TEST_METHOD, TEST_URL, headers={"pan": "cake"})

        response = api_data_set.load()

        assert response.request.headers["key"] == "value"
        assert response.headers["pan"] == "cake"

    def test_successful_json_load_with_response(self, requests_mock):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"json": TEST_JSON_RESPONSE_DATA, "headers": TEST_HEADERS},
        )
        requests_mock.register_uri(
            TEST_METHOD,
            TEST_URL,
            headers=TEST_HEADERS,
            text=json.dumps(TEST_JSON_RESPONSE_DATA),
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.json() == TEST_JSON_RESPONSE_DATA

    def test_http_error(self, requests_mock):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS},
        )
        requests_mock.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )

        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.load()

    def test_socket_error(self, requests_mock):
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS},
        )
        requests_mock.register_uri(TEST_METHOD, TEST_URL_WITH_PARAMS, exc=socket.error)

        with pytest.raises(DataSetError, match="Failed to connect"):
            api_data_set.load()

    def test_read_only_mode(self):
        """
        Saving is disabled on the data set.
        """
        api_data_set = APIDataSet(url=TEST_URL, method=TEST_METHOD)
        with pytest.raises(DataSetError, match="is a read only data set type"):
            api_data_set.save({})

    def test_credentials_auth_error(self):
        """
        If ``auth`` in ``load_args`` and ``credentials`` are both provided,
        the constructor should raise a ValueError.
        """
        with pytest.raises(ValueError, match="both auth and credentials"):
            APIDataSet(
                url=TEST_URL, method=TEST_METHOD, load_args={"auth": []}, credentials={}
            )

    @staticmethod
    def _basic_auth(username, password):
        encoded = base64.b64encode(f"{username}:{password}".encode("latin-1"))
        return f"Basic {encoded.decode('latin-1')}"

    @pytest.mark.parametrize(
        "auth_kwarg",
        [{"load_args": {"auth": ("john", "doe")}}, {"credentials": ("john", "doe")}],
    )
    def test_auth_sequence(self, requests_mock, auth_kwarg):
        """
        ``auth`` and ``credentials`` should be able to be any Iterable.
        """

        api_data_set = APIDataSet(url=TEST_URL, method=TEST_METHOD, **auth_kwarg)
        requests_mock.register_uri(
            TEST_METHOD,
            TEST_URL,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.request.headers["Authorization"] == TestAPIDataSet._basic_auth(
            "john", "doe"
        )
        assert response.text == TEST_TEXT_RESPONSE_DATA

    def test_exists_http_error(self, requests_mock):
        """
        In case of an unexpected HTTP error,
        ``exists()`` should not silently catch it.
        """
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS},
        )
        requests_mock.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text="Nope, not found",
            status_code=requests.codes.FORBIDDEN,
        )
        with pytest.raises(DataSetError, match="Failed to fetch data"):
            api_data_set.exists()

    def test_exists_ok(self, requests_mock):
        """
        If the file actually exists and server responds 200,
        ``exists()`` should return True
        """
        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"params": TEST_PARAMS, "headers": TEST_HEADERS},
        )
        requests_mock.register_uri(
            TEST_METHOD,
            TEST_URL_WITH_PARAMS,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA,
        )

        assert api_data_set.exists()

    def test_certs(self, requests_mock):

        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            load_args={"cert": ("cert.pem", "privkey.pem")},
        )
        requests_mock.register_uri(TEST_METHOD, TEST_URL)

        api_data_set.load()
        assert requests_mock.last_request.cert == ("cert.pem", "privkey.pem")

    def test_stream(self, requests_mock):
        text = "I am being streamed."

        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"stream": True}
        )

        requests_mock.register_uri(TEST_METHOD, TEST_URL, text=text)

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert requests_mock.last_request.stream

        chunks = list(response.iter_content(chunk_size=2, decode_unicode=True))
        assert chunks == ["I ", "am", " b", "ei", "ng", " s", "tr", "ea", "me", "d."]

    def test_proxy(self, requests_mock):
        api_data_set = APIDataSet(
            url="ftp://example.com/api/test",
            method=TEST_METHOD,
            load_args={"proxies": {"ftp": "ftp://127.0.0.1:3000"}},
        )
        requests_mock.register_uri(
            TEST_METHOD,
            "ftp://example.com/api/test",
        )

        api_data_set.load()
        assert requests_mock.last_request.proxies.get("ftp") == "ftp://127.0.0.1:3000"

    def test_api_cookies(self, requests_mock):
        api_data_set = APIDataSet(
            url=TEST_URL, method=TEST_METHOD, load_args={"cookies": {"pan": "cake"}}
        )
        requests_mock.register_uri(TEST_METHOD, TEST_URL, text="text")

        api_data_set.load()
        assert requests_mock.last_request.headers["Cookie"] == "pan=cake"
