"""Tests for the inspection public API (kedro/inspection/__init__.py)."""

from __future__ import annotations

from kedro.inspection import get_project_snapshot
from kedro.inspection.models import ProjectSnapshot


class TestGetProjectSnapshot:
    def test_get_project_snapshot_is_exported(self):
        from kedro.inspection import __all__

        assert "get_project_snapshot" in __all__

    def test_delegates_to_build_project_snapshot(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=ProjectSnapshot)
        mock_build = mocker.patch(
            "kedro.inspection._build_project_snapshot",
            return_value=mock_snapshot,
        )
        result = get_project_snapshot(tmp_path)
        mock_build.assert_called_once_with(tmp_path, env=None)
        assert result is mock_snapshot

    def test_passes_env_through(self, mocker, tmp_path):
        mock_build = mocker.patch(
            "kedro.inspection._build_project_snapshot",
            return_value=mocker.MagicMock(spec=ProjectSnapshot),
        )
        get_project_snapshot(tmp_path, env="staging")
        mock_build.assert_called_once_with(tmp_path, env="staging")
