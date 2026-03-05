from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_session():
    with patch("kedro.framework.session.KedroSession.create") as mock_create_session:
        mock_context = MagicMock()
        mock_catalog = MagicMock()
        mock_context.catalog = mock_catalog
        mock_session = MagicMock()
        mock_session.load_context.return_value = mock_context
        mock_create_session.return_value = mock_session
        yield mock_catalog


def test_describe_datasets_cli(runner, mock_session, fake_project_cli, fake_metadata):
    mock_session.describe_datasets.return_value = {
        "pipeline1": {
            "datasets": {"CSVDataSet": ["input1.csv"]},
            "factories": {},
            "defaults": {},
        }
    }

    result = runner.invoke(
        fake_project_cli,
        ["catalog", "describe-datasets", "--pipeline", "pipeline1", "--env", "local"],
        obj=fake_metadata,
    )

    assert result.exit_code == 0
    assert "pipeline1" in result.output
    assert "datasets" in result.output
    mock_session.describe_datasets.assert_called_once_with(["pipeline1"])


def test_list_patterns_cli(runner, mock_session, fake_project_cli, fake_metadata):
    mock_session.list_patterns.return_value = ["pattern_*", "other_*"]

    result = runner.invoke(
        fake_project_cli,
        ["catalog", "list-patterns", "--env", "local"],
        obj=fake_metadata,
    )

    assert result.exit_code == 0
    assert "pattern_*" in result.output
    mock_session.list_patterns.assert_called_once()


def test_resolve_patterns_cli(runner, mock_session, fake_project_cli, fake_metadata):
    mock_session.resolve_patterns.return_value = {
        "dataset1": {"type": "CSVDataSet", "filepath": "data/01_raw/ds1.csv"}
    }

    result = runner.invoke(
        fake_project_cli,
        ["catalog", "resolve-patterns", "--pipeline", "pipeline1", "--env", "local"],
        obj=fake_metadata,
    )

    assert result.exit_code == 0
    assert "dataset1" in result.output
    mock_session.resolve_patterns.assert_called_once_with(["pipeline1"])
