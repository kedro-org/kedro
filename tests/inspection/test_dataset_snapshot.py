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

    def test_from_config(self):
        snapshot = DatasetSnapshot.from_config(
            "companies",
            {"type": "pandas.CSVDataset", "filepath": "data/01_raw/companies.csv"},
        )
        assert snapshot.name == "companies"
        assert snapshot.type == "pandas.CSVDataset"
        assert snapshot.filepath == "data/01_raw/companies.csv"

    def test_from_config_missing_defaults(self):
        snapshot = DatasetSnapshot.from_config("ds", {"filepath": "data.csv"})
        assert snapshot.type == ""

    def test_from_config_missing_filepath(self):
        snapshot = DatasetSnapshot.from_config("ds", {"type": "kedro.io.MemoryDataset"})
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

    def test_non_dict_entry_excluded(self):
        snapshots = _build_dataset_snapshots(
            {
                "companies": {"type": "pandas.CSVDataset", "filepath": "companies.csv"},
                "bad_entry": "some_string_value",
            }
        )
        assert "bad_entry" not in snapshots
        assert "companies" in snapshots

    def test_none_entry_excluded(self):
        snapshots = _build_dataset_snapshots(
            {
                "companies": {"type": "pandas.CSVDataset"},
                "null_entry": None,
            }
        )
        assert "null_entry" not in snapshots
        assert "companies" in snapshots


class TestDatasetSnapshotCredentialScrubbing:
    @pytest.mark.parametrize(
        "raw_filepath, expected",
        [
            (
                "s3://access_key:secret_key@my-bucket/data/file.csv",  # pragma: allowlist secret
                "s3://<redacted>@my-bucket/data/file.csv",
            ),
            (
                "postgresql://user:password@db-host:5432/mydb",  # pragma: allowlist secret
                "postgresql://<redacted>@db-host:5432/mydb",
            ),
            (
                "gs://svc_account:token123@bucket/path/file.parquet",  # pragma: allowlist secret
                "gs://<redacted>@bucket/path/file.parquet",
            ),
        ],
    )
    def test_from_config_scrubs_embedded_credentials(self, raw_filepath, expected):
        snapshot = DatasetSnapshot.from_config(
            "ds", {"type": "pandas.CSVDataset", "filepath": raw_filepath}
        )
        assert snapshot.filepath == expected

    def test_plain_filepath_is_unchanged(self):
        filepath = "data/01_raw/companies.csv"
        snapshot = DatasetSnapshot.from_config(
            "ds", {"type": "pandas.CSVDataset", "filepath": filepath}
        )
        assert snapshot.filepath == filepath

    def test_none_filepath_is_unchanged(self):
        snapshot = DatasetSnapshot.from_config("ds", {"type": "kedro.io.MemoryDataset"})
        assert snapshot.filepath is None
