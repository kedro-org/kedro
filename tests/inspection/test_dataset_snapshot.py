"""Tests for DatasetSnapshot model and _build_catalog_snapshot builder."""

from __future__ import annotations

import dataclasses

import pytest
import yaml

from kedro.inspection.models import DatasetSnapshot
from kedro.inspection.snapshot import _build_catalog_snapshot


@pytest.fixture
def project_dir(tmp_path):
    """Create a minimal project directory with catalog and parameters config."""
    conf_base = tmp_path / "conf" / "base"
    conf_base.mkdir(parents=True)

    catalog = {
        "companies": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/companies.csv",
        },
        "reviews": {
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/reviews.csv",
        },
        "shuttles": {
            "type": "pandas.ExcelDataset",
            "filepath": "data/01_raw/shuttles.xlsx",
        },
    }
    (conf_base / "catalog.yml").write_text(yaml.dump(catalog))

    parameters = {
        "model_options": {
            "test_size": 0.2,
            "features": ["engine", "passenger_capacity"],
        },
        "train_fraction": 0.8,
    }
    (conf_base / "parameters.yml").write_text(yaml.dump(parameters))

    return tmp_path


class TestDatasetSnapshot:
    def test_construction(self):
        snapshot = DatasetSnapshot(
            name="companies",
            type="pandas.CSVDataset",
            filepath="data/01_raw/companies.csv",
        )
        assert snapshot.name == "companies"
        assert snapshot.type == "pandas.CSVDataset"
        assert snapshot.filepath == "data/01_raw/companies.csv"

    def test_filepath_default_none(self):
        snapshot = DatasetSnapshot(name="x", type="t")
        assert snapshot.filepath is None

    def test_dict_serialization(self):
        snapshot = DatasetSnapshot(
            name="companies",
            type="pandas.CSVDataset",
            filepath="data/01_raw/companies.csv",
        )
        result = dataclasses.asdict(snapshot)
        assert result == {
            "name": "companies",
            "type": "pandas.CSVDataset",
            "filepath": "data/01_raw/companies.csv",
        }


class TestBuildCatalogSnapshot:
    def test_datasets_populated(self, project_dir, mocker):
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        datasets, _ = _build_catalog_snapshot(project_dir, "base")
        assert set(datasets.keys()) == {"companies", "reviews", "shuttles"}

    def test_type_resolved_correctly(self, project_dir, mocker):
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        datasets, _ = _build_catalog_snapshot(project_dir, "base")
        assert datasets["companies"].type == "pandas.CSVDataset"
        assert datasets["shuttles"].type == "pandas.ExcelDataset"

    def test_filepath_resolved_correctly(self, project_dir, mocker):
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        datasets, _ = _build_catalog_snapshot(project_dir, "base")
        assert datasets["companies"].filepath == "data/01_raw/companies.csv"

    def test_parameter_keys_sorted_names_only(self, project_dir, mocker):
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        _, parameter_keys = _build_catalog_snapshot(project_dir, "base")
        assert parameter_keys == sorted(parameter_keys)
        assert "parameters" in parameter_keys
        assert "params:model_options" in parameter_keys
        assert "params:train_fraction" in parameter_keys
        assert "params:model_options.test_size" in parameter_keys
        assert "params:model_options.features" in parameter_keys
        # Values must never appear
        assert 0.2 not in parameter_keys
        assert 0.8 not in parameter_keys

    def test_empty_catalog(self, tmp_path, mocker):
        """Returns empty dict when catalog.yml is missing."""
        conf_base = tmp_path / "conf" / "base"
        conf_base.mkdir(parents=True)
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        datasets, _ = _build_catalog_snapshot(tmp_path, "base")
        assert datasets == {}

    def test_missing_parameters_graceful(self, tmp_path, mocker):
        """Returns empty parameter_keys list when parameters.yml is missing."""
        conf_base = tmp_path / "conf" / "base"
        conf_base.mkdir(parents=True)
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONF_SOURCE", "conf"
        )
        mocker.patch(
            "kedro.inspection.snapshot.settings.CONFIG_LOADER_ARGS",
            {"base_env": "base", "default_run_env": "local"},
        )
        _, parameter_keys = _build_catalog_snapshot(tmp_path, "base")
        assert parameter_keys == []
