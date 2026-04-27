import types

import pytest
from click.testing import CliRunner

from kedro.framework.cli.server import _resolve_project_path
from kedro.framework.cli.utils import KedroCliError
from kedro.server.utils import DEFAULT_HOST, DEFAULT_HTTP_PORT, KEDRO_PROJECT_PATH_ENV


class TestServerStartCommand:
    def test_uses_metadata_project_path(self, fake_metadata):
        assert _resolve_project_path(fake_metadata) == fake_metadata.project_path

    def test_falls_back_to_discovered_project(self, mocker, tmp_path):
        mock_find_project = mocker.patch(
            "kedro.framework.cli.server.find_kedro_project",
            return_value=tmp_path,
        )
        mock_bootstrap_project = mocker.patch(
            "kedro.framework.cli.server.bootstrap_project"
        )

        assert _resolve_project_path(None) == tmp_path
        mock_find_project.assert_called_once_with()
        mock_bootstrap_project.assert_called_once_with(tmp_path)

    def test_raises_when_project_cannot_be_discovered(self, mocker):
        mocker.patch("kedro.framework.cli.server.find_kedro_project", return_value=None)

        with pytest.raises(KedroCliError, match="Could not find a Kedro project"):
            _resolve_project_path(None)

    def test_server_with_default_options(self, fake_metadata, fake_project_cli, mocker):
        mock_environ = mocker.patch("os.environ", {})
        uvicorn_run = mocker.Mock()
        mocker.patch.dict(
            "sys.modules", {"uvicorn": types.SimpleNamespace(run=uvicorn_run)}
        )

        result = CliRunner().invoke(fake_project_cli, ["start"], obj=fake_metadata)

        assert result.exit_code == 0, result.output
        assert mock_environ[KEDRO_PROJECT_PATH_ENV] == str(fake_metadata.project_path)
        assert "KEDRO_SERVER_DEBUG" not in mock_environ
        uvicorn_run.assert_called_once_with(
            "kedro.server.http_server:create_http_server",
            factory=True,
            host=DEFAULT_HOST,
            port=DEFAULT_HTTP_PORT,
            reload=False,
            log_level="info",
        )

    def test_server_with_custom_options(self, fake_metadata, fake_project_cli, mocker):
        mock_environ = mocker.patch("os.environ", {})
        uvicorn_run = mocker.Mock()
        mocker.patch.dict(
            "sys.modules", {"uvicorn": types.SimpleNamespace(run=uvicorn_run)}
        )

        result = CliRunner().invoke(
            fake_project_cli,
            ["start", "--host", "2.2.2.2", "--port", "9000", "--reload", "--debug"],
            obj=fake_metadata,
        )

        assert result.exit_code == 0, result.output
        assert mock_environ[KEDRO_PROJECT_PATH_ENV] == str(fake_metadata.project_path)
        assert mock_environ["KEDRO_SERVER_DEBUG"] == "1"
        uvicorn_run.assert_called_once_with(
            "kedro.server.http_server:create_http_server",
            factory=True,
            host="2.2.2.2",  # Random address to ensure options are passed through
            port=9000,
            reload=True,
            log_level="info",
        )

    def test_raises_helpful_error_when_uvicorn_is_missing(
        self, fake_project_cli, fake_metadata, mocker
    ):
        mocker.patch.dict("sys.modules", {"uvicorn": None})

        result = CliRunner().invoke(fake_project_cli, ["start"], obj=fake_metadata)

        assert result.exit_code != 0
        assert "requires 'uvicorn' and 'fastapi' packages" in result.output
