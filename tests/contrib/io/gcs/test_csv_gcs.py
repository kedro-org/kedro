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

# pylint: disable=protected-access,no-member
import os
from multiprocessing.reduction import ForkingPickler

import mock
import pytest
import google.auth.credentials
from google.auth.exceptions import DefaultCredentialsError
from google.cloud.exceptions import NotFound, Unauthorized
import pandas as pd
from pandas.util.testing import assert_frame_equal

from tests.contrib.io.gcs.utils import my_vcr

from kedro.contrib.io.gcs.csv_gcs import CSVGCSDataSet

FILENAME = "test.csv"
BUCKET_NAME = "test_bucket"
GCP_PROJECT = "test_project"
GCP_CREDENTIALS = mock.Mock(spec=google.auth.credentials.Credentials)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


class TestCSGCSDataSet:

    @mock.patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': 'wrong credentials'})
    def test_invalid_default_credentials(self):
        """Test invalid credentials for connecting to GCS"""
        with pytest.raises(DefaultCredentialsError):
            CSVGCSDataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME
            )

    @mock.patch.dict(os.environ, {})
    def test_invalid_passed_credentials(self):
        """Test invalid credentials for connecting to GCS"""
        with pytest.raises(Unauthorized):
            CSVGCSDataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME,
                credentials=GCP_CREDENTIALS
            )

    @my_vcr.use_cassette(match=['all'])
    def test_not_existing_bucket(self):
        """Test not existing bucket"""
        with pytest.raises(NotFound):
            CSVGCSDataSet(
                filepath=FILENAME,
                bucket_name='not-existing-bucket',
                credentials=GCP_CREDENTIALS
            )

    @my_vcr.use_cassette(match=['all'])
    @pytest.mark.usefixtures("dummy_dataframe")
    def test_load_data(self, dummy_dataframe):
        """Test loading the data from gcs."""
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS
        )
        loaded_data = dataset.load()
        assert_frame_equal(loaded_data, dummy_dataframe)

    @my_vcr.use_cassette(match=['all'])
    @pytest.mark.usefixtures("dummy_dataframe")
    def test_save_data(self, dummy_dataframe):
        """Test saving the data"""
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS
        )
        assert not dataset.exists()
        dataset.save(dummy_dataframe)
        loaded_data = dataset.load()
        assert_frame_equal(loaded_data, dummy_dataframe)

    @my_vcr.use_cassette(match=['all'])
    @pytest.mark.usefixtures("dummy_dataframe")
    def test_exists(self, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS
        )
        assert not dataset.exists()
        dataset.save(dummy_dataframe)
        assert dataset.exists()

    @my_vcr.use_cassette(match=['all'])
    def test_load_save_args(self):
        """Test default load and save arguments of the data set."""
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS
        )
        assert not dataset._load_args
        assert "index" in dataset._save_args

    @my_vcr.use_cassette(match=['all'])
    def test_load_extra_params(self):
        """Test overriding the default load arguments."""
        load_args = {"k1": "v1", "index": "value"}
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS,
            load_args=load_args
        )
        for key, value in load_args.items():
            assert dataset._load_args[key] == value

    @my_vcr.use_cassette(match=['all'])
    def test_save_extra_params(self):
        """Test overriding the default save arguments."""
        save_args = {"k1": "v1", "index": "value"}
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS,
            save_args=save_args
        )
        for key, value in save_args.items():
            assert dataset._save_args[key] == value

    @my_vcr.use_cassette(match=['all'])
    def test_str_representation(self):
        """Test string representation of the data set instance."""
        save_args = {"option": "value"}
        dataset = CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS,
            save_args=save_args
        )
        str_repr = str(dataset)
        assert "CSVGCSDataSet" in str_repr
        for k in save_args.keys():
            assert k in str_repr

    # pylint: disable=unused-argument
    @my_vcr.use_cassette(match=['all'])
    def test_load_args_propagated(self, mocker):
        mock = mocker.patch("kedro.contrib.io.gcs.csv_gcs.pd.read_csv")
        CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS,
            load_args=dict(custom=42)
        ).load()
        assert mock.call_args_list[0][1] == {"custom": 42}
