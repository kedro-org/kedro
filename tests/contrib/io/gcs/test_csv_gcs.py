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

import mock
import pytest
import google.auth.credentials
import pandas as pd
from pandas.util.testing import assert_frame_equal

from kedro.io import DataSetError
from tests.contrib.io.gcs.utils import gcs_vcr

from kedro.contrib.io.gcs.csv_gcs import CSVGCSDataSet

FILENAME = "test.csv"
BUCKET_NAME = "test_bucket"
GCP_PROJECT = "test_project"
GCP_CREDENTIALS = mock.Mock(spec=google.auth.credentials.Credentials)


@pytest.fixture
def dummy_dataframe():
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture(params=[None])
def load_args(request):
    return request.param


@pytest.fixture(params=[None])
def save_args(request):
    return request.param


@pytest.fixture
@gcs_vcr.use_cassette(match=['all'])
def gcs_data_set(load_args, save_args):
    return CSVGCSDataSet(
        filepath=FILENAME,
        bucket_name=BUCKET_NAME,
        credentials=GCP_CREDENTIALS,
        load_args=load_args,
        save_args=save_args,
    )


class TestCSVGCSDataSet:
    @mock.patch.dict(os.environ, {'GOOGLE_APPLICATION_CREDENTIALS': 'wrong credentials'})
    def test_invalid_credentials(self):
        """Test invalid credentials for connecting to GCS"""
        pattern = "Anonymous caller"
        with pytest.raises(DataSetError, match=pattern):
            CSVGCSDataSet(
                filepath=FILENAME,
                bucket_name=BUCKET_NAME
            ).load()

    @gcs_vcr.use_cassette(match=['all'])
    def test_not_existing_bucket(self):
        """Test not existing bucket"""
        pattern = "Failed while loading data from data set"
        with pytest.raises(DataSetError, match=pattern):
            CSVGCSDataSet(
                filepath=FILENAME,
                bucket_name='not-existing-bucket',
                credentials=GCP_CREDENTIALS
            ).load()

    @gcs_vcr.use_cassette(match=['all'])
    def test_load_data(self, gcs_data_set, dummy_dataframe):
        """Test loading the data from gcs."""
        loaded_data = gcs_data_set.load()
        assert_frame_equal(loaded_data, dummy_dataframe)

    @gcs_vcr.use_cassette(match=['all'])
    def test_save_data(self, gcs_data_set, dummy_dataframe):
        """Test saving the data"""
        assert not gcs_data_set.exists()
        gcs_data_set.save(dummy_dataframe)
        loaded_data = gcs_data_set.load()
        assert_frame_equal(loaded_data, dummy_dataframe)

    @gcs_vcr.use_cassette(match=['all'])
    def test_exists(self, gcs_data_set, dummy_dataframe):
        """Test `exists` method invocation for both existing and
        nonexistent data set."""
        assert not gcs_data_set.exists()
        gcs_data_set.save(dummy_dataframe)
        assert gcs_data_set.exists()

    def test_load_save_args(self, gcs_data_set):
        """Test default load and save arguments of the data set."""
        assert not gcs_data_set._load_args
        assert "index" in gcs_data_set._save_args

    @pytest.mark.parametrize(
        "load_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_load_extra_params(self, gcs_data_set, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert gcs_data_set._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"k1": "v1", "index": "value"}], indirect=True
    )
    def test_save_extra_params(self, gcs_data_set, save_args):
        """Test overriding the default save arguments."""
        save_args = {"k1": "v1", "index": "value"}
        for key, value in save_args.items():
            assert gcs_data_set._save_args[key] == value

    @pytest.mark.parametrize("save_args", [{"option": "value"}], indirect=True)
    def test_str_representation(self, gcs_data_set, save_args):
        """Test string representation of the data set instance."""
        str_repr = str(gcs_data_set)
        assert "CSVGCSDataSet" in str_repr
        for k in save_args.keys():
            assert k in str_repr

    # pylint: disable=unused-argument
    @gcs_vcr.use_cassette(match=['all'])
    def test_load_args_propagated(self, mocker, gcs_data_set):
        mock = mocker.patch("kedro.contrib.io.gcs.csv_gcs.pd.read_csv")
        CSVGCSDataSet(
            filepath=FILENAME,
            bucket_name=BUCKET_NAME,
            credentials=GCP_CREDENTIALS,
            load_args=dict(custom=42)
        ).load()
        assert mock.call_args_list[0][1] == {"custom": 42}
