from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server import create_http_server as create_http_server_lazy
from kedro.server.http_server import create_http_server
from kedro.server.models import PipelineExecutionError, PipelineExecutionResult


class _FakeRunner:
    def __init__(self, *, is_async):
        self.is_async = is_async


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

    def test_create_http_server_raises_on_bad_project_path(self, mocker, tmp_path):
        mocker.patch(
            "kedro.server.http_server._resolve_project_path",
            side_effect=RuntimeError("cannot resolve project"),
        )

        with pytest.raises(RuntimeError, match="cannot resolve project"):
            create_http_server()

    def test_run_endpoint_reuses_service_session(self, mocker, tmp_path):
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()
        mock_create_session = mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mock_execute = mocker.patch(
            "kedro.server.http_server.execute_pipeline",
            return_value=PipelineExecutionResult(
                run_id="run-1",
                status="success",
                duration_ms=10.0,
            ),
        )

        app = create_http_server()
        with TestClient(app) as client:
            first = client.post("/run", json={})
            second = client.post("/run", json={})

        assert first.status_code == 200
        assert second.status_code == 200
        assert first.json()["status"] == "success"
        assert second.json()["status"] == "success"
        mock_create_session.assert_called_once_with(
            project_path=project_path, env=None, conf_source=None
        )
        assert mock_execute.call_count == 2

    def test_run_endpoint_uses_factory_defaults(self, mocker, tmp_path):
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()
        mock_create_session = mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mocker.patch(
            "kedro.server.http_server.execute_pipeline",
            return_value=PipelineExecutionResult(
                run_id="run-2",
                status="success",
                duration_ms=10.0,
            ),
        )

        app = create_http_server(
            project_path=str(project_path),
            env="base",
            conf_source="conf/base",
        )
        with TestClient(app) as client:
            response = client.post("/run", json={})

        assert response.status_code == 200
        mock_create_session.assert_called_once_with(
            project_path=project_path,
            env="base",
            conf_source="conf/base",
        )

    def test_run_endpoint_uses_env_var_defaults(self, mocker, tmp_path, monkeypatch):
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()
        mock_create_session = mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mocker.patch(
            "kedro.server.http_server.execute_pipeline",
            return_value=PipelineExecutionResult(
                run_id="run-3",
                status="success",
                duration_ms=10.0,
            ),
        )
        monkeypatch.setenv("KEDRO_SERVER_ENV", "local")
        monkeypatch.setenv("KEDRO_SERVER_CONF_SOURCE", "conf/local")

        app = create_http_server(project_path=str(project_path))
        with TestClient(app) as client:
            response = client.post("/run", json={})

        assert response.status_code == 200
        mock_create_session.assert_called_once_with(
            project_path=project_path,
            env="local",
            conf_source="conf/local",
        )

    def test_run_endpoint_factory_defaults_override_env_vars(
        self, mocker, tmp_path, monkeypatch
    ):
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()
        mock_create_session = mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mocker.patch(
            "kedro.server.http_server.execute_pipeline",
            return_value=PipelineExecutionResult(
                run_id="run-4",
                status="success",
                duration_ms=10.0,
            ),
        )
        monkeypatch.setenv("KEDRO_SERVER_ENV", "local")
        monkeypatch.setenv("KEDRO_SERVER_CONF_SOURCE", "conf/local")

        app = create_http_server(
            project_path=str(project_path),
            env="base",
            conf_source="conf/base",
        )
        with TestClient(app) as client:
            response = client.post("/run", json={})

        assert response.status_code == 200
        mock_create_session.assert_called_once_with(
            project_path=project_path,
            env="base",
            conf_source="conf/base",
        )

    def test_run_endpoint_returns_error_detail_on_failure(self, mocker, tmp_path):
        project_path = Path(tmp_path).resolve()
        fake_session = mocker.Mock()

        mocker.patch(
            "kedro.server.http_server.KedroServiceSession.create",
            return_value=fake_session,
        )
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mocker.patch("kedro.server.http_server.bootstrap_project")
        mocker.patch(
            "kedro.server.http_server.execute_pipeline",
            return_value=PipelineExecutionResult(
                run_id="run-fail",
                status="failure",
                duration_ms=12.34,
                error=PipelineExecutionError(
                    type="ValueError",
                    message="bad run",
                    traceback=["Traceback line"],
                ),
            ),
        )

        app = create_http_server()
        with TestClient(app) as client:
            response = client.post("/run", json={})

        assert response.status_code == 200
        payload = response.json()
        assert payload["run_id"] == "run-fail"
        assert payload["status"] == "failure"
        assert payload["duration_ms"] == 12.34
        assert payload["error"] == {
            "type": "ValueError",
            "message": "bad run",
            "traceback": ["Traceback line"],
        }
