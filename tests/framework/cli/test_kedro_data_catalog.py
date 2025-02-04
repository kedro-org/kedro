# TODO: move all tests to test_catalog.py after removing old catalog
import pytest
import yaml
from click.testing import CliRunner
from kedro_datasets.pandas import CSVDataset

from kedro.io import KedroDataCatalog, MemoryDataset
from kedro.pipeline import node
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


@pytest.fixture()
def fake_credentials_config(tmp_path):
    return {"db_connection": {"con": "foo"}}


@pytest.fixture
def fake_catalog_config():
    config = {
        "parquet_{factory_pattern}": {
            "type": "pandas.ParquetDataset",
            "filepath": "data/01_raw/{factory_pattern}.parquet",
            "credentials": "db_connection",
        },
        "csv_{factory_pattern}": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/{factory_pattern}.csv",
        },
        "csv_test": {"type": "pandas.CSVDataset", "filepath": "test.csv"},
    }
    return config


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
class TestCatalogListCommand:
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

    def test_default_dataset(
        self, fake_project_cli, fake_metadata, fake_load_context, mocker, mock_pipelines
    ):
        """Test that datasets that are found in `Pipeline.datasets()`,
        but not in the catalog, are outputted under the key "DefaultDataset".
        """
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_datasets = {"some_dataset": CSVDataset(filepath="test.csv")}
        mocked_context.catalog = KedroDataCatalog(datasets=catalog_datasets)
        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "datasets",
            return_value=catalog_datasets.keys() | {"intermediate"},
        )

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "list"],
            obj=fake_metadata,
        )

        assert not result.exit_code
        expected_dict = {
            f"Datasets in '{PIPELINE_NAME}' pipeline": {
                "Datasets mentioned in pipeline": {
                    "CSVDataset": ["some_dataset"],
                    "DefaultDataset": ["intermediate"],
                }
            }
        }
        key = f"Datasets in '{PIPELINE_NAME}' pipeline"
        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0][key] == expected_dict[key]

    def test_list_factory_generated_datasets(
        self,
        fake_project_cli,
        fake_metadata,
        fake_load_context,
        mocker,
        mock_pipelines,
        fake_catalog_config,
        fake_credentials_config,
    ):
        """Test that datasets generated from factory patterns in the catalog
        are resolved correctly under the correct dataset classes.
        """
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        mocked_context.catalog = KedroDataCatalog.from_config(
            catalog=fake_catalog_config, credentials=fake_credentials_config
        )
        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "datasets",
            return_value=mocked_context.catalog._datasets.keys()
            | {"csv_example", "parquet_example"},
        )

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "list"],
            obj=fake_metadata,
        )
        assert not result.exit_code
        expected_dict = {
            f"Datasets in '{PIPELINE_NAME}' pipeline": {
                "Datasets generated from factories": {
                    "pandas.CSVDataset": ["csv_example"],
                    "pandas.ParquetDataset": ["parquet_example"],
                },
                "Datasets mentioned in pipeline": {
                    "CSVDataset": ["csv_test"],
                },
            }
        }
        key = f"Datasets in '{PIPELINE_NAME}' pipeline"
        assert yaml_dump_mock.call_count == 1
        assert yaml_dump_mock.call_args[0][0][key] == expected_dict[key]


def identity(data):
    return data  # pragma: no cover


@pytest.mark.usefixtures("chdir_to_dummy_project")
class TestCatalogCreateCommand:
    PIPELINE_NAME = "data_engineering"

    def test_no_missing_datasets(
        self,
        fake_project_cli,
        fake_metadata,
        fake_load_context,
        fake_repo_path,
        mock_pipelines,
    ):
        mocked_context = fake_load_context.return_value

        catalog_datasets = {
            "input_data": CSVDataset(filepath="test.csv"),
            "output_data": CSVDataset(filepath="test2.csv"),
        }
        mocked_context.catalog = KedroDataCatalog(datasets=catalog_datasets)
        mocked_context.project_path = fake_repo_path
        mock_pipelines[self.PIPELINE_NAME] = modular_pipeline(
            [node(identity, "input_data", "output_data")]
        )

        data_catalog_file = (
            fake_repo_path / "conf" / "base" / f"catalog_{self.PIPELINE_NAME}.yml"
        )

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert not result.exit_code
        assert not data_catalog_file.exists()


@pytest.fixture
def fake_catalog_config_resolved():
    config = {
        "parquet_example": {
            "type": "pandas.ParquetDataset",
            "filepath": "data/01_raw/example.parquet",
            "credentials": {"con": "foo"},
        },
        "csv_example": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/example.csv",
        },
        "csv_test": {"type": "pandas.CSVDataset", "filepath": "test.csv"},
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

    def test_rank_catalog_factories_with_no_factories(
        self, fake_project_cli, fake_metadata, fake_load_context
    ):
        mocked_context = fake_load_context.return_value

        catalog_datasets = {
            "iris_data": CSVDataset(filepath="test.csv"),
            "intermediate": MemoryDataset(),
            "not_used": CSVDataset(filepath="test2.csv"),
        }
        mocked_context.catalog = KedroDataCatalog(datasets=catalog_datasets)

        result = CliRunner().invoke(
            fake_project_cli, ["catalog", "rank"], obj=fake_metadata
        )

        assert not result.exit_code
        expected_output = "There are no dataset factories in the catalog."
        assert expected_output in result.output

    @pytest.mark.usefixtures("mock_pipelines")
    def test_catalog_resolve(
        self,
        fake_project_cli,
        fake_metadata,
        fake_load_context,
        mocker,
        mock_pipelines,
        fake_catalog_config,
        fake_catalog_config_resolved,
        fake_credentials_config,
    ):
        """Test that datasets factories are correctly resolved to the explicit datasets in the pipeline."""
        mocked_context = fake_load_context.return_value
        mocked_context.config_loader = {
            "catalog": fake_catalog_config,
            "credentials": fake_credentials_config,
        }
        mocked_context._get_config_credentials.return_value = fake_credentials_config
        mocked_context.catalog = KedroDataCatalog.from_config(
            catalog=fake_catalog_config, credentials=fake_credentials_config
        )
        placeholder_ds = mocked_context.catalog.config_resolver.list_patterns()
        pipeline_datasets = {"csv_example", "parquet_example", "explicit_dataset"}

        mocker.patch.object(
            mock_pipelines[PIPELINE_NAME],
            "datasets",
            return_value=pipeline_datasets,
        )

        result = CliRunner().invoke(
            fake_project_cli, ["catalog", "resolve"], obj=fake_metadata
        )

        assert not result.exit_code
        resolved_config = yaml.safe_load(result.output)
        assert resolved_config == fake_catalog_config_resolved

        for ds in placeholder_ds:
            assert ds not in result.output
