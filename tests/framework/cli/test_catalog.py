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

import shutil
from functools import partial

import pytest
import yaml
from click.testing import CliRunner

from kedro.extras.datasets.pandas import CSVDataSet
from kedro.io import DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline, node


@pytest.fixture
def fake_load_context(mocker):
    context = mocker.MagicMock()
    return mocker.patch(
        "kedro.framework.session.KedroSession.load_context", return_value=context
    )


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture
def fake_cli_invoke(fake_project_cli, fake_metadata):
    return partial(CliRunner().invoke, fake_project_cli.cli, obj=fake_metadata)


PIPELINE_NAME = "pipeline"


@pytest.fixture
def mock_pipelines(mocker):
    dummy_pipelines = {PIPELINE_NAME: Pipeline([]), "second": Pipeline([])}
    return mocker.patch("kedro.framework.cli.catalog.pipelines", dummy_pipelines)


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
class TestCatalogListCommand:
    def test_list_all_pipelines(self, fake_cli_invoke, mocker):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")

        result = fake_cli_invoke(["catalog", "list"])

        assert not result.exit_code
        expected_dict = {
            "DataSets in 'pipeline' pipeline": {},
            "DataSets in 'second' pipeline": {},
        }
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_list_specific_pipelines(self, fake_cli_invoke, mocker):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")

        result = fake_cli_invoke(["catalog", "list", "--pipeline", PIPELINE_NAME])

        assert not result.exit_code
        expected_dict = {f"DataSets in '{PIPELINE_NAME}' pipeline": {}}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_not_found_pipeline(self, fake_cli_invoke):
        result = fake_cli_invoke(["catalog", "list", "--pipeline", "fake"])

        assert result.exit_code
        expected_output = (
            "Error: `fake` pipeline not found! Existing pipelines: pipeline, second"
        )
        assert expected_output in result.output

    def test_no_param_datasets_in_respose(
        self, fake_cli_invoke, fake_load_context, mocker, mock_pipelines
    ):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_data_sets = {
            "iris_data": CSVDataSet("test.csv"),
            "intermediate": MemoryDataSet(),
            "parameters": MemoryDataSet(),
            "params:data_ratio": MemoryDataSet(),
            "not_used": CSVDataSet("test2.csv"),
        }

        mocked_context.catalog = DataCatalog(data_sets=catalog_data_sets)
        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "data_sets",
            return_value=catalog_data_sets.keys() - {"not_used"},
        )

        result = fake_cli_invoke(["catalog", "list"])

        assert not result.exit_code
        # 'parameters' and 'params:data_ratio' should not appear in the response
        expected_dict = {
            f"DataSets in '{PIPELINE_NAME}' pipeline": {
                "Datasets mentioned in pipeline": {
                    "CSVDataSet": ["iris_data"],
                    "MemoryDataSet": ["intermediate"],
                },
                "Datasets not mentioned in pipeline": {"CSVDataSet": ["not_used"]},
            }
        }
        key = f"DataSets in '{PIPELINE_NAME}' pipeline"
        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0][key] == expected_dict[key]

    def test_default_dataset(
        self, fake_cli_invoke, fake_load_context, mocker, mock_pipelines
    ):
        """Test that datasets that are found in `Pipeline.data_sets()`,
        but not in the catalog, are outputted under the key "DefaultDataset".
        """
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_data_sets = {"some_dataset": CSVDataSet("test.csv")}
        mocked_context.catalog = DataCatalog(data_sets=catalog_data_sets)
        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "data_sets",
            return_value=catalog_data_sets.keys() | {"intermediate"},
        )

        result = fake_cli_invoke(["catalog", "list"])

        assert not result.exit_code
        expected_dict = {
            f"DataSets in '{PIPELINE_NAME}' pipeline": {
                "Datasets mentioned in pipeline": {
                    "CSVDataSet": ["some_dataset"],
                    "DefaultDataSet": ["intermediate"],
                }
            }
        }
        key = f"DataSets in '{PIPELINE_NAME}' pipeline"
        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0][key] == expected_dict[key]


def identity(data):
    return data  # pragma: no cover


