from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kedro.server import create_http_server as create_http_server_lazy
from kedro.server.http_server import create_http_server, execute_pipeline
from kedro.server.models import PipelineExecutionError, PipelineExecutionResult


class _FakeRunner:
    def __init__(self, *, is_async):
        self.is_async = is_async


def test_lazy_import_wrapper(mocker):
    app = mocker.Mock(name="app")
    mock_create = mocker.patch(
        "kedro.server.http_server.create_http_server", return_value=app
    )

    result = create_http_server_lazy()

    mock_create.assert_called_once_with()
    assert result is app


def test_execute_pipeline_success(mocker):
    """Test that execute_pipeline returns success result and handles debug mode correctly."""
    session = mocker.Mock()
    session.run.return_value = {}

    mocker.patch("kedro.server.http_server.is_debug_mode", return_value=False)
    mocker.patch("kedro.server.http_server.generate_timestamp", return_value="run-123")
    mocker.patch("kedro.server.http_server.load_obj", return_value=_FakeRunner)

    result = execute_pipeline(
        session,
        pipeline_names=["__default__"],
        runner="SequentialRunner",
        is_async=True,
        tags=["train", "daily"],
        node_names=["node_a"],
        from_nodes=["node_a"],
        to_nodes=["node_b"],
        from_inputs=["raw"],
        to_outputs=["model"],
        load_versions={"cars": "2025-01-01T00.00.00.000Z"},
        namespaces=["ns"],
        only_missing_outputs=True,
        params={"alpha": 1},
    )

    assert result.status == "success"
    assert result.run_id == "run-123"
    assert result.error is None

    session.run.assert_called_once()
    kwargs = session.run.call_args.kwargs
    assert kwargs["pipeline_names"] == ["__default__"]
    assert kwargs["tags"] == ("train", "daily")
    assert kwargs["node_names"] == ("node_a",)
    assert kwargs["only_missing_outputs"] is True
    assert kwargs["runtime_params"] == {"alpha": 1}
    assert isinstance(kwargs["runner"], _FakeRunner)
    assert kwargs["runner"].is_async is True


def test_execute_pipeline_failure_hides_traceback(mocker):
    """Test that execute_pipeline returns failure result and hides traceback when debug mode is off."""
    session = mocker.Mock()
    session.run.side_effect = ValueError("bad run")

    mocker.patch("kedro.server.http_server.is_debug_mode", return_value=False)
    mocker.patch("kedro.server.http_server.generate_timestamp", return_value="run-err")
    mocker.patch("kedro.server.http_server.load_obj", return_value=_FakeRunner)

    result = execute_pipeline(session)

    assert result.status == "failure"
    assert result.run_id == "run-err"
    assert result.error.type == "ValueError"
    assert result.error.message == "bad run"
    assert result.error.traceback is None


def test_execute_pipeline_failure_includes_traceback(mocker):
    """Test that execute_pipeline returns failure result and includes traceback when debug mode is on."""
    session = mocker.Mock()
    session.run.side_effect = RuntimeError("boom")

    mocker.patch("kedro.server.http_server.is_debug_mode", return_value=True)
    mocker.patch(
        "kedro.server.http_server.generate_timestamp", return_value="run-err-debug"
    )
    mocker.patch("kedro.server.http_server.load_obj", return_value=_FakeRunner)

    result = execute_pipeline(session)

    assert result.status == "failure"
    assert result.error.type == "RuntimeError"
    assert result.error.traceback is not None


def test_health_endpoint_with_lifespan(mocker, tmp_path):
    project_path = Path(tmp_path).resolve()
    mocker.patch("kedro.server.http_server.get_project_path", return_value=project_path)
    mock_bootstrap_project = mocker.patch("kedro.server.http_server.bootstrap_project")

    app = create_http_server()
    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["project_path"] == str(project_path)
    mock_bootstrap_project.assert_called_once_with(project_path)


def test_create_http_server_raises_on_bad_project_path(mocker, tmp_path):
    mocker.patch(
        "kedro.server.http_server.get_project_path",
        side_effect=RuntimeError("cannot resolve project"),
    )

    with pytest.raises(RuntimeError, match="cannot resolve project"):
        create_http_server()


def test_run_endpoint_reuses_service_session(mocker, tmp_path):
    project_path = Path(tmp_path).resolve()
    fake_session = mocker.Mock()
    mock_create_session = mocker.patch(
        "kedro.server.http_server.KedroServiceSession.create", return_value=fake_session
    )
    mocker.patch("kedro.server.http_server.get_project_path", return_value=project_path)
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


def test_run_endpoint_uses_factory_defaults(mocker, tmp_path):
    project_path = Path(tmp_path).resolve()
    fake_session = mocker.Mock()
    mock_create_session = mocker.patch(
        "kedro.server.http_server.KedroServiceSession.create", return_value=fake_session
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


def test_run_endpoint_uses_env_var_defaults(mocker, tmp_path, monkeypatch):
    project_path = Path(tmp_path).resolve()
    fake_session = mocker.Mock()
    mock_create_session = mocker.patch(
        "kedro.server.http_server.KedroServiceSession.create", return_value=fake_session
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


def test_run_endpoint_factory_defaults_override_env_vars(mocker, tmp_path, monkeypatch):
    project_path = Path(tmp_path).resolve()
    fake_session = mocker.Mock()
    mock_create_session = mocker.patch(
        "kedro.server.http_server.KedroServiceSession.create", return_value=fake_session
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


def test_run_endpoint_returns_error_detail_on_failure(mocker, tmp_path):
    project_path = Path(tmp_path).resolve()
    fake_session = mocker.Mock()

    mocker.patch(
        "kedro.server.http_server.KedroServiceSession.create", return_value=fake_session
    )
    mocker.patch("kedro.server.http_server.get_project_path", return_value=project_path)
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
