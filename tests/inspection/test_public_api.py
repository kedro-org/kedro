"""Tests for the inspection public API"""

from __future__ import annotations

import pytest

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
            project_path=tmp_path,
            env=None,
            conf_source=None,
            metadata=None,
            runtime_params=None,
            group_by="namespace",
        )
        assert result is mock_snapshot

    def test_delegates_runtime_params_to_build_project_snapshot(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=ProjectSnapshot)
        mock_build = mocker.patch(
            "kedro.inspection._build_project_snapshot",
            return_value=mock_snapshot,
        )
        runtime_params = {"version": "02"}
        result = get_project_snapshot(tmp_path, runtime_params=runtime_params)
        mock_build.assert_called_once_with(
            project_path=tmp_path,
            env=None,
            conf_source=None,
            metadata=None,
            runtime_params=runtime_params,
            group_by="namespace",
        )
        assert result is mock_snapshot

    def test_unsupported_group_by_raises_without_bootstrapping(self, mocker, tmp_path):
        mock_bootstrap = mocker.patch("kedro.inspection.snapshot.bootstrap_project")
        with pytest.raises(ValueError, match="Unsupported group_by strategy: 'tags'"):
            get_project_snapshot(tmp_path, group_by="tags")
        mock_bootstrap.assert_not_called()

    def test_delegates_group_by_to_build_project_snapshot(self, mocker, tmp_path):
        mock_build = mocker.patch("kedro.inspection._build_project_snapshot")
        get_project_snapshot(tmp_path, group_by=None)
        mock_build.assert_called_once_with(
            project_path=tmp_path,
            env=None,
            conf_source=None,
            metadata=None,
            runtime_params=None,
            group_by=None,
        )
