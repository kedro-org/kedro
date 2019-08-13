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

# pylint: disable=unused-argument

from unittest.mock import patch

import pandas as pd
import pytest

from kedro.contrib.io.azure import JSONBlobDataSet
from kedro.io import DataSetError

TEST_FILE_NAME = "test.json"
TEST_CONTAINER_NAME = "test_bucket"
TEST_CREDENTIALS = {"account_name": "ACCOUNT_NAME", "account_key": "ACCOUNT_KEY"}


@pytest.fixture()
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def blob_json_data_set():
    def make_data_set(load_args=None, save_args=None):
        return JSONBlobDataSet(
            filepath=TEST_FILE_NAME,
            container_name=TEST_CONTAINER_NAME,
            encoding="utf-8",
            blob_to_bytes_args={"to_extra": 42},
            blob_from_bytes_args={"from_extra": 42},
            credentials=TEST_CREDENTIALS,
            load_args=load_args,
            save_args=save_args,
        )

    return make_data_set


@patch("kedro.contrib.io.azure.json_blob.BlockBlobService")
def test_pass_credentials_load(blob_service, blob_json_data_set):
    try:
        blob_json_data_set().load()
    except DataSetError:
        # We don't care about it for this test, we just want to know that
        # azure service was called with the right parameters
        pass
    blob_service.assert_called_with(
        account_name="ACCOUNT_NAME", account_key="ACCOUNT_KEY"
    )


@patch("kedro.contrib.io.azure.json_blob.BlockBlobService")
def test_pass_credentials_save(blob_service, blob_json_data_set, dummy_dataframe):
    blob_json_data_set().save(dummy_dataframe)
    blob_service.assert_called_with(
        account_name="ACCOUNT_NAME", account_key="ACCOUNT_KEY"
    )


@patch("kedro.contrib.io.azure.json_blob.BlockBlobService.get_blob_to_bytes")
def test_load_blob_args(get_blob_mock, blob_json_data_set):
    try:
        blob_json_data_set().load()
    except DataSetError:
        pass

    get_blob_mock.assert_called_with(
        container_name=TEST_CONTAINER_NAME, blob_name=TEST_FILE_NAME, to_extra=42
    )


class BlobMock:
    def __init__(self):
        self._content = '{"name": ["tom", "bob"], "age": [3, 4]}\n'.encode("utf-8")

    @property
    def content(self):
        return self._content


def mock_load_func():
    def mocked(*args, **kwargs):
        return BlobMock()

    return mocked


@patch(
    "kedro.contrib.io.azure.json_blob.BlockBlobService.get_blob_to_bytes",
    new_callable=mock_load_func,
)
def test_load(get_blob_mock, blob_json_data_set):
    result = blob_json_data_set().load()[["name", "age"]]
    expected = pd.DataFrame({"name": ["tom", "bob"], "age": [3, 4]})
    expected = expected[["name", "age"]]
    assert result.equals(expected)


class BlobMockDelimited:
    def __init__(self):
        self._content = '{"name": "tom", "age": 3}\n{"name": "bob", "age": 4}\n'.encode(
            "utf-8"
        )

    @property
    def content(self):
        return self._content


def mock_load_delimited_func():
    def mocked(*args, **kwargs):
        return BlobMockDelimited()

    return mocked


@patch(
    "kedro.contrib.io.azure.json_blob.BlockBlobService.get_blob_to_bytes",
    new_callable=mock_load_delimited_func,
)
def test_load_delimited(get_blob_mock, blob_json_data_set):
    result = blob_json_data_set(load_args={"lines": True}).load()[["name", "age"]]
    expected = pd.DataFrame({"name": ["tom", "bob"], "age": [3, 4]})
    expected = expected[["name", "age"]]
    assert result.equals(expected)


@patch("kedro.contrib.io.azure.json_blob.BlockBlobService.create_blob_from_bytes")
def test_save_blob_args(blob_from_mock, blob_json_data_set, dummy_dataframe):
    blob_json_data_set().save(dummy_dataframe)
    blob_from_mock.assert_called_with(
        container_name=TEST_CONTAINER_NAME,
        blob_name=TEST_FILE_NAME,
        blob=dummy_dataframe.to_json().encode("utf-8"),
        from_extra=42,
    )


def test_str_representation(blob_json_data_set):
    data_set = blob_json_data_set(save_args={"option": "value"})
    assert "JSONBlobDataSet" in str(data_set)
    assert TEST_CREDENTIALS["account_name"] not in str(data_set)
    assert TEST_CREDENTIALS["account_key"] not in str(data_set)
