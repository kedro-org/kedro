from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server.http_server import _execute_pipeline, create_http_server
from kedro.server.models import ErrorDetail, RunRequest, RunResponse


class _FakeRunner:
    def __init__(self, *, is_async):
        self.is_async = is_async


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
        """Test that lifespan context manager calls bootstrap_project on startup."""
        project_path = Path(tmp_path).resolve()
        mocker.patch(
            "kedro.server.http_server._resolve_project_path", return_value=project_path
        )
        mock_bootstrap = mocker.patch("kedro.server.http_server.bootstrap_project")

        app = create_http_server()
        with TestClient(app) as client:
            client.get("/health")

        mock_bootstrap.assert_called_once_with(project_path)

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
        assert response.json()["project_path"] == str(project_path)

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
        assert set(payload.keys()) == {"status", "kedro_version", "project_path"}
        assert payload["status"] in ["healthy", "unhealthy"]
        assert "kedro_version" in payload
        assert isinstance(payload["kedro_version"], str)
        assert len(payload["kedro_version"]) > 0


class TestRunEndpoint:
    """Tests for /run endpoint and session management."""

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
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
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
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
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
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
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
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
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
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
                run_id="run-fail",
                status="failure",
                duration_ms=12.34,
                error=ErrorDetail(
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

    def test_run_endpoint_passes_parameters_to_execute_pipeline(self, mocker, tmp_path):
        """Test that RunRequest parameters are passed to _execute_pipeline."""
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
        mock_execute = mocker.patch(
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
                run_id="run-params",
                status="success",
                duration_ms=15.0,
            ),
        )

        app = create_http_server()
        with TestClient(app) as client:
            response = client.post(
                "/run",
                json={
                    "pipeline_names": ["my_pipeline"],
                    "params": {"learning_rate": 0.01},
                    "runner": "SequentialRunner",
                    "tags": ["training"],
                },
            )

        assert response.status_code == 200
        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args[1]
        request = call_kwargs["request"]
        assert request.pipeline_names == ["my_pipeline"]
        assert request.params == {"learning_rate": 0.01}
        assert request.runner == "SequentialRunner"
        assert request.tags == ["training"]

    def test_run_endpoint_passes_partial_parameters_to_execute_pipeline(
        self, mocker, tmp_path
    ):
        """Test that partial RunRequest parameters are passed correctly."""
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
        mock_execute = mocker.patch(
            "kedro.server.http_server._execute_pipeline",
            return_value=RunResponse(
                run_id="run-partial",
                status="success",
                duration_ms=8.5,
            ),
        )

        app = create_http_server()
        with TestClient(app) as client:
            response = client.post(
                "/run",
                json={
                    "node_names": ["node1", "node2"],
                    "from_inputs": ["input_data"],
                    "is_async": True,
                },
            )

        assert response.status_code == 200
        mock_execute.assert_called_once()
        call_kwargs = mock_execute.call_args[1]
        request = call_kwargs["request"]
        assert request.node_names == ["node1", "node2"]
        assert request.from_inputs == ["input_data"]
        assert request.is_async is True


class TestExecutePipeline:
    def test_execute_pipeline_success_with_defaults(self, mocker):
        """Test successful pipeline execution loads SequentialRunner by default."""

        mock_session = mocker.Mock()
        mock_runner = _FakeRunner(is_async=False)
        mock_runner_factory = mocker.Mock(return_value=mock_runner)
        mock_load_obj = mocker.patch(
            "kedro.server.http_server.load_obj",
            return_value=mock_runner_factory,
        )

        result = _execute_pipeline(session=mock_session, request=RunRequest())

        assert result.status == "success"
        assert result.run_id is not None
        assert result.duration_ms > 0
        assert result.error is None
        mock_load_obj.assert_called_once_with("SequentialRunner", "kedro.runner")
        mock_runner_factory.assert_called_once_with(is_async=False)
        mock_session.run.assert_called_once()
        assert mock_session.run.call_args.kwargs["runner"] is mock_runner

    def test_execute_pipeline_success_with_custom_runner(self, mocker):
        """Test successful execution with custom runner class."""

        mock_session = mocker.Mock()
        mock_runner = _FakeRunner(is_async=True)
        mock_load_obj = mocker.patch(
            "kedro.server.http_server.load_obj",
            return_value=lambda is_async: mock_runner,
        )

        result = _execute_pipeline(
            session=mock_session,
            request=RunRequest(runner="ParallelRunner", is_async=True),
        )

        assert result.status == "success"
        mock_load_obj.assert_called_once_with("ParallelRunner", "kedro.runner")
        mock_session.run.assert_called_once()
        call_kwargs = mock_session.run.call_args[1]
        assert call_kwargs["runner"].is_async is True

    def test_execute_pipeline_failure_with_exception(self, mocker):
        """Test pipeline execution failure with exception."""

        mock_session = mocker.Mock()
        mock_session.run.side_effect = ValueError("Pipeline execution failed")
        mock_runner = _FakeRunner(is_async=False)
        mocker.patch(
            "kedro.server.http_server.load_obj",
            return_value=lambda is_async: mock_runner,
        )

        result = _execute_pipeline(session=mock_session, request=RunRequest())

        assert result.status == "failure"
        assert result.run_id is not None
        assert result.error is not None
        assert result.error.type == "ValueError"
        assert result.error.message == "Pipeline execution failed"
        assert isinstance(result.error.traceback, list)

    def test_execute_pipeline_runner_loading_failure(self, mocker):
        """Test failure when runner class cannot be loaded."""

        mock_session = mocker.Mock()
        mocker.patch(
            "kedro.server.http_server.load_obj",
            side_effect=AttributeError("UnknownRunner not found"),
        )

        result = _execute_pipeline(
            session=mock_session,
            request=RunRequest(runner="UnknownRunner"),
        )

        assert result.status == "failure"
        assert result.error.type == "AttributeError"
        assert "UnknownRunner" in result.error.message

    def test_execute_pipeline_with_all_parameters(self, mocker):
        """Test pipeline execution with all parameters provided."""

        mock_session = mocker.Mock()
        mock_runner = _FakeRunner(is_async=False)
        mocker.patch(
            "kedro.server.http_server.load_obj",
            return_value=lambda is_async: mock_runner,
        )

        result = _execute_pipeline(
            session=mock_session,
            request=RunRequest(
                pipeline_names=["pipeline1", "pipeline2"],
                params={"param1": "value1"},
                runner="SequentialRunner",
                is_async=False,
                tags=["tag1", "tag2"],
                node_names=["node1"],
                from_nodes=["node2"],
                to_nodes=["node3"],
                from_inputs=["input1"],
                to_outputs=["output1"],
                load_versions={"dataset1": "2024-01-01"},
                namespaces=["ns1"],
                only_missing_outputs=True,
            ),
        )

        assert result.status == "success"
        call_kwargs = mock_session.run.call_args[1]
        assert call_kwargs["pipeline_names"] == ["pipeline1", "pipeline2"]
        assert call_kwargs["tags"] == ("tag1", "tag2")
        assert call_kwargs["node_names"] == ("node1",)
        assert call_kwargs["from_nodes"] == ["node2"]
        assert call_kwargs["to_nodes"] == ["node3"]
        assert call_kwargs["from_inputs"] == ["input1"]
        assert call_kwargs["to_outputs"] == ["output1"]
        assert call_kwargs["load_versions"] == {"dataset1": "2024-01-01"}
        assert call_kwargs["namespaces"] == ["ns1"]
        assert call_kwargs["only_missing_outputs"] is True
        assert call_kwargs["runtime_params"] == {"param1": "value1"}
