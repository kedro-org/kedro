from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server import create_http_server as create_http_server_lazy
from kedro.server.http_server import create_http_server
from kedro.server.utils import ServerSettingsError


class TestHTTPServer:
    def test_lazy_import_wrapper(self, mocker):
        app = mocker.Mock(name="app")
        mock_create = mocker.patch(
            "kedro.server.http_server.create_http_server", return_value=app
        )

        result = create_http_server_lazy()

        mock_create.assert_called_once_with(
            project_path=None, env=None, conf_source=None
        )
        assert result is app

    def test_create_http_server_resolves_env_from_argument_over_env_var(
        self, monkeypatch, mocker, tmp_path
    ):
        monkeypatch.setenv("KEDRO_SERVER_ENV", "from_env_var")
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=tmp_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        app = create_http_server(env="from_argument")
        assert app.state.default_env == "from_argument"
        assert app.state.default_conf_source is None

    def test_health_endpoint_with_lifespan(self, mocker, tmp_path):
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mock_bootstrap_project = mocker.patch(
            "kedro.server.http_server.bootstrap_project"
        )

        app = create_http_server()
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
        assert response.json()["project_path"] == str(project_path)
        mock_bootstrap_project.assert_called_once_with(project_path)

    def test_create_http_server_raises_on_bad_project_path(self, mocker):
        mocker.patch(
            "kedro.server.http_server._resolve_project_path",
            side_effect=ServerSettingsError("is not set"),
        )

        with pytest.raises(ServerSettingsError, match="is not set"):
            create_http_server()
