# Copyright 2021 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
from collections import namedtuple

import pytest
from dynaconf.validator import Validator

from kedro.framework.hooks.manager import _register_hooks, get_hook_manager
from kedro.framework.project import _ProjectSettings
from kedro.framework.session import KedroSession
from tests.framework.session.conftest import _mock_imported_settings_paths

MockDistInfo = namedtuple("Distinfo", ["project_name", "version"])


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

    def test_assert_register_hooks(self, request, project_hooks):
        hook_manager = get_hook_manager()
        assert not hook_manager.is_registered(project_hooks)

        # call the fixture to construct the session
        request.getfixturevalue("mock_session")

        assert hook_manager.is_registered(project_hooks)

    @pytest.mark.usefixtures("mock_session")
    def test_calling_register_hooks_twice(self, project_hooks):
        """Calling hook registration multiple times should not raise"""
        hook_manager = get_hook_manager()

        assert hook_manager.is_registered(project_hooks)
        _register_hooks(hook_manager, (project_hooks,))
        _register_hooks(hook_manager, (project_hooks,))
        assert hook_manager.is_registered(project_hooks)

    @pytest.mark.parametrize("num_plugins", [0, 1])
    def test_hooks_registered_when_session_created(
        self, mocker, request, caplog, project_hooks, num_plugins
    ):
        hook_manager = get_hook_manager()
        assert not hook_manager.get_plugins()

        load_setuptools_entrypoints = mocker.patch.object(
            hook_manager, "load_setuptools_entrypoints", return_value=num_plugins
        )
        distinfo = [("plugin_obj_1", MockDistInfo("test-project-a", "0.1"))]
        list_distinfo_mock = mocker.patch.object(
            hook_manager, "list_plugin_distinfo", return_value=distinfo
        )

        # call a fixture which creates a session
        request.getfixturevalue("mock_session")
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
    def test_disabling_auto_discovered_hooks(
        self, mocker, caplog, tmp_path, mock_package_name, naughty_plugin, good_plugin,
    ):
        hook_manager = get_hook_manager()
        assert not hook_manager.get_plugins()

        distinfo = [("plugin_obj_1", naughty_plugin), ("plugin_obj_2", good_plugin)]
        list_distinfo_mock = mocker.patch.object(
            hook_manager, "list_plugin_distinfo", return_value=distinfo
        )
        mocker.patch.object(
            hook_manager, "load_setuptools_entrypoints", return_value=len(distinfo)
        )
        unregister_mock = mocker.patch.object(hook_manager, "unregister")

        KedroSession.create(
            mock_package_name, tmp_path, extra_params={"params:key": "value"}
        )
        list_distinfo_mock.assert_called_once_with()
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
