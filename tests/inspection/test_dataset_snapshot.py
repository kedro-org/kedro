"""Tests for DatasetSnapshot model and _build_catalog_snapshot builder."""

from __future__ import annotations

import pytest
import yaml

from kedro.config import MissingConfigException
from kedro.inspection import snapshot as inspection_snapshot
from kedro.inspection.models import DatasetSnapshot
from kedro.inspection.snapshot import _build_catalog_snapshot, _is_parameter


@pytest.fixture
def configured_inspection_settings(monkeypatch):
    monkeypatch.setattr(inspection_snapshot.settings, "CONF_SOURCE", "conf")
    monkeypatch.setattr(
        inspection_snapshot.settings,
        "CONFIG_LOADER_ARGS",
        {"base_env": "base", "default_run_env": "local"},
    )


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
    (conf_base / "catalog.yml").write_text(yaml.safe_dump(catalog))

    parameters = {
        "model_options": {
            "test_size": 0.2,
            "features": ["engine", "passenger_capacity"],
        },
        "train_fraction": 0.8,
    }
    (conf_base / "parameters.yml").write_text(yaml.safe_dump(parameters))

    return tmp_path


@pytest.fixture
def empty_project_dir(tmp_path):
    conf_base = tmp_path / "conf" / "base"
    conf_base.mkdir(parents=True)
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


class TestIsParameter:
    def test_identifies_parameter_names(self):
        assert _is_parameter("parameters")
        assert _is_parameter("params:model_options")
        assert not _is_parameter("companies")


@pytest.mark.usefixtures("configured_inspection_settings")
class TestBuildCatalogSnapshot:
    def test_datasets_populated(self, project_dir):
        datasets, _ = _build_catalog_snapshot(project_dir, "base")
        assert set(datasets.keys()) == {"companies", "reviews", "shuttles"}
        assert isinstance(datasets["companies"], DatasetSnapshot)
        assert datasets["companies"].type == "pandas.CSVDataset"
        assert datasets["shuttles"].type == "pandas.ExcelDataset"
        assert datasets["companies"].filepath == "data/01_raw/companies.csv"

    def test_parameter_keys_sorted_names_only(self, project_dir):
        _, parameter_keys = _build_catalog_snapshot(project_dir, "base")
        assert parameter_keys == [
            "parameters",
            "params:model_options",
            "params:model_options.features",
            "params:model_options.test_size",
            "params:train_fraction",
        ]

    def test_empty_catalog(self, empty_project_dir):
        """Returns empty dict when catalog.yml is missing."""
        datasets, _ = _build_catalog_snapshot(empty_project_dir, "base")
        assert datasets == {}

    def test_missing_parameters_graceful(self, empty_project_dir):
        """Returns empty parameter_keys list when parameters.yml is missing."""
        _, parameter_keys = _build_catalog_snapshot(empty_project_dir, "base")
        assert parameter_keys == []

    def test_factory_patterns_are_excluded_from_dataset_snapshots(self, tmp_path):
        conf_base = tmp_path / "conf" / "base"
        conf_base.mkdir(parents=True)
        catalog = {
            "{namespace}.int_{name}": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/{name}.csv",
            },
            "companies": {
                "type": "pandas.CSVDataset",
                "filepath": "data/01_raw/companies.csv",
            },
        }
        (conf_base / "catalog.yml").write_text(yaml.safe_dump(catalog))

        datasets, _ = _build_catalog_snapshot(tmp_path, "base")

        assert set(datasets) == {"companies"}

    def test_missing_config_sections_are_handled_gracefully(self, tmp_path, mocker):
        config_loader = mocker.MagicMock()

        def _get_config_value(key):
            if key == "catalog":
                raise KeyError("catalog")
            if key in {"credentials", "parameters"}:
                raise MissingConfigException(key)
            return {}

        config_loader.__getitem__.side_effect = _get_config_value
        mocker.patch(
            "kedro.inspection.snapshot._make_config_loader",
            return_value=config_loader,
        )

        datasets, parameter_keys = _build_catalog_snapshot(tmp_path, "base")

        assert datasets == {}
        assert parameter_keys == []
