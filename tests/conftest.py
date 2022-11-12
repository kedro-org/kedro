"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""
import os
import sys

import aiobotocore
import botocore
import moto
import pytest
from botocore.awsrequest import AWSResponse
import aiobotocore.endpoint

# Patch `aiobotocore.endpoint.convert_to_response_dict` to work with moto.
class PatchedAWSResponse:
    def __init__(self, response: botocore.awsrequest.AWSResponse):
        self._response = response
        self.status_code = response.status_code
        self.raw = response.raw
        self.raw.raw_headers = {}

    @property
    async def content(self):
        return self._response.content


def factory(original):
    def patched_convert_to_response_dict(http_response, operation_model):
        return original(PatchedAWSResponse(http_response), operation_model)

    return patched_convert_to_response_dict


aiobotocore.endpoint.convert_to_response_dict = factory(
    aiobotocore.endpoint.convert_to_response_dict
)


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
