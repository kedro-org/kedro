import pytest
import requests_mock


@pytest.fixture
def requests_mocker():
    with requests_mock.Mocker() as mock:
        yield mock