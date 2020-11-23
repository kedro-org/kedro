# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
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
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from google.cloud.exceptions import NotFound
from kedro.extras.datasets.avro import GBQTableGCSAVRODataSet
from kedro.io.core import DataSetError


DATASET = "dataset"
TABLE_NAME = "table_name"
PROJECT = "project"
BUCKET = "bucket"
OBJECT = "test.avro"


@pytest.fixture
def mock_bigquery_client(mocker):
    return mocker.patch("google.cloud.bigquery.Client", autospec=True)


@pytest.fixture
def gbq_to_gcs_avro_dataset(
    load_args, save_args, mock_bigquery_client
):  # pylint: disable=unused-argument
    return GBQTableGCSAVRODataSet(
        project=PROJECT,
        dataset=DATASET,
        table_name=TABLE_NAME,
        bucket=BUCKET,
        path_object=OBJECT,
        credentials=None,
        load_args=load_args,
        save_args=save_args,
    )


class TestGBQTableGCSAVRODataSet:
    def test_exists(self, mock_bigquery_client):
        """Test `exists` method invocation."""
        mock_bigquery_client.return_value.get_table.side_effect = [
            NotFound("NotFound"),
            "exists",
        ]

        data_set = GBQTableGCSAVRODataSet(PROJECT, DATASET, TABLE_NAME, BUCKET)
        assert not data_set.exists()
        assert data_set.exists()

    @pytest.mark.parametrize(
        "load_args", [{"use_avro_logical_types": False}], indirect=True
    )
    def test_load_extra_params(self, gbq_to_gcs_avro_dataset, load_args):
        """Test overriding the default load arguments."""
        for key, value in load_args.items():
            assert gbq_to_gcs_avro_dataset._load_args[key] == value

    @pytest.mark.parametrize(
        "save_args", [{"use_avro_logical_types": False}], indirect=True
    )
    def test_save_extra_params(self, gbq_to_gcs_avro_dataset, save_args):
        """Test overriding the default save arguments."""
        for key, value in save_args.items():
            assert gbq_to_gcs_avro_dataset._save_args[key] == value

    def test_load_missing_object(self, gbq_to_gcs_avro_dataset):
        assert not gbq_to_gcs_avro_dataset.load()

    def test_save_missing_bucket(self, gbq_to_gcs_avro_dataset):
        assert not gbq_to_gcs_avro_dataset.save(1)
