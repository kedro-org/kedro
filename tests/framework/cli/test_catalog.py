import pytest
import yaml
from click.testing import CliRunner
from kedro_datasets.pandas import CSVDataset

from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline


@pytest.fixture
def fake_load_context(mocker):
    context = mocker.MagicMock()
    return mocker.patch(
        "kedro.framework.session.KedroSession.load_context", return_value=context
    )


PIPELINE_NAME = "pipeline"


@pytest.fixture
def mock_pipelines(mocker):
    dummy_pipelines = {
        PIPELINE_NAME: modular_pipeline([]),
        "second": modular_pipeline([]),
    }
    return mocker.patch("kedro.framework.cli.catalog.pipelines", dummy_pipelines)


@pytest.fixture
def fake_catalog_config():
    config = {
        "parquet_{factory_pattern}": {
            "type": "pandas.ParquetDataset",
            "filepath": "test.pq",
        },
        "csv_{factory_pattern}": {"type": "pandas.CSVDataset", "filepath": "test.csv"},
    }
    return config


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


@pytest.fixture
def fake_catalog_config_with_resolvable_dataset():
    config = {
        "parquet_{factory_pattern}": {
            "type": "pandas.ParquetDataset",
            "filepath": "test.pq",
        },
        "csv_{factory_pattern}": {"type": "pandas.CSVDataset", "filepath": "test.csv"},
        "explicit_ds": {"type": "pandas.CSVDataset", "filepath": "test.csv"},
        "{factory_pattern}_ds": {
            "type": "pandas.ParquetDataset",
            "filepath": "test.pq",
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

    def test_not_found_pipeline(self, fake_project_cli, fake_metadata):
        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "list", "--pipeline", "fake"],
            obj=fake_metadata,
        )

        assert result.exit_code
        expected_output = (
            "Error: 'fake' pipeline not found! Existing pipelines: pipeline, second"
        )
        assert expected_output in result.output

    def test_no_param_datasets_in_respose(
        self, fake_project_cli, fake_metadata, fake_load_context, mocker, mock_pipelines
    ):
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        catalog_datasets = {
            "iris_data": CSVDataset("test.csv"),
            "intermediate": MemoryDataset(),
            "parameters": MemoryDataset(),
            "params:data_ratio": MemoryDataset(),
            "not_used": CSVDataset("test2.csv"),
        }

        mocked_context.catalog = DataCatalog(datasets=catalog_datasets)
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
        catalog_datasets = {"some_dataset": CSVDataset("test.csv")}
        mocked_context.catalog = DataCatalog(datasets=catalog_datasets)
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
    ):
        """Test that datasets generated from factory patterns in the catalog
        are resolved correctly under the correct dataset classes.
        """
        yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
        mocked_context = fake_load_context.return_value
        mocked_context.catalog = DataCatalog.from_config(fake_catalog_config)
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
                }
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

    @staticmethod
    @pytest.fixture(params=["base"])
    def catalog_path(request, fake_repo_path):
        catalog_path = fake_repo_path / "conf" / request.param

        yield catalog_path

        for file in catalog_path.glob("catalog_*"):
            file.unlink()

    def test_pipeline_argument_is_required(self, fake_project_cli):
        result = CliRunner().invoke(fake_project_cli, ["catalog", "create"])
        assert result.exit_code
        expected_output = "Error: Missing option '--pipeline' / '-p'."
        assert expected_output in result.output

    @pytest.mark.usefixtures("fake_load_context")
    def test_not_found_pipeline(self, fake_project_cli, fake_metadata, mock_pipelines):
        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "create", "--pipeline", "fake"],
            obj=fake_metadata,
        )

        assert result.exit_code

        existing_pipelines = ", ".join(sorted(mock_pipelines.keys()))
        expected_output = (
            f"Error: 'fake' pipeline not found! Existing "
            f"pipelines: {existing_pipelines}\n"
        )
        assert expected_output in result.output

    def test_catalog_is_created_in_base_by_default(
        self, fake_project_cli, fake_metadata, fake_repo_path, catalog_path
    ):
        main_catalog_path = fake_repo_path / "conf" / "base" / "catalog.yml"
        main_catalog_config = yaml.safe_load(main_catalog_path.read_text())
        assert "example_iris_data" in main_catalog_config

        data_catalog_file = catalog_path / f"catalog_{self.PIPELINE_NAME}.yml"

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert not result.exit_code
        assert data_catalog_file.is_file()

        expected_catalog_config = {
            "example_test_x": {"type": "MemoryDataset"},
            "example_test_y": {"type": "MemoryDataset"},
            "example_train_x": {"type": "MemoryDataset"},
            "example_train_y": {"type": "MemoryDataset"},
        }
        catalog_config = yaml.safe_load(data_catalog_file.read_text())
        assert catalog_config == expected_catalog_config

    @pytest.mark.parametrize("catalog_path", ["local"], indirect=True)
    def test_catalog_is_created_in_correct_env(
        self, fake_project_cli, fake_metadata, catalog_path
    ):
        data_catalog_file = catalog_path / f"catalog_{self.PIPELINE_NAME}.yml"

        env = catalog_path.name
        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME, "--env", env],
            obj=fake_metadata,
        )

        assert not result.exit_code
        assert data_catalog_file.is_file()

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
            "input_data": CSVDataset("test.csv"),
            "output_data": CSVDataset("test2.csv"),
        }
        mocked_context.catalog = DataCatalog(datasets=catalog_datasets)
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

    @pytest.mark.usefixtures("fake_repo_path")
    def test_missing_datasets_appended(
        self, fake_project_cli, fake_metadata, catalog_path
    ):
        data_catalog_file = catalog_path / f"catalog_{self.PIPELINE_NAME}.yml"

        catalog_config = {
            "example_test_x": {"type": "pandas.CSVDataset", "filepath": "test.csv"}
        }
        with data_catalog_file.open(mode="w") as catalog_file:
            yaml.safe_dump(catalog_config, catalog_file, default_flow_style=False)

        result = CliRunner().invoke(
            fake_project_cli,
            ["catalog", "create", "--pipeline", self.PIPELINE_NAME],
            obj=fake_metadata,
        )

        assert not result.exit_code

        expected_catalog_config = {
            "example_test_x": catalog_config["example_test_x"],
            "example_test_y": {"type": "MemoryDataset"},
            "example_train_x": {"type": "MemoryDataset"},
            "example_train_y": {"type": "MemoryDataset"},
        }
        catalog_config = yaml.safe_load(data_catalog_file.read_text())
        assert catalog_config == expected_catalog_config

    def test_bad_env(self, fake_project_cli, fake_metadata):
        """Test error when provided conf environment does not exist"""
        env = "no_such_env"
        cmd = ["catalog", "list", "-e", env, "--pipeline", PIPELINE_NAME]

        result = CliRunner().invoke(fake_project_cli, cmd, obj=fake_metadata)

        assert result.exit_code
        assert "Unable to instantiate Kedro Catalog" in result.output


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
def test_rank_catalog_factories(
    fake_project_cli,
    fake_metadata,
    mocker,
    fake_load_context,
    fake_catalog_with_overlapping_factories,
):
    yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
    mocked_context = fake_load_context.return_value
    mocked_context.catalog = DataCatalog.from_config(
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


@pytest.mark.usefixtures(
    "chdir_to_dummy_project",
    "fake_load_context",
)
def test_rank_catalog_factories_with_no_factories(
    fake_project_cli, fake_metadata, fake_load_context
):
    mocked_context = fake_load_context.return_value

    catalog_datasets = {
        "iris_data": CSVDataset("test.csv"),
        "intermediate": MemoryDataset(),
        "not_used": CSVDataset("test2.csv"),
    }
    mocked_context.catalog = DataCatalog(datasets=catalog_datasets)

    result = CliRunner().invoke(
        fake_project_cli, ["catalog", "rank"], obj=fake_metadata
    )

    assert not result.exit_code
    expected_output = "There are no dataset factories in the catalog."
    assert expected_output in result.output


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
def test_catalog_resolve(
    fake_project_cli,
    fake_metadata,
    fake_load_context,
    mocker,
    mock_pipelines,
    fake_catalog_config,
):
    """Test that datasets factories are correctly resolved to the explicit datasets in the pipeline."""
    yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
    mocked_context = fake_load_context.return_value
    mocked_context.catalog = DataCatalog.from_config(fake_catalog_config)

    placeholder_ds = mocked_context.catalog._datasets.keys()
    explicit_ds = {"csv_example", "parquet_example"}

    mocker.patch.object(
        mock_pipelines[PIPELINE_NAME],
        "datasets",
        return_value=explicit_ds,
    )

    result = CliRunner().invoke(
        fake_project_cli, ["catalog", "resolve"], obj=fake_metadata
    )

    assert not result.exit_code
    assert yaml_dump_mock.call_count == 1

    output = yaml_dump_mock.call_args[0][0]

    for ds in placeholder_ds:
        assert ds not in output

    for ds in explicit_ds:
        assert ds in output


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
def test_no_overwrite(
    fake_project_cli,
    fake_metadata,
    fake_load_context,
    mocker,
    mock_pipelines,
    fake_catalog_config_with_resolvable_dataset,
):
    """Test that explicit catalog entries are not overwritten by factory config."""
    yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
    mocked_context = fake_load_context.return_value

    mocked_context.config_loader = {
        "catalog": fake_catalog_config_with_resolvable_dataset
    }
    mocked_context.catalog = DataCatalog.from_config(
        fake_catalog_config_with_resolvable_dataset
    )

    mocker.patch.object(
        mock_pipelines[PIPELINE_NAME],
        "datasets",
        return_value=mocked_context.catalog._datasets.keys()
        | {"csv_example", "parquet_example"},
    )

    result = CliRunner().invoke(
        fake_project_cli, ["catalog", "resolve"], obj=fake_metadata
    )

    assert not result.exit_code
    assert yaml_dump_mock.call_count == 1

    assert (
        yaml_dump_mock.call_args[0][0]["explicit_ds"]
        == fake_catalog_config_with_resolvable_dataset["explicit_ds"]
    )


@pytest.mark.usefixtures(
    "chdir_to_dummy_project", "fake_load_context", "mock_pipelines"
)
def test_no_param_datasets_in_resolve(
    fake_project_cli, fake_metadata, fake_load_context, mocker, mock_pipelines
):

    yaml_dump_mock = mocker.patch("yaml.dump", return_value="Result YAML")
    mocked_context = fake_load_context.return_value

    catalog_config = {
        "iris_data": {
            "type": "pandas.CSVDataset",
            "filepath": "test.csv",
        },
        "intermediate": {"type": "MemoryDataset"},
    }

    catalog_datasets = {
        "iris_data": CSVDataset("test.csv"),
        "intermediate": MemoryDataset(),
        "parameters": MemoryDataset(),
        "params:data_ratio": MemoryDataset(),
    }

    mocked_context.config_loader = {"catalog": catalog_config}
    mocked_context.catalog = DataCatalog(datasets=catalog_datasets)

    mocker.patch.object(
        mock_pipelines[PIPELINE_NAME],
        "datasets",
        return_value=catalog_datasets.keys(),
    )

    result = CliRunner().invoke(
        fake_project_cli,
        ["catalog", "resolve"],
        obj=fake_metadata,
    )

    assert not result.exit_code
    assert yaml_dump_mock.call_count == 1

    # 'parameters' and 'params:data_ratio' should not appear in the output
    output = yaml_dump_mock.call_args[0][0]

    assert "parameters" not in output.keys()
    assert "params:data_ratio" not in output.keys()
    assert "iris_data" in output.keys()
    assert "intermediate" in output.keys()
