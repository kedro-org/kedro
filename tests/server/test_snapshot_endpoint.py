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
                        func_name="process_data",
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


def _make_snapshot_with_node_source() -> ProjectSnapshot:
    """Return a project snapshot whose node includes source location metadata."""
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
                        func_name="process_data",
                        inputs=["raw_data"],
                        outputs=["processed"],
                        source=NodeSourceSnapshot(
                            filepath="src/pkg/pipelines/nodes.py",
                            line_start=10,
                            line_end=25,
                        ),
                    )
                ],
                inputs=["raw_data"],
                outputs=["processed"],
            )
        ],
        datasets={},
        parameters=[],
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
        assert pipelines[0]["nodes"][0]["func_name"] == "process_data"

        assert "raw_data" in payload["datasets"]
        assert payload["datasets"]["raw_data"]["type"] == "pandas.CSVDataset"

        assert payload["parameters"] == ["learning_rate", "epochs"]

    def test_snapshot_serializes_node_source_metadata(self, mocker, make_http_server):
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=_make_snapshot_with_node_source(),
        )
        with TestClient(app) as client:
            node = client.get("/snapshot").json()["pipelines"][0]["nodes"][0]

        assert node["source"] == {
            "filepath": "src/pkg/pipelines/nodes.py",
            "line_start": 10,
            "line_end": 25,
        }

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

    def test_snapshot_dataset_filepath_redacts_credentials_and_query(
        self, mocker, make_http_server
    ):
        """Dataset filepaths in a successful snapshot must not leak
        authority credentials, signed URL query parameters, or fragments.
        """
        snapshot = _make_snapshot()
        # Mirrors how the real snapshot-building path constructs
        # DatasetSnapshot entries from raw catalog config.
        snapshot.datasets["signed_data"] = DatasetSnapshot.from_config(
            "signed_data",
            {
                "type": "pandas.CSVDataset",
                "filepath": (
                    "https://user:pass@example.com/bucket/file.csv"  # pragma: allowlist secret
                    "?X-Amz-Signature=verysecretsig#frag"
                ),
            },
        )
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            return_value=snapshot,
        )
        with TestClient(app) as client:
            payload = client.get("/snapshot").json()

        filepath = payload["datasets"]["signed_data"]["filepath"]
        assert "pass" not in filepath
        assert "verysecretsig" not in filepath
        assert "frag" not in filepath
        assert "<redacted>" in filepath

    def test_snapshot_failure_message_redacts_credentials_from_exception(
        self, mocker, make_http_server, caplog
    ):
        """A third-party exception raised while building the snapshot must
        not leak dataset credentials in the response or in server logs."""
        app = make_http_server()
        mocker.patch(
            "kedro.server.http_server.get_project_snapshot",
            side_effect=RuntimeError(
                "Could not reach https://user:pass@example.com/bucket/file.csv"  # pragma: allowlist secret
                "?X-Amz-Signature=verysecretsig"
            ),
        )
        with TestClient(app) as client:
            response = client.get("/snapshot")

        payload = response.json()
        assert payload["status"] == "failure"
        assert "verysecretsig" not in payload["error"]["message"]
        assert "pass" not in payload["error"]["message"]
        assert "<redacted>" in payload["error"]["message"]
        assert "verysecretsig" not in caplog.text
        assert "pass" not in caplog.text
