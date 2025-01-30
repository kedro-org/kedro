# TODO: rename to test_catalog.py after removing old catalog
import pytest
from click.testing import CliRunner
from kedro_datasets.pandas import CSVDataset

from kedro.io import KedroDataCatalog, MemoryDataset
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline

PIPELINE_NAME = "pipeline"


@pytest.fixture
def fake_load_context(mocker):
    context = mocker.MagicMock()
    return mocker.patch(
        "kedro.framework.session.KedroSession.load_context", return_value=context
    )


@pytest.fixture
def mock_pipelines(mocker):
    dummy_pipelines = {
        PIPELINE_NAME: modular_pipeline([]),
        "second": modular_pipeline([]),
    }
    return mocker.patch("kedro.framework.cli.catalog.pipelines", dummy_pipelines)


@pytest.fixture
def fake_catalog_with_overlapping_factories():
    config = {
        "an_example_dataset": {
            "type": "pandas.CSVDataset",
            "filepath": "dummy_filepath",
        },
        "an_example_{placeholder}": {
            "type": "dummy_type",
            "filepath": "dummy_filepath",
        },
        "an_example_{place}_{holder}": {
            "type": "dummy_type",
            "filepath": "dummy_filepath",
        },
        "on_{example_placeholder}": {
            "type": "dummy_type",
            "filepath": "dummy_filepath",
        },
        "an_{example_placeholder}": {
            "type": "dummy_type",
            "filepath": "dummy_filepath",
        },
    }
    return config


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
class TestCatalogListCommand:
    def test_list_all_pipelines(self, fake_project_cli, fake_metadata, mocker):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")

        result = CliRunner().invoke(
            fake_project_cli, ["catalog", "list"], obj=fake_metadata
        )

        assert not result.exit_code
        expected_dict = {
            "Datasets in 'pipeline' pipeline": {},
            "Datasets in 'second' pipeline": {},
        }
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_list_specific_pipelines(self, fake_project_cli, fake_metadata, mocker):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "list", "--pipeline", PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {f"Datasets in '{PIPELINE_NAME}' pipeline": {}}
        yaml_dump_mock.assert_called_once_with(expected_dict)

    def test_no_param_datasets_in_respose(
        self, fake_project_cli, fake_metadata, fake_load_context, mocker, mock_pipelines
    ):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_datasets = {
            "iris_data": CSVDataset(filepath="test.csv"),
            "intermediate": MemoryDataset(),
            "parameters": MemoryDataset(),
            "params:data_ratio": MemoryDataset(),
            "not_used": CSVDataset(filepath="test2.csv"),
        }

        mocked_context.catalog = KedroDataCatalog(datasets=catalog_datasets)
        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "datasets",
            return_value=catalog_datasets.keys() - {"not_used"},
        )

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "list"],
            obj=fake_metadata,
        )

        assert not result.exit_code
        # 'parameters' and 'params:data_ratio' should not appear in the response
        expected_dict = {
            f"Datasets in '{PIPELINE_NAME}' pipeline": {
                "Datasets mentioned in pipeline": {
                    "CSVDataset": ["iris_data"],
                    "MemoryDataset": ["intermediate"],
                },
                "Datasets not mentioned in pipeline": {"CSVDataset": ["not_used"]},
            }
        }
        key = f"Datasets in '{PIPELINE_NAME}' pipeline"
        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0][key] == expected_dict[key]


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestCatalogCreateCommand:
    def test_pipeline_argument_is_required(self, fake_project_cli):
        result = CliRunner().invoke(fake_project_cli, ["catalog", "create"])
        assert result.exit_code
        expected_output = "Error: Missing option '--pipeline' / '-p'."
        assert expected_output in result.output


@pytest.mark.usefixtures("chdir_to_dummy_project", "fake_load_context")
class TestCatalogFactoryCommands:
    @pytest.mark.usefixtures("mock_pipelines")
    def test_rank_catalog_factories(
        self,
        fake_project_cli,
        fake_metadata,
        mocker,
        fake_load_context,
        fake_catalog_with_overlapping_factories,
    ):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        mocked_context.catalog = KedroDataCatalog.from_config(
            fake_catalog_with_overlapping_factories
        )
        result = CliRunner().invoke(
            fake_project_cli, ["catalog", "rank"], obj=fake_metadata
        )
        assert not result.exit_code

        expected_patterns_sorted = [
            "an_example_{place}_{holder}",
            "an_example_{placeholder}",
            "an_{example_placeholder}",
            "on_{example_placeholder}",
        ]

        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0] == expected_patterns_sorted
