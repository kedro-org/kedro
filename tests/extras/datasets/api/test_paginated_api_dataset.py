# pylint: disable=no-member
from types import GeneratorType

from kedro.extras.datasets.api import PaginatedJSONAPIDataSet

TEST_URL = "http://example.com/api/test"


class TestPaginatedJSONAPIDataSet:
    def test_load_returns_generator(self, requests_mock):
        api_data_set = PaginatedJSONAPIDataSet(url=TEST_URL)
        requests_mock.get(TEST_URL)
        responses = api_data_set.load()
        assert isinstance(responses, GeneratorType)
