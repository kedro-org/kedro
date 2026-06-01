"""Tests for the inspection public API"""

from __future__ import annotations

from kedro.inspection import get_project_snapshot
from kedro.inspection.models import ProjectSnapshot


class TestGetProjectSnapshot:
    def test_delegates_to_build_project_snapshot(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=ProjectSnapshot)
        mock_build = mocker.patch(
            "kedro.inspection._build_project_snapshot",
            return_value=mock_snapshot,
        )
        result = get_project_snapshot(tmp_path)
        mock_build.assert_called_once_with(
            project_path=tmp_path, env=None, conf_source=None, metadata=None
        )
        assert result is mock_snapshot
