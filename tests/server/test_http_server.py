from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server.http_server import create_http_server
from kedro.server.models import RunResponse


class TestHTTPServerFactory:
    """Tests for HTTP server factory creation and health endpoint."""

    def test_create_http_server_resolves_env_from_argument(
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

    def test_conf_source_in_app_state(self, mocker, tmp_path):
        """Test that conf_source is stored in app state for later use."""
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=tmp_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server(conf_source="conf/custom")

        assert app.state.default_conf_source == "conf/custom"

    def test_create_http_server_raises_on_bad_project_path(self, mocker, tmp_path):
        mocker.patch(
            "kedro.server.http_server._resolve_project_path",
            side_effect=RuntimeError("cannot resolve project"),
        )

        with pytest.raises(RuntimeError, match="cannot resolve project"):
            create_http_server()

    def test_lifespan_calls_bootstrap_on_startup(self, mocker, tmp_path):
        """Test that lifespan bootstraps the project and stores metadata on app.state."""
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mock_bootstrap = mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server()
        with TestClient(app) as client:
            client.get("/health")

        mock_bootstrap.assert_called_once_with(project_path)
        assert app.state.metadata is mock_bootstrap.return_value

    def test_lifespan_closes_session_on_shutdown(self, mocker, tmp_path):
        """Test that the session is closed when the server shuts down."""
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch(
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
                run_id="run-1", status="success", duration_ms=10.0
            ),
        )

        app = create_http_server()
        with TestClient(app) as client:
            client.post("/run", json={})

        fake_session.close.assert_called_once()

    def test_lifespan_shutdown_without_session(self, mocker, tmp_path):
        """Test that shutdown does not raise if no session was created."""
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server()
        with TestClient(app):
            pass  # no /run call, so no session is created

    def test_lifespan_warns_on_custom_session_class(self, mocker, tmp_path, caplog):
        """Test that a warning is logged when SESSION_CLASS is not KedroServiceSession."""
        import logging

        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")

        class CustomSession:
            pass

        mock_settings = mocker.Mock()
        mock_settings.SESSION_CLASS = CustomSession
        mocker.patch("kedro.server.http_server.settings", mock_settings)

        app = create_http_server()
        with caplog.at_level(logging.WARNING, logger="kedro.server.http_server"):
            with TestClient(app):
                pass

        assert any(
            "SESSION_CLASS" in record.message or "KedroServiceSession" in record.message
            for record in caplog.records
        )

    def test_health_endpoint_returns_healthy_status(self, mocker, tmp_path):
        """Test that health endpoint returns 200 with healthy status."""
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server()
        with TestClient(app) as client:
            response = client.get("/health")

        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

    def test_health_endpoint_response_model_validation(self, mocker, tmp_path):
        """Test that health endpoint response validates against HealthResponse model."""
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server()
        with TestClient(app) as client:
            response = client.get("/health")

        payload = response.json()
        assert set(payload.keys()) == {"status", "kedro_version"}
        assert payload["status"] in ["healthy", "unhealthy"]
        assert "kedro_version" in payload
        assert isinstance(payload["kedro_version"], str)
        assert len(payload["kedro_version"]) > 0
        assert "project_path" not in payload
