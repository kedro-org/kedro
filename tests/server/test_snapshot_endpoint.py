from fastapi.testclient import TestClient

from kedro.inspection.models import (
    DatasetSnapshot,
    NodeSnapshot,
    NodeSourceSnapshot,
    PipelineSnapshot,
    ProjectMetadataSnapshot,
    ProjectSnapshot,
)


def _make_snapshot() -> ProjectSnapshot:
    """Return a minimal but fully-populated ProjectSnapshot for tests."""
    return ProjectSnapshot(
        metadata=ProjectMetadataSnapshot(
            project_name="test_project",
            package_name="test_pkg",
            kedro_version="1.0.0",
        ),
        pipelines=[
            PipelineSnapshot(
                name="__default__",
                nodes=[
                    NodeSnapshot(
                        name="my_node",
                        namespace="ns",
                        tags=["tag1"],
                        inputs=["raw_data"],
                        outputs=["processed"],
                    )
                ],
                inputs=["raw_data"],
                outputs=["processed"],
            )
        ],
        datasets={
            "raw_data": DatasetSnapshot(
                name="raw_data",
                type="pandas.CSVDataset",
                filepath="/data/raw.csv",
            )
        },
        parameters=["learning_rate", "epochs"],
    )


class TestSnapshotEndpoint:
    """Test GET /snapshot via TestClient."""

    def test_snapshot_returns_200_with_success_status(self, mocker, make_http_server):
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot(),
        )
        with TestClient(app) as client:
            response = client.get("/snapshot")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_snapshot_response_contains_all_fields(self, mocker, make_http_server):
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot(),
        )
        with TestClient(app) as client:
            payload = client.get("/snapshot").json()

        meta = payload["metadata"]
        assert meta["project_name"] == "test_project"
        assert meta["package_name"] == "test_pkg"
        assert meta["kedro_version"] == "1.0.0"

        pipelines = payload["pipelines"]
        assert len(pipelines) == 1
        assert pipelines[0]["name"] == "__default__"
        assert pipelines[0]["nodes"][0]["name"] == "my_node"

        assert "raw_data" in payload["datasets"]
        assert payload["datasets"]["raw_data"]["type"] == "pandas.CSVDataset"

        assert payload["parameters"] == ["learning_rate", "epochs"]

    def test_snapshot_uses_server_env(self, mocker, make_http_server):
        app = make_http_server(env="staging")
        mock_get = mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot(),
        )
        with TestClient(app) as client:
            client.get("/snapshot")
        assert mock_get.call_args[1]["env"] == "staging"

    def test_snapshot_returns_failure_status_on_exception(
        self, mocker, make_http_server
    ):
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            side_effect=RuntimeError("project not found"),
        )
        with TestClient(app) as client:
            response = client.get("/snapshot")
        assert response.status_code == 200
        payload = response.json()
        assert payload["status"] == "failure"
        assert payload["error"]["type"] == "RuntimeError"
        assert payload["error"]["message"] == "project not found"

    def test_snapshot_failure_response_has_no_data_fields(
        self, mocker, make_http_server
    ):
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            side_effect=ValueError("bad env"),
        )
        with TestClient(app) as client:
            payload = client.get("/snapshot").json()
        assert "metadata" not in payload
        assert "pipelines" not in payload
        assert "datasets" not in payload
        assert "parameters" not in payload

    def test_snapshot_passes_conf_source_to_get_project_snapshot(
        self, mocker, make_http_server
    ):
        mock_get = mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot(),
        )
        app = make_http_server(conf_source="conf/custom")
        with TestClient(app) as client:
            client.get("/snapshot")
        assert mock_get.call_args[1]["conf_source"] == "conf/custom"

    def test_snapshot_passes_metadata_from_app_state_to_get_project_snapshot(
        self, mocker, make_http_server
    ):
        mock_get = mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot(),
        )
        app = make_http_server()
        with TestClient(app) as client:
            client.get("/snapshot")
        assert (
            mock_get.call_args[1]["metadata"]
            is make_http_server.mock_bootstrap.return_value
        )

    def test_node_source_endpoint_returns_source_snapshot(
        self, mocker, make_http_server
    ):
        source = NodeSourceSnapshot(
            name="my_node",
            func_name="my_func",
            source_filepath="src/test_pkg/nodes.py",
            source_line_start=10,
            source_line_end=12,
            code="def my_func(x):\n    return x\n",
        )
        mock_get = mocker.patch(
            "kedro.server.http_server.get_node_source", return_value=source
        )
        app = make_http_server()
        with TestClient(app) as client:
            payload = client.get("/snapshot/nodes/my_node/source").json()
        assert payload["status"] == "success"
        assert payload["source"]["name"] == "my_node"
        assert payload["source"]["code"] == "def my_func(x):\n    return x\n"
        mock_get.assert_called_once_with(
            node_name="my_node",
            env=None,
            conf_source=None,
            metadata=make_http_server.mock_bootstrap.return_value,
            include_code=True,
        )

    def test_node_source_endpoint_forwards_include_code_false(
        self, mocker, make_http_server
    ):
        source = NodeSourceSnapshot(
            name="my_node",
            func_name="my_func",
            source_filepath="src/test_pkg/nodes.py",
        )
        mock_get = mocker.patch(
            "kedro.server.http_server.get_node_source", return_value=source
        )
        app = make_http_server()
        with TestClient(app) as client:
            client.get("/snapshot/nodes/my_node/source?include_code=false")
        assert mock_get.call_args[1]["include_code"] is False

    def test_node_source_endpoint_uses_server_env_and_conf_source(
        self, mocker, make_http_server
    ):
        source = NodeSourceSnapshot(name="my_node")
        mock_get = mocker.patch(
            "kedro.server.http_server.get_node_source", return_value=source
        )
        app = make_http_server(env="staging", conf_source="conf/custom")
        with TestClient(app) as client:
            client.get("/snapshot/nodes/my_node/source")
        assert mock_get.call_args[1]["env"] == "staging"
        assert mock_get.call_args[1]["conf_source"] == "conf/custom"

    def test_node_source_endpoint_returns_failure_on_exception(
        self, mocker, make_http_server
    ):
        mock_get = mocker.patch(
            "kedro.server.http_server.get_node_source",
            side_effect=KeyError("my_node"),
        )
        app = make_http_server()
        with TestClient(app) as client:
            payload = client.get("/snapshot/nodes/my_node/source").json()
        assert payload["status"] == "failure"
        assert payload["error"]["type"] == "KeyError"
        assert "my_node" in payload["error"]["message"]
