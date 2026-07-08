"""Tests for the inspection public API"""

from __future__ import annotations

from kedro.inspection import get_node_source, get_project_snapshot
from kedro.inspection.models import NodeSourceSnapshot, ProjectSnapshot


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


class TestGetNodeSource:
    def test_delegates_to_build_node_source_snapshot(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=NodeSourceSnapshot)
        mock_build = mocker.patch(
            "kedro.inspection._build_node_source_snapshot",
            return_value=mock_snapshot,
        )
        result = get_node_source("my_node", tmp_path)
        mock_build.assert_called_once_with(
            node_name="my_node",
            project_path=tmp_path,
            env=None,
            conf_source=None,
            metadata=None,
            include_code=True,
        )
        assert result is mock_snapshot

    def test_include_code_false_forwarded(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=NodeSourceSnapshot)
        mock_build = mocker.patch(
            "kedro.inspection._build_node_source_snapshot",
            return_value=mock_snapshot,
        )
        get_node_source("my_node", tmp_path, include_code=False)
        mock_build.assert_called_once_with(
            node_name="my_node",
            project_path=tmp_path,
            env=None,
            conf_source=None,
            metadata=None,
            include_code=False,
        )

    def test_all_params_forwarded(self, mocker, tmp_path):
        mock_snapshot = mocker.MagicMock(spec=NodeSourceSnapshot)
        mock_metadata = mocker.MagicMock()
        mock_build = mocker.patch(
            "kedro.inspection._build_node_source_snapshot",
            return_value=mock_snapshot,
        )
        get_node_source(
            "my_node",
            tmp_path,
            env="staging",
            conf_source="/conf",
            metadata=mock_metadata,
            include_code=False,
        )
        mock_build.assert_called_once_with(
            node_name="my_node",
            project_path=tmp_path,
            env="staging",
            conf_source="/conf",
            metadata=mock_metadata,
            include_code=False,
        )
