import uuid

import pytest

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

    # @pytest.mark.usefixture("mock_context_class")
    def test_load_context(self, fake_project, mock_context_class):
        session = KedroServiceSession.create(project_path=fake_project)
        context = session.load_context()