@pytest.mark.usefixtures("chdir_to_dummy_project", "patch_log")
class TestCatalogCreateCommand:
    PIPELINE_NAME = "de"

    @staticmethod
    @pytest.fixture(params=["base"])
    def catalog_path(request, fake_repo_path):
        catalog_path = fake_repo_path / "conf" / request.param / "catalog"

        yield catalog_path

        shutil.rmtree(catalog_path, ignore_errors=True)

    def test_pipeline_argument_is_required(self, fake_project_cli):
        result = CliRunner().invoke(fake_project_cli.cli, ["catalog", "create"])
        assert result.exit_code
        expected_output = "Error: Missing option '--pipeline'."
        assert expected_output in result.output

    @pytest.mark.usefixtures("fake_load_context")
    def test_not_found_pipeline(self, fake_cli_invoke, mock_pipelines):
        result = fake_cli_invoke(["catalog", "create", "--pipeline", "fake"])

        assert result.exit_code

        existing_pipelines = ", ".join(sorted(mock_pipelines.keys()))
        expected_output = (
            f"Error: `fake` pipeline not found! Existing "
            f"pipelines: {existing_pipelines}\n"
        )
        assert expected_output in result.output

    def test_catalog_is_created_in_base_by_default(
        self, fake_cli_invoke, fake_repo_path, catalog_path
    ):
        main_catalog_path = fake_repo_path / "conf" / "base" / "catalog.yml"
        main_catalog_config = yaml.safe_load(main_catalog_path.read_text())
        assert "example_iris_data" in main_catalog_config

        data_catalog_file = catalog_path / f"{self.PIPELINE_NAME}.yml"

        result = fake_cli_invoke(
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME]
        )

        assert not result.exit_code
        assert data_catalog_file.is_file()

        expected_catalog_config = {
            "example_test_x": {"type": "MemoryDataSet"},
            "example_test_y": {"type": "MemoryDataSet"},
            "example_train_x": {"type": "MemoryDataSet"},
            "example_train_y": {"type": "MemoryDataSet"},
        }
        catalog_config = yaml.safe_load(data_catalog_file.read_text())
        assert catalog_config == expected_catalog_config

    @pytest.mark.parametrize("catalog_path", ["local"], indirect=True)
    def test_catalog_is_created_in_correct_env(self, fake_cli_invoke, catalog_path):
        data_catalog_file = catalog_path / f"{self.PIPELINE_NAME}.yml"

        env = catalog_path.parent.name
        result = fake_cli_invoke(
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME, "--env", env]
        )

        assert not result.exit_code
        assert data_catalog_file.is_file()

    def test_no_missing_datasets(
        self, fake_cli_invoke, fake_load_context, fake_repo_path, mock_pipelines
    ):
        mocked_context = fake_load_context.return_value

        catalog_data_sets = {
            "input_data": CSVDataSet("test.csv"),
            "output_data": CSVDataSet("test2.csv"),
        }
        mocked_context.catalog = DataCatalog(data_sets=catalog_data_sets)
        mocked_context.project_path = fake_repo_path
        mock_pipelines[self.PIPELINE_NAME] = Pipeline(
            [node(identity, "input_data", "output_data")]
        )

        data_catalog_file = (
            fake_repo_path / "conf" / "base" / "catalog" / f"{self.PIPELINE_NAME}.yml"
        )

        result = fake_cli_invoke(
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME]
        )

        assert not result.exit_code
        assert not data_catalog_file.exists()

    @pytest.mark.usefixtures("fake_repo_path")
    def test_missing_datasets_appended(self, fake_cli_invoke, catalog_path):
        data_catalog_file = catalog_path / f"{self.PIPELINE_NAME}.yml"
        assert not catalog_path.exists()
        catalog_path.mkdir()

        catalog_config = {
            "example_test_x": {"type": "pandas.CSVDataSet", "filepath": "test.csv"}
        }
        with data_catalog_file.open(mode="w") as catalog_file:
            yaml.safe_dump(catalog_config, catalog_file, default_flow_style=False)

        result = fake_cli_invoke(
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME]
        )

        assert not result.exit_code

        expected_catalog_config = {
            "example_test_x": catalog_config["example_test_x"],
            "example_test_y": {"type": "MemoryDataSet"},
            "example_train_x": {"type": "MemoryDataSet"},
            "example_train_y": {"type": "MemoryDataSet"},
        }
        catalog_config = yaml.safe_load(data_catalog_file.read_text())
        assert catalog_config == expected_catalog_config

    def test_bad_env(self, fake_cli_invoke):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["catalog", "list", "-e", env, "--pipeline", PIPELINE_NAME]

        result = fake_cli_invoke(cmd)

        assert result.exit_code
        assert "Unable to instantiate Kedro session" in result.output
