import uuid

import pytest

from kedro.config.abstract_config import AbstractConfigLoader
from kedro.config.omegaconf_config import OmegaConfigLoader
from kedro.framework.context.context import KedroContext
from kedro.framework.session import KedroServiceSession


class TestKedroServiceSession:
    @pytest.mark.parametrize("env", [None, "test_env"])
    def test_create_session(self, fake_project, env):
        session = KedroServiceSession.create(
            project_path=fake_project,
            env=env,
        )
        assert uuid.UUID(session.session_id, version=4)
        assert session._project_path == fake_project.resolve()
        assert session.env == env
        assert session._conf_source == str(fake_project / "conf")

    def test_create_with_custom_session_id(self, fake_project):
        session_id = "my_session"
        session = KedroServiceSession.create(
            project_path=fake_project,
            session_id=session_id,
        )
        assert session.session_id == session_id

    def test_load_context(self, fake_project):
        session = KedroServiceSession.create(project_path=fake_project)
        context = session.load_context()
        config_loader = session._get_config_loader()
        assert isinstance(context, KedroContext)
        assert isinstance(config_loader, OmegaConfigLoader)
        assert context.config_loader == config_loader

    def test_load_context_with_runtime_params(self, fake_project):
        session = KedroServiceSession.create(project_path=fake_project)
        runtime_params = {"param1": "value1"}
        context = session.load_context(runtime_params=runtime_params)
        assert context.config_loader.runtime_params == runtime_params

    def test_load_context_with_envvar(self, fake_project, monkeypatch):
        monkeypatch.setenv("KEDRO_ENV", "my_fake_env")

        session = KedroServiceSession.create(fake_project)
        result = session.load_context()

        assert isinstance(result, KedroContext)
        assert result.__class__.__name__ == "KedroContext"
        assert result.env == "my_fake_env"

    def test_load_config_loader_with_envvar(self, fake_project, monkeypatch):
        monkeypatch.setenv("KEDRO_ENV", "my_fake_env")

        session = KedroServiceSession.create(fake_project)
        result = session._get_config_loader()

        assert isinstance(result, OmegaConfigLoader)
        assert result.__class__.__name__ == "OmegaConfigLoader"
        assert result.env == "my_fake_env"

    @pytest.mark.usefixtures("mock_settings_custom_context_class")
    def test_load_context_custom_context_class(self, fake_project):
        session = KedroServiceSession.create(fake_project)
        result = session.load_context()

        assert isinstance(result, KedroContext)
        assert result.__class__.__name__ == "MyContext"

    @pytest.mark.usefixtures("mock_settings_custom_config_loader_class")
    def test_load_config_loader_custom_config_loader_class(self, fake_project):
        session = KedroServiceSession.create(fake_project)
        result = session._get_config_loader()

        assert isinstance(result, AbstractConfigLoader)
        assert result.__class__.__name__ == "MyConfigLoader"
