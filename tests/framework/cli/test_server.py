import types

from click.testing import CliRunner

from kedro.server.utils import DEFAULT_HOST, DEFAULT_HTTP_PORT, KEDRO_PROJECT_PATH_ENV


class TestServerCommand:
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
        assert "KEDRO_SERVER_ENV" not in mock_environ
        assert "KEDRO_SERVER_CONF_SOURCE" not in mock_environ
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
        conf_source = fake_metadata.project_path / "conf"
        mocker.patch.dict(
            "sys.modules", {"uvicorn": types.SimpleNamespace(run=uvicorn_run)}
        )

        result = CliRunner().invoke(
            fake_project_cli,
            [
                "start",
                "--host",
                "2.2.2.2",
                "--port",
                "9000",
                "--reload",
                "--env",
                "local",
                "--conf-source",
                str(conf_source),
            ],
            obj=fake_metadata,
        )

        assert result.exit_code == 0, result.output
        assert mock_environ[KEDRO_PROJECT_PATH_ENV] == str(fake_metadata.project_path)
        assert mock_environ["KEDRO_SERVER_ENV"] == "local"
        assert mock_environ["KEDRO_SERVER_CONF_SOURCE"] == str(conf_source.resolve())
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
