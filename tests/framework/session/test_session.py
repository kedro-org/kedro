# Copyright 2020 QuantumBlack Visual Analytics Limited
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
import logging
import subprocess
from pathlib import Path
from time import sleep

import pytest
import toml

from kedro.framework.session import KedroSession, get_current_session
from kedro.framework.session.store import BaseSessionStore, ShelveStore

_FAKE_KEDRO_VERSION = "fake_kedro_version"
_FAKE_PACKAGE_NAME = "fake_package"
_FAKE_PIPELINE_NAME = "fake_pipeline"


@pytest.fixture
def mock_load_context(mocker):
    return mocker.patch("kedro.framework.session.session.load_context")


@pytest.fixture
def fake_session_id(mocker):
    session_id = "fake_session_id"
    mocker.patch(
        "kedro.framework.session.session.generate_timestamp", return_value=session_id
    )
    return session_id


@pytest.fixture
def fake_project(tmp_path, mock_load_context):  # pylint: disable=unused-argument
    fake_project_dir = Path(tmp_path) / "fake_project"
    (fake_project_dir / "src").mkdir(parents=True)

    pyproject_toml_path = fake_project_dir / "pyproject.toml"
    payload = {
        "tool": {
            "kedro": {
                "project_version": _FAKE_KEDRO_VERSION,
                "package_name": _FAKE_PACKAGE_NAME,
            }
        }
    }
    toml_str = toml.dumps(payload)
    pyproject_toml_path.write_text(toml_str)

    return fake_project_dir


class FakeException(Exception):
    """Fake exception class for testing purposes"""


SESSION_LOGGER_NAME = "kedro.framework.session.session"
STORE_LOGGER_NAME = "kedro.framework.session.store"


