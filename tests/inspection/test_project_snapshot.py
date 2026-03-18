"""Tests for ProjectSnapshot model and _build_project_snapshot orchestrator."""

from __future__ import annotations

import pytest

from kedro.framework.startup import ProjectMetadata
from kedro.inspection.models import (
    DatasetSnapshot,
    NodeSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)
from kedro.inspection.snapshot import _build_project_snapshot


@pytest.fixture
def project_metadata(tmp_path):
    return ProjectMetadata(
        config_file=tmp_path / "pyproject.toml",
        package_name="my_package",
        project_name="My Project",
        project_path=tmp_path,
        source_dir=tmp_path / "src",
        kedro_init_version="1.2.0",
        tools=None,
        example_pipeline=None,
    )


@pytest.fixture
def metadata_snapshot():
    return ProjectMetadataSnapshot(
        project_name="My Project",
        package_name="my_package",
        kedro_version="1.2.0",
    )


@pytest.fixture
def node_snapshot():
    return NodeSnapshot(
        name="node_a",
        inputs=["companies"],
        outputs=["processed_companies"],
    )


@pytest.fixture
def pipeline_snapshot(node_snapshot):
    return PipelineSnapshot(
        name="__default__",
        nodes=[node_snapshot],
        inputs=["companies"],
        outputs=["processed_companies"],
    )


@pytest.fixture
def dataset_snapshots():
    return {
        "companies": DatasetSnapshot(
            name="companies",
            type="pandas.CSVDataset",
            filepath="data/01_raw/companies.csv",
        ),
        "processed_companies": DatasetSnapshot(
            name="processed_companies",
            type="pandas.CSVDataset",
            filepath="data/02_intermediate/processed_companies.csv",
        ),
    }


class TestProjectSnapshot:
    def test_instantiation(
        self, metadata_snapshot, pipeline_snapshot, dataset_snapshots
    ):
        snapshot = ProjectSnapshot(
            metadata=metadata_snapshot,
            pipelines=[pipeline_snapshot],
            datasets=dataset_snapshots,
            parameters=["model_options", "test_size"],
        )
        assert snapshot.metadata is metadata_snapshot
        assert snapshot.pipelines == [pipeline_snapshot]
        assert snapshot.datasets is dataset_snapshots
        assert snapshot.parameters == ["model_options", "test_size"]

    def test_empty_collections(self, metadata_snapshot):
        snapshot = ProjectSnapshot(
            metadata=metadata_snapshot,
            pipelines=[],
            datasets={},
            parameters=[],
        )
        assert snapshot.pipelines == []
        assert snapshot.datasets == {}
        assert snapshot.parameters == []


class TestBuildProjectSnapshot:
    """Tests for _build_project_snapshot using fully mocked sub-components."""

    @pytest.fixture(autouse=True)
    def _patch_orchestrator(
        self, mocker, tmp_path, project_metadata, pipeline_snapshot, dataset_snapshots
    ):
        """Patch every sub-component so _build_project_snapshot runs in isolation."""
        self.project_path = tmp_path

        mocker.patch(
            "kedro.inspection.snapshot.bootstrap_project",
            return_value=project_metadata,
        )

        self.mock_config_loader = mocker.MagicMock()
        mocker.patch(
            "kedro.inspection.snapshot._make_config_loader",
            return_value=self.mock_config_loader,
        )

        self.metadata_snapshot = ProjectMetadataSnapshot(
            project_name=project_metadata.project_name,
            package_name=project_metadata.package_name,
            kedro_version=project_metadata.kedro_init_version,
        )
        mocker.patch(
            "kedro.inspection.snapshot._build_project_metadata_snapshot",
            return_value=self.metadata_snapshot,
        )

        self.pipeline_snapshots = [pipeline_snapshot]
        mocker.patch(
            "kedro.inspection.snapshot._build_pipeline_snapshots",
            return_value=self.pipeline_snapshots,
        )

        self.dataset_snapshots = dataset_snapshots
        mocker.patch(
            "kedro.inspection.snapshot._build_dataset_snapshots",
            return_value=self.dataset_snapshots,
        )

        # _resolve_factory_patterns returns the datasets unchanged by default
        mocker.patch(
            "kedro.inspection.snapshot._resolve_factory_patterns",
            return_value=self.dataset_snapshots,
        )

        mocker.patch(
            "kedro.inspection.snapshot._get_parameter_keys",
            return_value=["model_options", "test_size"],
        )

    def test_returns_project_snapshot_instance(self):
        result = _build_project_snapshot(self.project_path)
        assert isinstance(result, ProjectSnapshot)

    def test_metadata_populated(self):
        result = _build_project_snapshot(self.project_path)
        assert result.metadata is self.metadata_snapshot

    def test_pipelines_populated(self):
        result = _build_project_snapshot(self.project_path)
        assert result.pipelines is self.pipeline_snapshots

    def test_datasets_populated(self):
        result = _build_project_snapshot(self.project_path)
        assert result.datasets is self.dataset_snapshots

    def test_parameters_populated(self):
        result = _build_project_snapshot(self.project_path)
        assert result.parameters == ["model_options", "test_size"]

    def test_bootstrap_called_with_project_path(self, mocker):
        mock_bootstrap = mocker.patch(
            "kedro.inspection.snapshot.bootstrap_project",
            return_value=pytest.importorskip("kedro.framework.startup").ProjectMetadata(
                config_file=self.project_path / "pyproject.toml",
                package_name="my_package",
                project_name="My Project",
                project_path=self.project_path,
                source_dir=self.project_path / "src",
                kedro_init_version="1.2.0",
                tools=None,
                example_pipeline=None,
            ),
        )
        _build_project_snapshot(self.project_path)
        mock_bootstrap.assert_called_once_with(self.project_path)

    def test_config_loader_created_with_project_path(self, mocker):
        mock_make_loader = mocker.patch(
            "kedro.inspection.snapshot._make_config_loader",
            return_value=self.mock_config_loader,
        )
        _build_project_snapshot(self.project_path, env="staging")
        mock_make_loader.assert_called_once_with(self.project_path, env="staging")

    def test_config_loader_reused_for_datasets_and_params(self, mocker):
        """The same config loader instance is passed to both downstream builders."""
        calls_with_loader = []

        def capture_loader(loader):
            calls_with_loader.append(loader)
            return {}

        mocker.patch(
            "kedro.inspection.snapshot._build_dataset_snapshots",
            side_effect=capture_loader,
        )

        def capture_params_loader(loader):
            calls_with_loader.append(loader)
            return []

        mocker.patch(
            "kedro.inspection.snapshot._get_parameter_keys",
            side_effect=capture_params_loader,
        )

        _build_project_snapshot(self.project_path)

        assert len(calls_with_loader) == 2
        assert calls_with_loader[0] is calls_with_loader[1]

    def test_accepts_string_path(self, mocker):
        """A string project_path is accepted and converted internally."""
        result = _build_project_snapshot(str(self.project_path))
        assert isinstance(result, ProjectSnapshot)

    def test_factory_patterns_resolved(self, mocker):
        """_resolve_factory_patterns is called with datasets and pipelines."""
        mock_resolve = mocker.patch(
            "kedro.inspection.snapshot._resolve_factory_patterns",
            return_value=self.dataset_snapshots,
        )
        _build_project_snapshot(self.project_path)
        mock_resolve.assert_called_once_with(
            self.dataset_snapshots, self.pipeline_snapshots
        )
