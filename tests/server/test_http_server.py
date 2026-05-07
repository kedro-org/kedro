from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server import create_http_server as create_http_server_lazy
from kedro.server.http_server import create_http_server, execute_pipeline
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


class TestExecutePipeline:
    def test_execute_pipeline_success_returns_structured_result(self, mocker):
        session = mocker.Mock()
        mocker.patch(
            "kedro.server.http_server.generate_timestamp", return_value="run-success"
        )
        mock_load_obj = mocker.patch(
            "kedro.server.http_server.load_obj", return_value=_FakeRunner
        )

        result = execute_pipeline(
            session=session,
            pipeline_names=["__default__"],
            params={"alpha": 1},
            runner="ThreadRunner",
            is_async=True,
            tags=["t1"],
            node_names=["n1"],
            from_nodes=["fn"],
            to_nodes=["tn"],
            from_inputs=["fi"],
            to_outputs=["to"],
            load_versions={"ds": "2024-01-01"},
            namespaces=["ns"],
            only_missing_outputs=True,
        )

        assert isinstance(result, PipelineExecutionResult)
        assert result.run_id == "run-success"
        assert result.status == "success"
        assert result.duration_ms >= 0
        assert result.error is None

        mock_load_obj.assert_called_once_with("ThreadRunner", "kedro.runner")
        session.run.assert_called_once()
        run_kwargs = session.run.call_args.kwargs
        assert run_kwargs["run_id"] == "run-success"
        assert run_kwargs["pipeline_names"] == ["__default__"]
        assert run_kwargs["tags"] == ("t1",)
        assert run_kwargs["node_names"] == ("n1",)
        assert run_kwargs["from_nodes"] == ["fn"]
        assert run_kwargs["to_nodes"] == ["tn"]
        assert run_kwargs["from_inputs"] == ["fi"]
        assert run_kwargs["to_outputs"] == ["to"]
        assert run_kwargs["load_versions"] == {"ds": "2024-01-01"}
        assert run_kwargs["namespaces"] == ["ns"]
        assert run_kwargs["only_missing_outputs"] is True
        assert run_kwargs["runtime_params"] == {"alpha": 1}
        assert isinstance(run_kwargs["runner"], _FakeRunner)
        assert run_kwargs["runner"].is_async is True

    def test_execute_pipeline_defaults_to_sequential_runner(self, mocker):
        session = mocker.Mock()
        mocker.patch(
            "kedro.server.http_server.generate_timestamp", return_value="run-default"
        )
        mock_load_obj = mocker.patch(
            "kedro.server.http_server.load_obj", return_value=_FakeRunner
        )

        result = execute_pipeline(session=session)

        assert result.status == "success"
        mock_load_obj.assert_called_once_with("SequentialRunner", "kedro.runner")
        run_kwargs = session.run.call_args.kwargs
        assert run_kwargs["tags"] is None
        assert run_kwargs["node_names"] is None
        assert run_kwargs["runner"].is_async is False

    def test_execute_pipeline_failure_returns_error_detail(self, mocker):
        session = mocker.Mock()
        session.run.side_effect = ValueError("boom")
        mocker.patch(
            "kedro.server.http_server.generate_timestamp", return_value="run-fail"
        )
        mocker.patch("kedro.server.http_server.load_obj", return_value=_FakeRunner)

        result = execute_pipeline(session=session)

        assert isinstance(result, PipelineExecutionResult)
        assert result.run_id == "run-fail"
        assert result.status == "failure"
        assert result.duration_ms >= 0
        assert isinstance(result.error, PipelineExecutionError)
        assert result.error.type == "ValueError"
        assert result.error.message == "boom"
        assert isinstance(result.error.traceback, list)

    def test_execute_pipeline_failure_falls_back_to_unknown_run_id(self, mocker):
        session = mocker.Mock()
        session.run.side_effect = RuntimeError("late failure")
        mocker.patch("kedro.server.http_server.generate_timestamp", return_value=None)
        mocker.patch("kedro.server.http_server.load_obj", return_value=_FakeRunner)

        result = execute_pipeline(session=session)

        assert result.run_id == "unknown"
        assert result.status == "failure"
        assert result.error is not None
        assert result.error.type == "RuntimeError"