@pytest.mark.usefixtures("mock_load_context")
class TestKedroSession:
    @pytest.mark.parametrize("env", [None, "env1"])
    @pytest.mark.parametrize("extra_params", [None, {"key": "val"}])
    def test_create(
        self,
        fake_project,
        mock_load_context,
        fake_session_id,
        mocker,
        env,
        extra_params,
    ):
        mock_click_ctx = mocker.patch("click.get_current_context").return_value
        session = KedroSession.create(fake_project, env=env, extra_params=extra_params)

        expected_cli_data = {
            "args": mock_click_ctx.args,
            "params": mock_click_ctx.params,
            "command_name": mock_click_ctx.command.name,
            "command_path": mock_click_ctx.command_path,
        }
        expected_store = {
            "config_file": fake_project / "pyproject.toml",
            "project_path": fake_project,
            "source_dir": fake_project / "src",
            "session_id": fake_session_id,
            "project_version": _FAKE_KEDRO_VERSION,
            "package_name": _FAKE_PACKAGE_NAME,
            "cli": expected_cli_data,
        }
        if env:
            expected_store["env"] = env
        if extra_params:
            expected_store["extra_params"] = extra_params

        assert session.store == expected_store

        mock_load_context.assert_not_called()
        assert session.context is mock_load_context.return_value
        if extra_params:
            mock_load_context.assert_called_once_with(
                project_path=fake_project, env=env, **extra_params
            )
        else:
            mock_load_context.assert_called_once_with(
                project_path=fake_project, env=env
            )

    def test_create_no_env_extra_params(
        self, fake_project, mock_load_context, fake_session_id, mocker
    ):
        mock_click_ctx = mocker.patch("click.get_current_context").return_value
        session = KedroSession.create(fake_project)

        expected_cli_data = {
            "args": mock_click_ctx.args,
            "params": mock_click_ctx.params,
            "command_name": mock_click_ctx.command.name,
            "command_path": mock_click_ctx.command_path,
        }
        expected_store = {
            "config_file": fake_project / "pyproject.toml",
            "project_path": fake_project,
            "source_dir": fake_project / "src",
            "session_id": fake_session_id,
            "package_name": _FAKE_PACKAGE_NAME,
            "project_version": _FAKE_KEDRO_VERSION,
            "cli": expected_cli_data,
        }

        assert session.store == expected_store

        mock_load_context.assert_not_called()
        assert session.context is mock_load_context.return_value
        mock_load_context.assert_called_once_with(project_path=fake_project, env=None)

    def test_default_store(self, fake_project, fake_session_id, caplog):
        caplog.set_level(logging.WARN, logger="kedro.framework.session.store")

        session = KedroSession.create(fake_project)
        assert isinstance(session.store, dict)
        assert session._store.__class__ is BaseSessionStore
        assert session._store._path == (fake_project / "sessions").as_posix()
        assert session._store._session_id == fake_session_id
        session.close()
        expected_log_messages = [
            "`read()` not implemented for `BaseSessionStore`. Assuming empty store.",
            "`save()` not implemented for `BaseSessionStore`. Skipping the step.",
        ]
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.WARN
        ]
        assert actual_log_messages == expected_log_messages

    def test_shelve_store(self, fake_project, fake_session_id, caplog, mocker):
        mocker.patch("pathlib.Path.is_file", return_value=True)
        shelve_location = fake_project / "nested" / "sessions"
        session_store = {
            "type": "ShelveStore",
            "path": shelve_location.as_posix(),
        }
        fake_settings_module = mocker.Mock()
        fake_settings_module.SESSION_STORE = session_store
        fake_settings_module.DISABLE_HOOKS_FOR_PLUGINS = ()
        fake_settings_module.HOOKS = ()
        mocker.patch(
            "kedro.framework.context.context.import_module",
            return_value=fake_settings_module,
        )

        other = KedroSession.create(fake_project)
        assert other._store.__class__ is ShelveStore
        assert other._store._path == shelve_location.as_posix()
        assert other._store._location == shelve_location / fake_session_id / "store"
        assert other._store._session_id == fake_session_id
        assert not shelve_location.is_dir()

        other.close()  # session data persisted
        assert shelve_location.is_dir()
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.WARN
        ]
        assert not actual_log_messages

    @pytest.mark.parametrize("fake_git_status", ["dirty", ""])
    @pytest.mark.parametrize("fake_commit_hash", ["fake_commit_hash"])
    def test_git_describe(
        self, fake_project, fake_commit_hash, fake_git_status, mocker
    ):
        """Test that git information is added to the session store"""
        mocker.patch(
            "subprocess.check_output",
            side_effect=[fake_commit_hash.encode(), fake_git_status.encode()],
        )

        session = KedroSession.create(fake_project)
        expected_git_info = {
            "commit_sha": fake_commit_hash,
            "dirty": bool(fake_git_status),
        }
        assert session.store["git"] == expected_git_info

    @pytest.mark.parametrize(
        "exception",
        [
            subprocess.CalledProcessError(1, "fake command"),
            FileNotFoundError,
            NotADirectoryError,
        ],
    )
    def test_git_describe_error(self, fake_project, exception, mocker, caplog):
        """Test that git information is not added to the session store
        if call to git fails
        """
        mocker.patch("subprocess.check_output", side_effect=exception)
        session = KedroSession.create(fake_project)
        assert "git" not in session.store

        expected_log_messages = [f"Unable to git describe {fake_project}"]
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == SESSION_LOGGER_NAME and rec.levelno == logging.WARN
        ]
        assert actual_log_messages == expected_log_messages

    def test_log_error(self, fake_project):
        """Test logging the error by the session"""

        # test that the error is not swallowed by the session
        with pytest.raises(FakeException), KedroSession.create(fake_project) as session:
            raise FakeException

        exception = session.store["exception"]
        assert exception["type"] == "tests.framework.session.test_session.FakeException"
        assert exception["value"] == ""
        assert any(
            "raise FakeException" in tb_line for tb_line in exception["traceback"]
        )

    def test_get_current_session(self, fake_project):
        assert get_current_session(silent=True) is None  # no sessions yet

        pattern = "There is no active Kedro session"
        with pytest.raises(RuntimeError, match=pattern):
            get_current_session()

        # create a session, pull it from the stack
        with KedroSession.create(fake_project) as session:
            assert get_current_session() is session
            sleep(0.01)  # to make sure we don't generate the same session id
            with KedroSession.create(fake_project) as another:
                assert get_current_session() is another
                assert session.session_id != another.session_id
            assert get_current_session() is session

        # session has been closed, so no sessions left in the stack
        assert get_current_session(silent=True) is None

    @pytest.mark.parametrize("fake_pipeline_name", [None, _FAKE_PIPELINE_NAME])
    def test_run(
        self,
        fake_project,
        fake_session_id,
        fake_pipeline_name,
        mock_load_context,
        mocker,
    ):
        """Test running the project via the session"""

        mock_hook = mocker.patch(
            "kedro.framework.session.session.get_hook_manager"
        ).return_value.hook
        mock_context = mock_load_context.return_value
        mock_catalog = mock_context._get_catalog.return_value
        mock_runner = mocker.Mock()
        mock_pipeline = mock_context._filter_pipeline.return_value

        with KedroSession.create(fake_project) as session:
            session.run(runner=mock_runner, pipeline_name=fake_pipeline_name)

        record_data = {
            "run_id": fake_session_id,
            "project_path": fake_project.as_posix(),
            "env": mock_context.env,
            "kedro_version": _FAKE_KEDRO_VERSION,
            "tags": None,
            "from_nodes": None,
            "to_nodes": None,
            "node_names": None,
            "from_inputs": None,
            "load_versions": None,
            "extra_params": {},
            "pipeline_name": fake_pipeline_name,
        }

        mock_hook.before_pipeline_run.assert_called_once_with(
            run_params=record_data, pipeline=mock_pipeline, catalog=mock_catalog
        )
        mock_runner.run.assert_called_once_with(
            mock_pipeline, mock_catalog, fake_session_id
        )
        mock_hook.after_pipeline_run.assert_called_once_with(
            run_params=record_data,
            run_result=mock_runner.run.return_value,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    @pytest.mark.parametrize("fake_pipeline_name", [None, _FAKE_PIPELINE_NAME])
    def test_run_exception(
        self,
        fake_project,
        fake_session_id,
        fake_pipeline_name,
        mock_load_context,
        mocker,
    ):
        """Test exception being raise during the run"""
        mock_hook = mocker.patch(
            "kedro.framework.session.session.get_hook_manager"
        ).return_value.hook
        mock_context = mock_load_context.return_value
        mock_catalog = mock_context._get_catalog.return_value
        error = FakeException("You shall not pass!")
        mock_runner = mocker.Mock()
        mock_runner.run.side_effect = error  # runner.run() raises an error
        mock_pipeline = mock_context._filter_pipeline.return_value

        with pytest.raises(FakeException), KedroSession.create(fake_project) as session:
            session.run(runner=mock_runner, pipeline_name=fake_pipeline_name)

        record_data = {
            "run_id": fake_session_id,
            "project_path": fake_project.as_posix(),
            "env": mock_context.env,
            "kedro_version": _FAKE_KEDRO_VERSION,
            "tags": None,
            "from_nodes": None,
            "to_nodes": None,
            "node_names": None,
            "from_inputs": None,
            "load_versions": None,
            "extra_params": {},
            "pipeline_name": fake_pipeline_name,
        }

        mock_hook.on_pipeline_error.assert_called_once_with(
            error=error,
            run_params=record_data,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

        mock_hook.after_pipeline_run.assert_not_called()

        exception = session.store["exception"]
        assert exception["type"] == "tests.framework.session.test_session.FakeException"
        assert exception["value"] == "You shall not pass!"
        assert exception["traceback"]
