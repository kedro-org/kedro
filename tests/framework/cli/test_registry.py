# Copyright 2021 QuantumBlack Visual Analytics Limited
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


@pytest.fixture
def yaml_dump_mock(mocker):
    return mocker.patch("yaml.dump", return_value="Result YAML")


@pytest.fixture
def pipelines_dict():
    pipelines = {
        "de": ["split_data (split_data)"],
        "ds": [
            "train_model (train_model)",
            "predict (predict)",
            "report_accuracy (report_accuracy)",
        ],
        "dp": ["data_processing.split_data (split_data)"],
    }
    pipelines["__default__"] = pipelines["de"] + pipelines["ds"]
    return pipelines


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
def test_list_registered_pipelines(
    fake_project_cli, fake_metadata, yaml_dump_mock, pipelines_dict
):
    result = CliRunner().invoke(
        fake_project_cli, ["registry", "list"], obj=fake_metadata
    )

    assert not result.exit_code
    yaml_dump_mock.assert_called_once_with(sorted(pipelines_dict.keys()))


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestRegistryDescribeCommand:
    @pytest.mark.parametrize("pipeline_name", ["de", "ds", "dp", "__default__"])
    def test_describe_registered_pipeline(
        self,
        fake_project_cli,
        fake_metadata,
        yaml_dump_mock,
        pipeline_name,
        pipelines_dict,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["registry", "describe", pipeline_name],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict[pipeline_name]}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_registered_pipeline_not_found(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli, ["registry", "describe", "missing"], obj=fake_metadata
        )

        assert result.exit_code
        expected_output = (
            "Error: `missing` pipeline not found. Existing pipelines: "
            "[__default__, de, dp, ds]\n"
        )
        assert expected_output in result.output

    def test_describe_registered_pipeline_default(
        self,
        fake_project_cli,
        fake_metadata,
        yaml_dump_mock,
        pipelines_dict,
    ):
        result = CliRunner().invoke(
            fake_project_cli,
            ["registry", "describe"],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {"Nodes": pipelines_dict["__default__"]}
        yaml_dump_mock.assert_called_once_with(expected_dict)
