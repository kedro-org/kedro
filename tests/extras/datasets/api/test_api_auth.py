import pytest
import requests
from requests.auth import AuthBase, _basic_auth_str

from kedro.extras.datasets.api import APIDataSet
from tests.extras.datasets.api.test_api_dataset import TEST_URL, TEST_METHOD, TEST_HEADERS, TEST_TEXT_RESPONSE_DATA


class AccessTokenAuth(AuthBase):
    """Attaches Access Token Authentication to the given Request object."""

    def __init__(self, token):
        # setup any auth-related data here
        self.token = token

    def __call__(self, r):
        # modify and return the request
        r.headers['Authorization'] = f'access_token {self.token}'
        return r


class TestApiAuth:

    @pytest.mark.parametrize("auth_type,auth_cred,auth_header_key, auth_header_value", [
        ("requests.auth.HTTPBasicAuth", { "username": "john", "password": "doe" }, "Authorization", _basic_auth_str('john', 'doe')),
        ("requests.auth.HTTPProxyAuth", { "username": "john", "password": "doe" }, "Proxy-Authorization", _basic_auth_str('john', 'doe')),
        ("tests.extras.datasets.api.test_api_auth.AccessTokenAuth", { "token": "abc" }, "Authorization", "access_token abc"),
    ])
    def test_auth_sequence(self, requests_mocker, auth_cred, auth_type, auth_header_key, auth_header_value):

        api_data_set = APIDataSet(
            url=TEST_URL,
            method=TEST_METHOD,
            auth_type=auth_type,
            load_args={"headers": TEST_HEADERS},
            credentials=auth_cred
        )

        requests_mocker.register_uri(
            TEST_METHOD,
            TEST_URL,
            headers=TEST_HEADERS,
            text=TEST_TEXT_RESPONSE_DATA
        )

        response = api_data_set.load()
        assert isinstance(response, requests.Response)
        assert response.text == TEST_TEXT_RESPONSE_DATA
        assert requests_mocker.last_request.headers[auth_header_key] == auth_header_value