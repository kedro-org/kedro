import logging
from collections import namedtuple

import pytest
from dynaconf.validator import Validator

from kedro.framework.hooks.manager import _register_hooks
from kedro.framework.project import _ProjectSettings
from kedro.framework.session import KedroSession
from tests.framework.session.conftest import _mock_imported_settings_paths

MockDistInfo = namedtuple("MockDistInfo", ["project_name", "version"])


@pytest.fixture
def naughty_plugin():
    return MockDistInfo("test-project-a", "0.1")


@pytest.fixture
def good_plugin():
    return MockDistInfo("test-project-b", "0.2")


@pytest.fixture
def mock_settings_with_disabled_hooks(mocker, project_hooks, naughty_plugin):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(project_hooks,))
        _DISABLE_HOOKS_FOR_PLUGINS = Validator(
            "DISABLE_HOOKS_FOR_PLUGINS", default=(naughty_plugin.project_name,)
        )

    _mock_imported_settings_paths(mocker, MockSettings())


class TestSessionHookManager:
    """Test the process of registering hooks with the hook manager in a session."""

    @pytest.mark.nologreset
    def test_assert_register_hooks(self, project_hooks, mock_session):
        hook_manager = mock_session._hook_manager
        assert hook_manager.is_registered(project_hooks)

    @pytest.mark.usefixtures("mock_session")
    @pytest.mark.nologreset
    def test_calling_register_hooks_twice(self, project_hooks, mock_session):
        """Calling hook registration multiple times should not raise"""
        hook_manager = mock_session._hook_manager

        assert hook_manager.is_registered(project_hooks)
        _register_hooks(hook_manager, (project_hooks,))
        _register_hooks(hook_manager, (project_hooks,))
        assert hook_manager.is_registered(project_hooks)

    @pytest.mark.parametrize("num_plugins", [0, 1])
    @pytest.mark.nologreset
    def test_hooks_registered_when_session_created(
        self, mocker, request, caplog, project_hooks, num_plugins
    ):
        caplog.set_level(logging.DEBUG, logger="kedro")
        load_setuptools_entrypoints = mocker.patch(
            "pluggy._manager.PluginManager.load_setuptools_entrypoints",
            return_value=num_plugins,
        )
        distinfo = [("plugin_obj_1", MockDistInfo("test-project-a", "0.1"))]
        list_distinfo_mock = mocker.patch(
            "pluggy._manager.PluginManager.list_plugin_distinfo", return_value=distinfo
        )

        # call a fixture which creates a session
        session = request.getfixturevalue("mock_session")
        hook_manager = session._hook_manager
        assert hook_manager.is_registered(project_hooks)

        load_setuptools_entrypoints.assert_called_once_with("kedro.hooks")
        list_distinfo_mock.assert_called_once_with()

        if num_plugins:
            log_messages = [record.getMessage() for record in caplog.records]
            plugin = f"{distinfo[0][1].project_name}-{distinfo[0][1].version}"
            expected_msg = (
                f"Registered hooks from {num_plugins} installed plugin(s): {plugin}"
            )
            assert expected_msg in log_messages

    @pytest.mark.usefixtures("mock_settings_with_disabled_hooks")
    @pytest.mark.nologreset
    def test_disabling_auto_discovered_hooks(
        self,
        mocker,
        caplog,
        tmp_path,
        mock_package_name,
        naughty_plugin,
        good_plugin,
    ):
        caplog.set_level(logging.DEBUG, logger="kedro")

        distinfo = [("plugin_obj_1", naughty_plugin), ("plugin_obj_2", good_plugin)]
        mocked_distinfo = mocker.patch(
            "pluggy._manager.PluginManager.list_plugin_distinfo", return_value=distinfo
        )

        mocker.patch(
            "pluggy._manager.PluginManager.load_setuptools_entrypoints",
            return_value=len(distinfo),
        )
        unregister_mock = mocker.patch("pluggy._manager.PluginManager.unregister")

        # create a session that will use the mock_settings_with_disabled_hooks from the fixture.
        KedroSession.create(
            mock_package_name, tmp_path, extra_params={"params:key": "value"}
        )

        mocked_distinfo.assert_called_once_with()
        unregister_mock.assert_called_once_with(plugin=distinfo[0][0])

        # check the logs
        log_messages = [record.getMessage() for record in caplog.records]
        expected_msg = (
            f"Registered hooks from 1 installed plugin(s): "
            f"{good_plugin.project_name}-{good_plugin.version}"
        )
        assert expected_msg in log_messages

        expected_msg = (
            f"Hooks are disabled for plugin(s): "
            f"{naughty_plugin.project_name}-{naughty_plugin.version}"
        )
        assert expected_msg in log_messages
