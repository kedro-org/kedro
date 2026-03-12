"""Tests for ProjectMetadataSnapshot model and builder."""

from __future__ import annotations

import dataclasses
import json

import pytest

from kedro.framework.startup import ProjectMetadata
from kedro.inspection.models import ProjectMetadataSnapshot
from kedro.inspection.snapshot import _build_project_metadata_snapshot


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


class TestProjectMetadataSnapshot:
    def test_construction(self):
        snapshot = ProjectMetadataSnapshot(
            project_name="My Project",
            package_name="my_package",
            kedro_version="1.2.0",
        )
        assert snapshot.project_name == "My Project"
        assert snapshot.package_name == "my_package"
        assert snapshot.kedro_version == "1.2.0"

    def test_dict_serialization(self):
        snapshot = ProjectMetadataSnapshot(
            project_name="My Project",
            package_name="my_package",
            kedro_version="1.2.0",
        )
        result = dataclasses.asdict(snapshot)
        assert result == {
            "project_name": "My Project",
            "package_name": "my_package",
            "kedro_version": "1.2.0",
        }

    def test_json_serialization(self):
        snapshot = ProjectMetadataSnapshot(
            project_name="My Project",
            package_name="my_package",
            kedro_version="1.2.0",
        )
        result = json.loads(json.dumps(dataclasses.asdict(snapshot)))
        assert result["project_name"] == "My Project"
        assert result["package_name"] == "my_package"
        assert result["kedro_version"] == "1.2.0"


class TestInspectProjectMetadata:
    def test_builder_populates_all_fields(self, project_metadata):
        snapshot = _build_project_metadata_snapshot(project_metadata)
        assert snapshot.project_name == project_metadata.project_name
        assert snapshot.package_name == project_metadata.package_name

    def test_kedro_version_matches_metadata(self, project_metadata):
        snapshot = _build_project_metadata_snapshot(project_metadata)
        assert snapshot.kedro_version == project_metadata.kedro_init_version

    def test_returns_snapshot_instance(self, project_metadata):
        snapshot = _build_project_metadata_snapshot(project_metadata)
        assert isinstance(snapshot, ProjectMetadataSnapshot)

    def test_no_file_io(self, project_metadata, mocker):
        """Builder must not perform any file I/O."""
        mock_open = mocker.patch("builtins.open")
        _build_project_metadata_snapshot(project_metadata)
        mock_open.assert_not_called()
