import pytest

from kedro.framework.context.catalog_mixins import CatalogCommandsMixin
from kedro.framework.context.context import compose_classes
from kedro.io import DataCatalog
from kedro.io.memory_dataset import MemoryDataset
from kedro.pipeline import Node, Pipeline


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


@pytest.fixture
def expected_fake_config_list_datasets_output():
    return {
        "datasets": {"kedro_datasets.pandas.csv_dataset.CSVDataset": ["csv_test"]},
        "factories": {
            "kedro_datasets.pandas.csv_dataset.CSVDataset": ["csv_example"],
            "kedro_datasets.pandas.parquet_dataset.ParquetDataset": ["parquet_example"],
        },
        "defaults": {"kedro.io.MemoryDataset": ["memory_output"]},
    }


@pytest.fixture
def fake_catalog_config_resolved():
    config = {
        "csv_test": {
            "type": "kedro_datasets.pandas.csv_dataset.CSVDataset",
            "filepath": "test.csv",
            "load_args": None,
            "save_args": None,
            "credentials": None,
            "fs_args": None,
        },
        "memory_output": {"type": "kedro.io.MemoryDataset"},
        "parquet_example": {
            "type": "pandas.ParquetDataset",
            "filepath": "data/01_raw/example.parquet",
            "credentials": "parquet_example_credentials",
        },
        "csv_example": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/example.csv",
        },
    }
    return config


@pytest.fixture
def fake_pipeline():
    return Pipeline(
        [
            Node(
                func=lambda x: x,
                inputs="csv_example",
                outputs=["parquet_example", "params:fake_param"],
                name="node1",
            ),
            Node(
                func=lambda x: x,
                inputs="parquet_example",
                outputs="csv_test",
                name="node2",
            ),
            Node(
                func=lambda x: x,
                inputs="csv_test",
                outputs="memory_output",
                name="node3",
            ),
        ]
    )


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
def DataCatalogWithFactories(fake_catalog_config, fake_credentials_config):
    """
    Fixture to create a DataCatalog with factories.
    """
    catalog_class = compose_classes(DataCatalog, CatalogCommandsMixin)

    catalog = catalog_class.from_config(
        catalog=fake_catalog_config,
        credentials=fake_credentials_config,
        load_versions=None,
        save_version=None,
    )
    # Add parameter
    catalog["params:fake_param"] = MemoryDataset(2)
    return catalog


@pytest.fixture
def DataCatalogWithOverlappingFactories(fake_catalog_with_overlapping_factories):
    """
    Fixture to create a DataCatalog with overlapping factories.
    """
    catalog_class = compose_classes(DataCatalog, CatalogCommandsMixin)

    catalog = catalog_class.from_config(
        catalog=fake_catalog_with_overlapping_factories,
        credentials={},
        load_versions=None,
        save_version=None,
    )
    return catalog


class TestCatalogCommands:
    def test_list_datasets(
        self,
        DataCatalogWithFactories,
        fake_pipeline,
        expected_fake_config_list_datasets_output,
    ):
        catalog = DataCatalogWithFactories
        result = catalog.list_datasets(pipelines=fake_pipeline)["pipeline_0"]
        assert result == expected_fake_config_list_datasets_output

    def test_list_patterns(self, DataCatalogWithFactories):
        catalog = DataCatalogWithFactories
        patterns = catalog.list_patterns()
        expected_patterns = {
            "parquet_{factory_pattern}",
            "csv_{factory_pattern}",
            "{default}",
        }
        assert set(patterns) == expected_patterns

    def test_resolve_patterns(
        self, DataCatalogWithFactories, fake_pipeline, fake_catalog_config_resolved
    ):
        catalog = DataCatalogWithFactories
        resolved_patterns = catalog.resolve_patterns(pipelines=[fake_pipeline])
        assert resolved_patterns == fake_catalog_config_resolved

    def test_patterns_order(self, DataCatalogWithOverlappingFactories):
        catalog = DataCatalogWithOverlappingFactories
        # Ordered list of expected patterns
        expected_patterns_list = [
            "an_example_{place}_{holder}",
            "an_example_{placeholder}",
            "an_{example_placeholder}",
            "on_{example_placeholder}",
            "{default}",
        ]
        pattern_list = catalog.list_patterns()
        assert pattern_list == expected_patterns_list
