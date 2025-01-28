# TODO: rename to test_catalog.py after removing old catalog
import pytest
from click.testing import CliRunner

from kedro.io import KedroDataCatalog
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
