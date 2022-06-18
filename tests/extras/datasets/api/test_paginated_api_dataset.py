# pylint: disable=no-member

from types import GeneratorType

import pytest

from kedro.extras.datasets.api import PaginatedJSONAPIDataSet

TEST_HEADERS = {"key": "value"}
TEST_URL = "http://example.com/api/test"
TEST_PARAMS = {"param": "value"}
TEST_URL_WITH_PARAMS = TEST_URL + "?param=value"

TEST_URL_WITH_PARAMS_PAGINATED = TEST_URL_WITH_PARAMS + "&page=2"
TEST_JSON_RESPONSE_DATA_PAGINATED = {"key": 1, "next": TEST_URL_WITH_PARAMS_PAGINATED}
TEST_JSON_RESPONSE_DATA_END_PAGINATED = {"key": 2, "next": None}


class TestPaginatedJSONAPIDataSet:
    def test_load_returns_generator(self, requests_mock):
        api_data_set = PaginatedJSONAPIDataSet(url=TEST_URL)
        requests_mock.get(TEST_URL)
        responses = api_data_set.load()
        assert isinstance(responses, GeneratorType)

    def test_headers_are_set(self):
        api_data_set = PaginatedJSONAPIDataSet(url=TEST_URL, headers=TEST_HEADERS)
        assert set(TEST_HEADERS.items()).issubset(api_data_set._session.headers.items())
        assert api_data_set._session.headers["Connection"] == "keep-alive"

    def test_load_handles_pagination(self, requests_mock):
        requests_mock.register_uri(
            "GET", TEST_URL_WITH_PARAMS, json=TEST_JSON_RESPONSE_DATA_PAGINATED
        )
        requests_mock.register_uri(
            "GET",
            TEST_URL_WITH_PARAMS_PAGINATED,
            json=TEST_JSON_RESPONSE_DATA_END_PAGINATED,
        )

        api_data_set = PaginatedJSONAPIDataSet(
            url=TEST_URL, params=TEST_PARAMS, path_to_next_page="next"
        )
        responses = list(api_data_set.load())
        expected_num_respones = 2
        assert len(responses) == expected_num_respones
        assert responses[0].json()["key"] == 1
        assert responses[1].json()["key"] == 2
