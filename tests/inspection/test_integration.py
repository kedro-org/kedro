"""Integration tests for the inspection public API against a fake Kedro project.

The fixture ``fake_project`` creates a minimal project that mirrors the
structure of the spaceflights-pandas starter (two modular pipelines, a
three-dataset catalog, and a small parameters file) without requiring network
access or a real project installation.
"""

from __future__ import annotations

import dataclasses
import json

import pytest
import tomli_w
import yaml

from kedro import __version__ as kedro_version
from kedro.inspection import get_project_snapshot
from kedro.inspection.models import ProjectSnapshot

# ---------------------------------------------------------------------------
# Constants matching the fake project definition below
# ---------------------------------------------------------------------------

_PACKAGE_NAME = "test_spaceflights"
_PROJECT_NAME = "Spaceflights"

_CATALOG_DATASETS = {
    "companies": {
        "type": "pandas.CSVDataset",
        "filepath": "data/01_raw/companies.csv",
    },
    "preprocessed_companies": {
        "type": "pandas.CSVDataset",
        "filepath": "data/02_intermediate/preprocessed_companies.csv",
    },
    "model_input_table": {
        "type": "pandas.CSVDataset",
        "filepath": "data/03_primary/model_input_table.csv",
    },
}

_PARAMETERS = {
    "test_size": 0.2,
    "random_state": 3,
    "features": ["engines", "passenger_capacity"],
}


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def fake_project(tmp_path_factory):
    """Create a self-contained fake Kedro project in a temp directory.

    Structure mirrors the spaceflights-pandas starter:
      - two modular pipelines: ``data_processing`` and ``data_science``
      - three catalog entries in ``conf/base/catalog.yml``
      - three parameter keys in ``conf/base/parameters.yml``
    """
    project_path = tmp_path_factory.mktemp("spaceflights_project")

    # --- pyproject.toml ---------------------------------------------------
    with (project_path / "pyproject.toml").open("wb") as f:
        tomli_w.dump(
            {
                "tool": {
                    "kedro": {
                        "package_name": _PACKAGE_NAME,
                        "project_name": _PROJECT_NAME,
                        "kedro_init_version": kedro_version,
                    }
                }
            },
            f,
        )

    # --- Python package ---------------------------------------------------
    src = project_path / "src" / _PACKAGE_NAME
    src.mkdir(parents=True)
    (src / "__init__.py").write_text("")
    (src / "settings.py").write_text("")

    (src / "pipeline_registry.py").write_text(
        "from kedro.pipeline import Pipeline\n"
        "from kedro.pipeline.node import node\n"
        "\n"
        "\n"
        "def _identity(x):\n"
        "    return x\n"
        "\n"
        "\n"
        "def register_pipelines():\n"
        "    data_processing = Pipeline([\n"
        "        node(_identity, inputs='companies',\n"
        "             outputs='preprocessed_companies',\n"
        "             name='preprocess_companies_node'),\n"
        "        node(_identity, inputs='preprocessed_companies',\n"
        "             outputs='model_input_table',\n"
        "             name='create_model_input_node'),\n"
        "    ])\n"
        "    data_science = Pipeline([\n"
        "        node(_identity, inputs='model_input_table',\n"
        "             outputs='predictions',\n"
        "             name='train_model_node'),\n"
        "    ])\n"
        "    return {\n"
        "        '__default__': data_processing + data_science,\n"
        "        'data_processing': data_processing,\n"
        "        'data_science': data_science,\n"
        "    }\n"
    )

    # --- Configuration files ----------------------------------------------
    conf_base = project_path / "conf" / "base"
    conf_base.mkdir(parents=True)

    with (conf_base / "catalog.yml").open("w") as f:
        yaml.dump(_CATALOG_DATASETS, f)

    with (conf_base / "parameters.yml").open("w") as f:
        yaml.dump(_PARAMETERS, f)

    return project_path


@pytest.fixture(scope="module")
def snapshot(fake_project):
    """Full project snapshot (module-scoped to avoid repeated bootstrap cost)."""
    return get_project_snapshot(fake_project)


# ---------------------------------------------------------------------------
# TestGetProjectSnapshot
# ---------------------------------------------------------------------------


class TestGetProjectSnapshot:
    def test_returns_project_snapshot_instance(self, snapshot):
        assert isinstance(snapshot, ProjectSnapshot)

    def test_metadata_project_name(self, snapshot):
        assert snapshot.metadata.project_name == _PROJECT_NAME

    def test_metadata_package_name(self, snapshot):
        assert snapshot.metadata.package_name == _PACKAGE_NAME

    def test_metadata_kedro_version(self, snapshot):
        assert snapshot.metadata.kedro_version == kedro_version

    def test_all_pipelines_present(self, snapshot):
        pipeline_names = {p.name for p in snapshot.pipelines}
        assert {"__default__", "data_processing", "data_science"}.issubset(
            pipeline_names
        )

    def test_pipelines_have_nodes(self, snapshot):
        for pipeline in snapshot.pipelines:
            if pipeline.name != "__default__":
                assert (
                    len(pipeline.nodes) > 0
                ), f"Pipeline '{pipeline.name}' has no nodes"

    def test_catalog_datasets_present(self, snapshot):
        for ds_name in _CATALOG_DATASETS:
            assert ds_name in snapshot.datasets

    def test_dataset_type_correct(self, snapshot):
        assert snapshot.datasets["companies"].type == "pandas.CSVDataset"

    def test_dataset_filepath_correct(self, snapshot):
        assert snapshot.datasets["companies"].filepath == "data/01_raw/companies.csv"

    def test_parameters_contain_expected_keys(self, snapshot):
        for key in _PARAMETERS:
            assert key in snapshot.parameters

    def test_parameters_are_sorted(self, snapshot):
        assert snapshot.parameters == sorted(snapshot.parameters)

    def test_parameters_store_keys_only(self, snapshot):
        """Parameter values must not appear in the snapshot."""
        assert 0.2 not in snapshot.parameters
        assert 3 not in snapshot.parameters

    def test_json_serialisable(self, snapshot):
        raw = json.dumps(dataclasses.asdict(snapshot))
        parsed = json.loads(raw)
        assert "metadata" in parsed
        assert "pipelines" in parsed
        assert "datasets" in parsed
        assert "parameters" in parsed
