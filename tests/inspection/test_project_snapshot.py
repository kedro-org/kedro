"""Tests for ProjectSnapshot model and _build_project_snapshot orchestrator."""

from __future__ import annotations

import pytest

from kedro.config import MissingConfigException
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

        self.mock_bootstrap = mocker.patch(
            "kedro.inspection.snapshot.bootstrap_project",
            return_value=project_metadata,
        )

        self.mock_config_loader = mocker.MagicMock()
        self.mock_make_config_loader = mocker.patch(
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
            "kedro.inspection.snapshot.pipelines",
            new={},
        )
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
        self.mock_resolve_factory_patterns = mocker.patch(
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

    def test_bootstrap_called_with_project_path(self):
        _build_project_snapshot(self.project_path)
        self.mock_bootstrap.assert_called_once_with(self.project_path)

    def test_config_loader_created_with_explicit_env(self):
        _build_project_snapshot(self.project_path, env="staging")
        self.mock_make_config_loader.assert_called_once_with(
            self.project_path, env="staging", conf_source=None
        )

    def test_config_loader_created_with_default_env(self):
        _build_project_snapshot(self.project_path)
        self.mock_make_config_loader.assert_called_once_with(
            self.project_path, env=None, conf_source=None
        )

    def test_config_loader_created_with_explicit_conf_source(self):
        _build_project_snapshot(self.project_path, conf_source="conf/custom")
        self.mock_make_config_loader.assert_called_once_with(
            self.project_path, env=None, conf_source="conf/custom"
        )

    def test_metadata_parameter_skips_bootstrap(self, project_metadata):
        _build_project_snapshot(self.project_path, metadata=project_metadata)
        self.mock_bootstrap.assert_not_called()

    def test_catalog_loaded_from_config_loader_and_passed_downstream(self, mocker):
        """Catalog config is loaded from the config loader and passed to both
        _build_dataset_snapshots and _resolve_factory_patterns."""
        catalog_data = {"companies": {"type": "pandas.CSVDataset"}}
        self.mock_config_loader.__getitem__.return_value = catalog_data

        captured_ds = []
        mocker.patch(
            "kedro.inspection.snapshot._build_dataset_snapshots",
            side_effect=lambda conf: captured_ds.append(conf) or {},
        )
        captured_rfp = []
        mocker.patch(
            "kedro.inspection.snapshot._resolve_factory_patterns",
            side_effect=lambda conf, ds, pipes: captured_rfp.append(conf) or ds,
        )

        _build_project_snapshot(self.project_path)

        assert captured_ds == [catalog_data]
        assert captured_rfp == [catalog_data]

    def test_accepts_string_path(self):
        """A string project_path is accepted and converted internally."""
        result = _build_project_snapshot(str(self.project_path))
        assert isinstance(result, ProjectSnapshot)

    def test_factory_patterns_resolved(self):
        """_resolve_factory_patterns is called with catalog_config, datasets, and pipelines."""
        _build_project_snapshot(self.project_path)
        self.mock_resolve_factory_patterns.assert_called_once_with(
            self.mock_config_loader["catalog"],
            self.dataset_snapshots,
            self.pipeline_snapshots,
        )

    def test_missing_catalog_key_error_falls_back_to_empty(self, mocker):
        """When config_loader['catalog'] raises KeyError, an empty dict is used."""
        self.mock_config_loader.__getitem__.side_effect = KeyError("catalog")
        captured = []
        mocker.patch(
            "kedro.inspection.snapshot._build_dataset_snapshots",
            side_effect=lambda conf: captured.append(conf) or {},
        )
        _build_project_snapshot(self.project_path)
        assert captured == [{}]

    def test_missing_catalog_missing_config_falls_back_to_empty(self, mocker):
        """When config_loader['catalog'] raises MissingConfigException, an empty dict is used."""
        self.mock_config_loader.__getitem__.side_effect = MissingConfigException(
            "catalog"
        )
        captured = []
        mocker.patch(
            "kedro.inspection.snapshot._build_dataset_snapshots",
            side_effect=lambda conf: captured.append(conf) or {},
        )
        _build_project_snapshot(self.project_path)
        assert captured == [{}]

    def test_project_path_is_resolved_before_bootstrap(self):
        """Path with '..' segments is resolved before being passed to bootstrap_project."""
        unresolved = self.project_path / "subdir" / ".."
        expected = unresolved.resolve()
        _build_project_snapshot(unresolved)
        self.mock_bootstrap.assert_called_once_with(expected)

    @pytest.mark.parametrize("env", ["staging/prod", "../prod", "bad env", "env!", ""])
    def test_invalid_env_raises_value_error(self, env):
        with pytest.raises(ValueError, match="Invalid env value"):
            _build_project_snapshot(self.project_path, env=env)

    @pytest.mark.parametrize(
        "env", ["staging", "prod", "local", "staging-1", "my_env", "env2", None]
    )
    def test_valid_env_does_not_raise(self, env):
        _build_project_snapshot(self.project_path, env=env)

    def test_raises_when_neither_project_path_nor_metadata_provided(self):
        with pytest.raises(
            ValueError, match="Either project_path or metadata must be provided"
        ):
            _build_project_snapshot()

    def test_warns_when_project_path_and_metadata_project_path_differ(
        self, project_metadata, tmp_path
    ):
        different_path = tmp_path / "other_project"
        with pytest.warns(UserWarning, match="project_path will be ignored"):
            _build_project_snapshot(different_path, metadata=project_metadata)

    def test_no_warning_when_project_path_matches_metadata(self, project_metadata):
        import warnings

        with warnings.catch_warnings():
            warnings.simplefilter("error")
            _build_project_snapshot(
                project_metadata.project_path, metadata=project_metadata
            )

    def test_metadata_project_path_used_for_config_loader_when_only_metadata_provided(
        self, project_metadata
    ):
        _build_project_snapshot(metadata=project_metadata)
        self.mock_bootstrap.assert_not_called()
        self.mock_make_config_loader.assert_called_once_with(
            project_metadata.project_path, env=None, conf_source=None
        )
