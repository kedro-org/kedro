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

import io
from pathlib import PurePosixPath
from unittest.mock import patch

import pandas as pd
import pytest
from pandas.util.testing import assert_frame_equal

from kedro.contrib.io.azure import CSVBlobDataSet
from kedro.io import DataSetError, Version
from kedro.io.core import generate_timestamp

TEST_FILE_NAME = "test.csv"
TEST_CONTAINER_NAME = "test_bucket"
TEST_CREDENTIALS = {"account_name": "ACCOUNT_NAME", "account_key": "ACCOUNT_KEY"}


@pytest.fixture(params=[None])
def load_version(request):
    return request.param


@pytest.fixture(params=[None])
def save_version(request):
    return request.param or generate_timestamp()


@pytest.fixture()
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def blob_csv_data_set():
    def make_data_set(load_args=None, save_args=None):
        return CSVBlobDataSet(
            filepath=TEST_FILE_NAME,
            container_name=TEST_CONTAINER_NAME,
            blob_to_text_args={"to_extra": 42},
            blob_from_text_args={"from_extra": 42},
            credentials=TEST_CREDENTIALS,
            load_args=load_args,
            save_args=save_args,
        )

    return make_data_set


@pytest.fixture
def versioned_blob_csv_data_set(load_version, save_version):
    return CSVBlobDataSet(
        filepath=TEST_FILE_NAME,
        container_name=TEST_CONTAINER_NAME,
        credentials=TEST_CREDENTIALS,
        blob_to_text_args={"to_extra": 41},
        blob_from_text_args={"from_extra": 42},
        version=Version(load_version, save_version),
    )


@pytest.fixture
def save_path(save_version):
    return "{0}/{1}/{0}".format(TEST_FILE_NAME, save_version)


class TestCSVBlobDataSetVersioned:
    # pylint: disable=too-many-arguments
    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.create_blob_from_text")
    @patch(
        "kedro.contrib.io.azure.csv_blob.BlockBlobService.exists", return_value=False
    )
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    def test_save(
        self,
        load_mock,
        exists_mock,
        save_mock,
        versioned_blob_csv_data_set,
        dummy_dataframe,
        save_path,
    ):
        """Test that saving saves with a correct version"""
        versioned_blob_csv_data_set.save(dummy_dataframe)
        save_mock.assert_called_with(
            container_name=TEST_CONTAINER_NAME,
            blob_name=save_path,
            text=dummy_dataframe.to_csv(index=False),
            from_extra=42,
        )

    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.get_blob_to_text")
    def test_load(self, get_blob_mock, load_mock, versioned_blob_csv_data_set):
        load_mock.return_value = TEST_FILE_NAME
        get_blob_mock.return_value = BlobMock()
        result = versioned_blob_csv_data_set.load()
        get_blob_mock.assert_called_once_with(
            container_name=TEST_CONTAINER_NAME, blob_name=TEST_FILE_NAME, to_extra=41
        )
        expected = pd.read_csv(io.StringIO(BlobMock().content))
        assert_frame_equal(result, expected)

    @patch(
        "kedro.contrib.io.azure.csv_blob.BlockBlobService.list_blob_names",
        return_value=[],
    )
    @patch(
        "kedro.contrib.io.azure.csv_blob.BlockBlobService.exists", return_value=False
    )
    def test_no_versions(self, exists_mock, list_mock, versioned_blob_csv_data_set):
        """Check the error if no versions are available for load."""
        pattern = r"Did not find any versions for CSVBlobDataSet\(.+\)"
        with pytest.raises(DataSetError, match=pattern):
            versioned_blob_csv_data_set.load()

    # pylint: disable=too-many-arguments
    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.create_blob_from_text")
    @patch(
        "kedro.contrib.io.azure.csv_blob.BlockBlobService.exists", return_value=False
    )
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    def test_exists(
        self,
        load_mock,
        exists_mock,
        save_mock,
        versioned_blob_csv_data_set,
        dummy_dataframe,
        save_path,
    ):
        versioned_blob_csv_data_set.save(dummy_dataframe)
        load_mock.return_value = PurePosixPath(save_path)
        versioned_blob_csv_data_set.exists()
        exists_mock.assert_called_with(TEST_CONTAINER_NAME, blob_name=save_path)

    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.create_blob_from_text")
    @patch(
        "kedro.contrib.io.azure.csv_blob.BlockBlobService.exists", return_value=False
    )
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    def test_exists_dataset_error(
        self,
        load_mock,
        exists_mock,
        save_mock,
        versioned_blob_csv_data_set,
        dummy_dataframe,
        save_path,
    ):
        versioned_blob_csv_data_set.save(dummy_dataframe)
        load_mock.side_effect = DataSetError
        assert not versioned_blob_csv_data_set.exists()

    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.exists", return_value=True)
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    def test_prevent_override(
        self, load_mock, exists_mock, versioned_blob_csv_data_set, dummy_dataframe
    ):
        """Check the error when attempting to override the data set if the
        corresponding csv file for a given save version already exists in S3.
        """
        pattern = (
            r"Save path \`.+\` for CSVBlobDataSet\(.+\) must not exist "
            r"if versioning is enabled"
        )
        with pytest.raises(DataSetError, match=pattern):
            versioned_blob_csv_data_set.save(dummy_dataframe)

    @patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.create_blob_from_text")
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_save_path")
    @patch("kedro.contrib.io.azure.csv_blob.CSVBlobDataSet._get_load_path")
    def test_save_version_warning(
        self,
        load_mock,
        save_mock,
        create_blob_mock,
        versioned_blob_csv_data_set,
        dummy_dataframe,
    ):
        """Check the warning when saving to the path that differs from
        the subsequent load path."""
        save_version = "2019-01-02T00.00.00.000Z"
        load_version = "2019-01-01T23.59.59.999Z"
        pattern = (
            r"Save path `{f}/{sv}/{f}` did not match load path "
            r"`{f}/{lv}/{f}` for CSVBlobDataSet\(.+\)".format(
                f=TEST_FILE_NAME, sv=save_version, lv=load_version
            )
        )
        load_mock.return_value = PurePosixPath(
            "{0}/{1}/{0}".format(TEST_FILE_NAME, load_version)
        )
        save_mock.return_value = PurePosixPath(
            "{0}/{1}/{0}".format(TEST_FILE_NAME, save_version)
        )
        with pytest.warns(UserWarning, match=pattern):
            versioned_blob_csv_data_set.save(dummy_dataframe)

    def test_version_str_repr(self, load_version, save_version):
        """Test that version is in string representation of the class instance
        when applicable."""
        ds = CSVBlobDataSet(
            filepath=TEST_FILE_NAME,
            container_name=TEST_CONTAINER_NAME,
            credentials=TEST_CREDENTIALS,
        )
        ds_versioned = CSVBlobDataSet(
            filepath=TEST_FILE_NAME,
            container_name=TEST_CONTAINER_NAME,
            credentials=TEST_CREDENTIALS,
            version=Version(load_version, save_version),
        )
        assert TEST_FILE_NAME in str(ds)
        assert "version" not in str(ds)

        assert TEST_FILE_NAME in str(ds_versioned)
        ver_str = "version=Version(load={}, save='{}')".format(
            load_version, save_version
        )
        assert ver_str in str(ds_versioned)


