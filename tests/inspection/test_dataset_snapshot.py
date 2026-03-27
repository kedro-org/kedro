"""Tests for DatasetSnapshot model and _build_dataset_snapshots builder."""

from __future__ import annotations

import pytest

from kedro.inspection.models import DatasetSnapshot
from kedro.inspection.snapshot import _build_dataset_snapshots


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
    def test_datasets_populated(self, catalog_config):
        snapshots = _build_dataset_snapshots(catalog_config)
        assert set(snapshots.keys()) == {"companies", "shuttles"}

    def test_returns_dataset_snapshot_instances(self, catalog_config):
        snapshots = _build_dataset_snapshots(catalog_config)
        assert all(isinstance(s, DatasetSnapshot) for s in snapshots.values())

    def test_type_and_filepath_correct(self, catalog_config):
        snapshots = _build_dataset_snapshots(catalog_config)
        assert snapshots["companies"].type == "pandas.CSVDataset"
        assert snapshots["companies"].filepath == "data/01_raw/companies.csv"
        assert snapshots["shuttles"].type == "pandas.ExcelDataset"

    def test_missing_type_defaults_to_empty_string(self):
        snapshots = _build_dataset_snapshots({"memory_ds": {"filepath": "data.csv"}})
        assert snapshots["memory_ds"].type == ""

    def test_missing_filepath_defaults_to_none(self):
        snapshots = _build_dataset_snapshots(
            {"memory_ds": {"type": "kedro.io.MemoryDataset"}}
        )
        assert snapshots["memory_ds"].filepath is None

    def test_empty_catalog_returns_empty_dict(self):
        assert _build_dataset_snapshots({}) == {}

    def test_yaml_interpolation_anchors_excluded(self):
        snapshots = _build_dataset_snapshots(
            {
                "_csv_default": {"type": "pandas.CSVDataset"},
                "companies": {"type": "pandas.CSVDataset", "filepath": "companies.csv"},
            }
        )
        assert "_csv_default" not in snapshots
        assert "companies" in snapshots

    def test_factory_patterns_included(self):
        snapshots = _build_dataset_snapshots(
            {
                "{namespace}.{name}": {
                    "type": "pandas.CSVDataset",
                    "filepath": "data/{name}.csv",
                },
                "companies": {"type": "pandas.CSVDataset", "filepath": "companies.csv"},
            }
        )
        assert "{namespace}.{name}" in snapshots
        assert snapshots["{namespace}.{name}"].type == "pandas.CSVDataset"
