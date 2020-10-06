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
from click.testing import CliRunner

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io import DataCatalog, MemoryDataSet


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestCatalogListCommand:
    PIPELINE_NAME = "pipeline"

    @staticmethod
    @pytest.fixture
    def fake_load_context(mocker):
        context = mocker.MagicMock()
        return mocker.patch(
            "kedro.framework.cli.catalog.load_context", return_value=context
        )

    def test_list_all_pipelines(self, fake_kedro_cli, fake_load_context, mocker):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        mocked_context.pipelines.keys.return_value = (self.PIPELINE_NAME,)
        mocked_context.catalog.list.return_value = []
        mocked_pl_obj = mocked_context.pipelines.get.return_value
        mocked_pl_obj.data_sets.return_value = set()

        result = CliRunner().invoke(fake_kedro_cli.cli, ["catalog", "list"])

        assert not result.exit_code
        assert mocked_context.pipelines.keys.call_count == 1
        mocked_context.pipelines.get.assert_called_once_with(self.PIPELINE_NAME)

        expected_dict = {"DataSets in 'pipeline' pipeline": {}}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_list_specific_pipelines(self, fake_kedro_cli, fake_load_context):
        mocked_context = fake_load_context.return_value

        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["catalog", "list", "--pipeline", self.PIPELINE_NAME]
        )

        assert not result.exit_code
        assert not mocked_context.pipelines.keys.called
        mocked_context.pipelines.get.assert_called_once_with(self.PIPELINE_NAME)

    def test_not_found_pipeline(self, fake_kedro_cli, fake_load_context):
        mocked_context = fake_load_context.return_value
        mocked_context.pipelines.get.return_value = None
        mocked_context.pipelines.keys.return_value = (self.PIPELINE_NAME,)
        result = CliRunner().invoke(
            fake_kedro_cli.cli, ["catalog", "list", "--pipeline", "fake"]
        )
        assert result.exit_code
        expected_output = (
            f"Error: fake pipeline not found! Existing "
            f"pipelines: {self.PIPELINE_NAME}\n"
        )
        assert expected_output in result.output

    def test_no_param_datasets_in_respose(
        self, fake_kedro_cli, fake_load_context, mocker
    ):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_data_sets = {
            "iris_data": CSVDataSet("test.csv"),
            "parameters": MemoryDataSet(),
            "params:data_ratio": MemoryDataSet(),
            "intermediate": MemoryDataSet(),
            "not_used": CSVDataSet("test2.csv"),
        }

        pl_obj_data_sets = catalog_data_sets.keys() - {"not_used"}
        mocked_context.catalog = DataCatalog(data_sets=catalog_data_sets)
        mocked_context.pipelines.keys.return_value = (self.PIPELINE_NAME,)
        mocked_pl_obj = mocked_context.pipelines.get.return_value
        mocked_pl_obj.data_sets.return_value = pl_obj_data_sets

        result = CliRunner().invoke(fake_kedro_cli.cli, ["catalog", "list"])

        assert not result.exit_code
        # 'parameters' and 'params:data_ratio' should not appear in the response
        expected_dict = {
            "DataSets in 'pipeline' pipeline": {
                "Datasets mentioned in pipeline": {
                    "CSVDataSet": ["iris_data"],
                    "MemoryDataSet": ["intermediate"],
                },
                "Datasets not mentioned in pipeline": {"CSVDataSet": ["not_used"]},
            }
        }
        yaml_dump_mock.assert_called_once_with(expected_dict)