@patch("kedro.contrib.io.azure.csv_blob.BlockBlobService")
def test_pass_credentials_load(blob_service, blob_csv_data_set):
    try:
        blob_csv_data_set().load()
    except DataSetError:
        # We don't care about it for this test, we just want to know that
        # azure service was called with the right parameters
        pass
    blob_service.assert_called_with(
        account_name="ACCOUNT_NAME", account_key="ACCOUNT_KEY"
    )


@patch("kedro.contrib.io.azure.csv_blob.BlockBlobService")
def test_pass_credentials_save(blob_service, blob_csv_data_set, dummy_dataframe):
    blob_csv_data_set().save(dummy_dataframe)
    blob_service.assert_called_with(
        account_name="ACCOUNT_NAME", account_key="ACCOUNT_KEY"
    )


@patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.get_blob_to_text")
def test_load_blob_args(get_blob_mock, blob_csv_data_set):
    try:
        blob_csv_data_set().load()
    except DataSetError:
        pass

    get_blob_mock.assert_called_with(
        container_name=TEST_CONTAINER_NAME, blob_name=TEST_FILE_NAME, to_extra=42
    )


class BlobMock:
    def __init__(self):
        self._content = "name,age\ntom,3\nbob,4"

    @property
    def content(self):
        return self._content


def mock_load_func():
    def mocked(*args, **kwargs):
        return BlobMock()

    return mocked


@patch(
    "kedro.contrib.io.azure.csv_blob.BlockBlobService.get_blob_to_text",
    new_callable=mock_load_func,
)
def test_load(get_blob_mock, blob_csv_data_set):
    result = blob_csv_data_set().load()[["name", "age"]]
    expected = pd.DataFrame({"name": ["tom", "bob"], "age": [3, 4]})
    expected = expected[["name", "age"]]
    assert_frame_equal(result, expected)


@patch("kedro.contrib.io.azure.csv_blob.BlockBlobService.create_blob_from_text")
def test_save_blob_args(blob_from_mock, blob_csv_data_set, dummy_dataframe):
    blob_csv_data_set().save(dummy_dataframe)
    blob_from_mock.assert_called_with(
        container_name=TEST_CONTAINER_NAME,
        blob_name=TEST_FILE_NAME,
        text=dummy_dataframe.to_csv(index=False),
        from_extra=42,
    )


# pylint: disable=protected-access
def test_load_extra_params(blob_csv_data_set):
    expected_keys = ["option"]
    data_set = blob_csv_data_set(load_args={"option": "value"})
    for expected_key in expected_keys:
        assert expected_key in data_set._load_args.keys()


# pylint: disable=protected-access
def test_save_with_extra_params(blob_csv_data_set):
    expected_keys = ["index", "option"]
    data_set = blob_csv_data_set(save_args={"option": "value"})
    for expected_key in expected_keys:
        assert expected_key in data_set._save_args.keys()


def test_str_representation(blob_csv_data_set):
    data_set = blob_csv_data_set(save_args={"option": "value"})
    assert "CSVBlobDataSet" in str(data_set)
    assert TEST_CREDENTIALS["account_name"] not in str(data_set)
    assert TEST_CREDENTIALS["account_key"] not in str(data_set)
