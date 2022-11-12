"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""
import os
import sys

import aiobotocore
import aiobotocore.endpoint
import botocore
import pytest
from botocore.awsrequest import AWSResponse

from typing import Callable
from unittest.mock import MagicMock

import aiobotocore.awsrequest
import aiobotocore.endpoint
import aiohttp
import aiohttp.client_reqrep
import aiohttp.typedefs
import botocore.awsrequest
import botocore.model
import pytest

"""
Patch aiobotocore to work with moto
See https://github.com/aio-libs/aiobotocore/issues/755
"""


class MockAWSResponse(aiobotocore.awsrequest.AioAWSResponse):
    def __init__(self, response: botocore.awsrequest.AWSResponse):
        self._moto_response = response
        self.status_code = response.status_code
        self.raw = MockHttpClientResponse(response)

    # adapt async methods to use moto's response
    async def _content_prop(self) -> bytes:
        return self._moto_response.content

    async def _text_prop(self) -> str:
        return self._moto_response.text


class MockHttpClientResponse(aiohttp.client_reqrep.ClientResponse):
    def __init__(self, response: botocore.awsrequest.AWSResponse):

        async def read(self, n: int = -1) -> bytes:
            # streaming/range requests. used by s3fs
            return response.content

        self.content = MagicMock(aiohttp.StreamReader)
        self.content.read = read
        self.response = response

    @property
    def raw_headers(self) -> aiohttp.typedefs.RawHeaders:
        # Return the headers encoded the way that aiobotocore expects them
        return { k.encode('utf-8') : str(v).encode('utf-8') for k, v in self.response.headers.items() }.items()


# @pytest.fixture
# def patch_aiobotocore():
def factory(original: Callable) -> Callable:
    def patched_convert_to_response_dict(
        http_response: botocore.awsrequest.AWSResponse, operation_model: botocore.model.OperationModel
    ):
        return original(MockAWSResponse(http_response), operation_model)

    return patched_convert_to_response_dict

aiobotocore.endpoint.convert_to_response_dict = factory(aiobotocore.endpoint.convert_to_response_dict)


@pytest.fixture(autouse=True)
def preserve_system_context():
    """
    Revert some changes to the application context tests do to isolate them.
    """
    old_path = sys.path.copy()
    old_cwd = os.getcwd()
    yield
    sys.path = old_path

    if os.getcwd() != old_cwd:
        os.chdir(old_cwd)  # pragma: no cover
