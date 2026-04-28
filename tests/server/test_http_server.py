from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server import create_http_server as create_http_server_lazy
from kedro.server.http_server import create_http_server


class TestHTTPServer:
    def test_lazy_import_wrapper(self, mocker):
        app = mocker.Mock(name="app")
        mock_create = mocker.patch(
            "kedro.server.http_server.create_http_server", return_value=app
        )

        result = create_http_server_lazy()

        mock_create.assert_called_once_with()
        assert result is app

    def test_health_endpoint_with_lifespan(self, mocker, tmp_path):
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server.get_project_path", return_value=project_path
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

    def test_create_http_server_raises_on_bad_project_path(self, mocker, tmp_path):
        mocker.patch(
            "kedro.server.http_server.get_project_path",
            side_effect=RuntimeError("cannot resolve project"),
        )

        with pytest.raises(RuntimeError, match="cannot resolve project"):
            create_http_server()
