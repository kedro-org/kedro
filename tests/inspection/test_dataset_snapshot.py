"""Tests for DatasetSnapshot model and _build_dataset_snapshots builder."""

from __future__ import annotations

import pytest

from kedro.config import MissingConfigException
from kedro.inspection.models import DatasetSnapshot
from kedro.inspection.snapshot import _build_dataset_snapshots


@pytest.fixture
def config_loader(mocker):
    return mocker.MagicMock()


@pytest.fixture
def catalog_config():
    return {
        "companies": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/companies.csv",
        },
        "shuttles": {
            "type": "pandas.ExcelDataset",
            "filepath": "data/01_raw/shuttles.xlsx",
        },
    }


class TestDatasetSnapshot:
    def test_instantiation(self):
        snapshot = DatasetSnapshot(
            name="companies",
            type="pandas.CSVDataset",
            filepath="data/01_raw/companies.csv",
        )
        assert snapshot.name == "companies"
        assert snapshot.type == "pandas.CSVDataset"
        assert snapshot.filepath == "data/01_raw/companies.csv"

    def test_filepath_defaults_to_none(self):
        snapshot = DatasetSnapshot(name="x", type="kedro.io.MemoryDataset")
        assert snapshot.filepath is None


class TestBuildDatasetSnapshots:
    def test_datasets_populated(self, config_loader, catalog_config):
        config_loader.__getitem__.return_value = catalog_config
        snapshots = _build_dataset_snapshots(config_loader)
        assert set(snapshots.keys()) == {"companies", "shuttles"}

    def test_returns_dataset_snapshot_instances(self, config_loader, catalog_config):
        config_loader.__getitem__.return_value = catalog_config
        snapshots = _build_dataset_snapshots(config_loader)
        assert all(isinstance(s, DatasetSnapshot) for s in snapshots.values())

    def test_type_and_filepath_correct(self, config_loader, catalog_config):
        config_loader.__getitem__.return_value = catalog_config
        snapshots = _build_dataset_snapshots(config_loader)
        assert snapshots["companies"].type == "pandas.CSVDataset"
        assert snapshots["companies"].filepath == "data/01_raw/companies.csv"
        assert snapshots["shuttles"].type == "pandas.ExcelDataset"

    def test_missing_type_defaults_to_empty_string(self, config_loader):
        config_loader.__getitem__.return_value = {
            "memory_ds": {"filepath": "data.csv"},
        }
        snapshots = _build_dataset_snapshots(config_loader)
        assert snapshots["memory_ds"].type == ""

    def test_missing_filepath_defaults_to_none(self, config_loader):
        config_loader.__getitem__.return_value = {
            "memory_ds": {"type": "kedro.io.MemoryDataset"},
        }
        snapshots = _build_dataset_snapshots(config_loader)
        assert snapshots["memory_ds"].filepath is None

    def test_empty_catalog_on_key_error(self, config_loader):
        config_loader.__getitem__.side_effect = KeyError("catalog")
        assert _build_dataset_snapshots(config_loader) == {}

    def test_empty_catalog_on_missing_config(self, config_loader):
        config_loader.__getitem__.side_effect = MissingConfigException("catalog")
        assert _build_dataset_snapshots(config_loader) == {}

    def test_yaml_interpolation_anchors_excluded(self, config_loader):
        config_loader.__getitem__.return_value = {
            "_csv_default": {"type": "pandas.CSVDataset"},
            "companies": {"type": "pandas.CSVDataset", "filepath": "companies.csv"},
        }
        snapshots = _build_dataset_snapshots(config_loader)
        assert "_csv_default" not in snapshots
        assert "companies" in snapshots

    def test_factory_patterns_included(self, config_loader):
        config_loader.__getitem__.return_value = {
            "{namespace}.{name}": {
                "type": "pandas.CSVDataset",
                "filepath": "data/{name}.csv",
            },
            "companies": {"type": "pandas.CSVDataset", "filepath": "companies.csv"},
        }
        snapshots = _build_dataset_snapshots(config_loader)
        assert "{namespace}.{name}" in snapshots
        assert snapshots["{namespace}.{name}"].type == "pandas.CSVDataset"
