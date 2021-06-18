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
import json
import logging
import re
import subprocess
import textwrap
from pathlib import Path
from typing import Iterable

import pytest
import toml

from kedro import __version__ as kedro_version
from kedro.config import ConfigLoader
from kedro.framework.context import KedroContext, KedroContextError
from kedro.framework.hooks import hook_impl
from kedro.framework.project import (
    ValidationError,
    Validator,
    _ProjectSettings,
    configure_project,
)
from kedro.framework.session import KedroSession, get_current_session
from kedro.framework.session.store import BaseSessionStore, ShelveStore

_FAKE_PACKAGE_NAME = "fake_package"
_FAKE_PROJECT_NAME = "fake_project"
_FAKE_PIPELINE_NAME = "fake_pipeline"


class BadStore:  # pylint: disable=too-few-public-methods
    """
    Store class that doesn't subclass `BaseSessionStore`, for testing only.
    """


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture
def mock_context_class(mocker):
    return mocker.patch("kedro.framework.session.session.KedroContext", autospec=True)


class ConfigLoaderHooks:
    @hook_impl
    def register_config_loader(self, conf_paths: Iterable[str]) -> ConfigLoader:
        return ConfigLoader(conf_paths)


def _mock_imported_settings_paths(mocker, mock_settings):
    for path in [
        "kedro.framework.project.settings",
        "kedro.framework.session.session.settings",
        "kedro.framework.context.context.settings",
    ]:
        mocker.patch(path, mock_settings)
    return mock_settings


@pytest.fixture
def mock_settings(mocker):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(ConfigLoaderHooks(),))

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_context_class(mocker, mock_context_class):
    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(ConfigLoaderHooks(),))
        _CONTEXT_CLASS = Validator(
            "CONTEXT_CLASS", default=lambda *_: mock_context_class
        )

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_custom_context_class(mocker):
    class MyContext(KedroContext):
        pass

    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(ConfigLoaderHooks(),))
        _CONTEXT_CLASS = Validator("CONTEXT_CLASS", default=lambda *_: MyContext)

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_file_bad_session_store_class(tmpdir):
    mock_settings_file = tmpdir.join("mock_settings_file.py")
    mock_settings_file.write(
        textwrap.dedent(
            f"""
            from {__name__} import BadStore
            SESSION_STORE_CLASS = BadStore
            """
        )
    )
    return mock_settings_file


@pytest.fixture
def mock_settings_bad_session_store_args(mocker):
    class MockSettings(_ProjectSettings):
        _SESSION_STORE_ARGS = Validator(
            "SESSION_STORE_ARGS", default={"wrong_arg": "O_o"}
        )

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def mock_settings_uncaught_session_store_exception(mocker):
    class MockSettings(_ProjectSettings):
        _SESSION_STORE_ARGS = Validator("SESSION_STORE_ARGS", default={"path": "path"})

    _mock_imported_settings_paths(mocker, MockSettings())
    return mocker.patch.object(
        BaseSessionStore, "__init__", side_effect=Exception("Fake")
    )


@pytest.fixture
def mock_settings_shelve_session_store(mocker, fake_project):
    shelve_location = fake_project / "nested" / "sessions"

    class MockSettings(_ProjectSettings):
        _HOOKS = Validator("HOOKS", default=(ConfigLoaderHooks(),))
        _SESSION_STORE_CLASS = Validator(
            "SESSION_STORE_CLASS", default=lambda *_: ShelveStore
        )
        _SESSION_STORE_ARGS = Validator(
            "SESSION_STORE_ARGS", default={"path": shelve_location.as_posix()}
        )

    return _mock_imported_settings_paths(mocker, MockSettings())


@pytest.fixture
def fake_session_id(mocker):
    session_id = "fake_session_id"
    mocker.patch(
        "kedro.framework.session.session.generate_timestamp", return_value=session_id
    )
    return session_id


@pytest.fixture
def local_logging_config():
    return {
        "version": 1,
        "formatters": {
            "simple": {"format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"}
        },
        "root": {"level": "INFO", "handlers": ["console"]},
        "loggers": {
            "kedro": {"level": "INFO", "handlers": ["console"], "propagate": False}
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": "INFO",
                "formatter": "simple",
                "stream": "ext://sys.stdout",
            }
        },
        "info_file_handler": {
            "class": "logging.handlers.RotatingFileHandler",
            "level": "INFO",
            "formatter": "simple",
            "filename": "logs/info.log",
        },
    }


@pytest.fixture
def fake_project(mocker, tmp_path, local_logging_config):
    fake_project_dir = Path(tmp_path) / "fake_project"
    (fake_project_dir / "src").mkdir(parents=True)

    pyproject_toml_path = fake_project_dir / "pyproject.toml"
    payload = {
        "tool": {
            "kedro": {
                "project_version": kedro_version,
                "project_name": _FAKE_PROJECT_NAME,
                "package_name": _FAKE_PACKAGE_NAME,
            }
        }
    }
    toml_str = toml.dumps(payload)
    pyproject_toml_path.write_text(toml_str)

    env_logging = fake_project_dir / "conf" / "base" / "logging.yml"
    env_logging.parent.mkdir(parents=True)
    env_logging.write_text(json.dumps(local_logging_config))
    (fake_project_dir / "conf" / "local").mkdir()

    mocker.patch("kedro.framework.project._validate_module")
    return fake_project_dir


class FakeException(Exception):
    """Fake exception class for testing purposes"""


SESSION_LOGGER_NAME = "kedro.framework.session.session"
STORE_LOGGER_NAME = "kedro.framework.session.store"


class TestKedroSession:
    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("env", [None, "env1"])
    @pytest.mark.parametrize("extra_params", [None, {"key": "val"}])
    def test_create(
        self,
        fake_project,
        mock_context_class,
        fake_session_id,
        mocker,
        env,
        extra_params,
    ):
        mock_click_ctx = mocker.patch("click.get_current_context").return_value
        session = KedroSession.create(
            _FAKE_PACKAGE_NAME, fake_project, env=env, extra_params=extra_params
        )

        expected_cli_data = {
            "args": mock_click_ctx.args,
            "params": mock_click_ctx.params,
            "command_name": mock_click_ctx.command.name,
            "command_path": mock_click_ctx.command_path,
        }
        expected_store = {
            "project_path": fake_project,
            "session_id": fake_session_id,
            "package_name": _FAKE_PACKAGE_NAME,
            "cli": expected_cli_data,
        }
        if env:
            expected_store["env"] = env
        if extra_params:
            expected_store["extra_params"] = extra_params

        assert session.store == expected_store
        # called for logging setup
        mock_context_class.assert_called_once_with(
            project_path=fake_project,
            package_name=_FAKE_PACKAGE_NAME,
            env=env,
            extra_params=extra_params,
        )

        assert session.load_context() is mock_context_class.return_value

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_create_no_env_extra_params(
        self, fake_project, mock_context_class, fake_session_id, mocker
    ):
        mock_click_ctx = mocker.patch("click.get_current_context").return_value
        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)

        expected_cli_data = {
            "args": mock_click_ctx.args,
            "params": mock_click_ctx.params,
            "command_name": mock_click_ctx.command.name,
            "command_path": mock_click_ctx.command_path,
        }
        expected_store = {
            "project_path": fake_project,
            "session_id": fake_session_id,
            "package_name": _FAKE_PACKAGE_NAME,
            "cli": expected_cli_data,
        }

        assert session.store == expected_store
        mock_context_class.assert_called_once_with(
            project_path=fake_project,
            package_name=_FAKE_PACKAGE_NAME,
            env=None,
            extra_params=None,
        )

        assert session.load_context() is mock_context_class.return_value

    @pytest.mark.usefixtures("mock_settings")
    def test_load_context_with_envvar(self, fake_project, monkeypatch, mocker):
        mocker.patch("kedro.config.config.ConfigLoader.get")
        monkeypatch.setenv("KEDRO_ENV", "my_fake_env")

        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
        result = session.load_context()

        assert isinstance(result, KedroContext)
        assert result.__class__.__name__ == "KedroContext"
        assert result.env == "my_fake_env"

    @pytest.mark.usefixtures("mock_settings_custom_context_class")
    def test_load_context_custom_context_class(self, fake_project):
        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
        result = session.load_context()

        assert isinstance(result, KedroContext)
        assert result.__class__.__name__ == "MyContext"

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_default_store(self, fake_project, fake_session_id, caplog):
        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
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
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.INFO
        ]
        assert actual_log_messages == expected_log_messages

    @pytest.mark.usefixtures("mock_settings_shelve_session_store")
    def test_shelve_store(self, fake_project, fake_session_id, caplog, mocker):
        mocker.patch("pathlib.Path.is_file", return_value=True)
        shelve_location = fake_project / "nested" / "sessions"
        other = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
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
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.INFO
        ]
        assert not actual_log_messages

    def test_wrong_store_type(self, mock_settings_file_bad_session_store_class):
        pattern = (
            "Invalid value `tests.framework.session.test_session.BadStore` received "
            "for setting `SESSION_STORE_CLASS`. "
            "It must be a subclass of `kedro.framework.session.store.BaseSessionStore`."
        )
        mock_settings = _ProjectSettings(
            settings_file=str(mock_settings_file_bad_session_store_class)
        )
        with pytest.raises(ValidationError, match=re.escape(pattern)):
            # accessing the setting attribute will cause it to be evaluated and therefore validated
            assert mock_settings.SESSION_STORE_CLASS

    @pytest.mark.usefixtures("mock_settings_bad_session_store_args")
    def test_wrong_store_args(self, fake_project):
        classpath = f"{BaseSessionStore.__module__}.{BaseSessionStore.__qualname__}"
        pattern = (
            f"Store config must only contain arguments valid for "
            f"the constructor of `{classpath}`."
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)

    def test_store_uncaught_error(
        self,
        fake_project,
        fake_session_id,
        mock_settings_uncaught_session_store_exception,
    ):
        classpath = f"{BaseSessionStore.__module__}.{BaseSessionStore.__qualname__}"
        pattern = f"Failed to instantiate session store of type `{classpath}`."
        with pytest.raises(ValueError, match=re.escape(pattern)):
            KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)

        mock_settings_uncaught_session_store_exception.assert_called_once_with(
            path="path", session_id=fake_session_id
        )

    @pytest.mark.usefixtures("mock_settings")
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

        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
        expected_git_info = {
            "commit_sha": fake_commit_hash,
            "dirty": bool(fake_git_status),
        }
        assert session.store["git"] == expected_git_info

    @pytest.mark.usefixtures("mock_settings")
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
        session = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
        assert "git" not in session.store

        expected_log_messages = [f"Unable to git describe {fake_project}"]
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == SESSION_LOGGER_NAME and rec.levelno == logging.WARN
        ]
        assert actual_log_messages == expected_log_messages

    @pytest.mark.usefixtures("mock_settings")
    def test_log_error(self, fake_project):
        """Test logging the error by the session"""
        # test that the error is not swallowed by the session
        with pytest.raises(FakeException), KedroSession.create(
            _FAKE_PACKAGE_NAME, fake_project
        ) as session:
            raise FakeException

        exception = session.store["exception"]
        assert exception["type"] == "tests.framework.session.test_session.FakeException"
        assert exception["value"] == ""
        assert any(
            "raise FakeException" in tb_line for tb_line in exception["traceback"]
        )

    @pytest.mark.usefixtures("mock_settings")
    def test_get_current_session(self, fake_project, mocker):
        assert get_current_session(silent=True) is None  # no sessions yet

        pattern = "There is no active Kedro session"
        with pytest.raises(RuntimeError, match=pattern):
            get_current_session()

        mocker.patch("kedro.framework.project._validate_module")
        configure_project(_FAKE_PACKAGE_NAME)
        session1 = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)
        session2 = KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)

        with session1:
            assert get_current_session() is session1

            pattern = (
                "Cannot activate the session as another active session already exists"
            )
            with pytest.raises(RuntimeError, match=pattern), session2:
                pass  # pragma: no cover

        # session has been closed, so no current sessions should be available
        assert get_current_session(silent=True) is None

        with session2:
            assert get_current_session() is session2

    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("fake_pipeline_name", [None, _FAKE_PIPELINE_NAME])
    def test_run(
        self,
        fake_project,
        fake_session_id,
        fake_pipeline_name,
        mock_context_class,
        mocker,
    ):
        """Test running the project via the session"""

        mock_hook = mocker.patch(
            "kedro.framework.session.session.get_hook_manager"
        ).return_value.hook
        mock_pipelines = {
            _FAKE_PIPELINE_NAME: mocker.Mock(),
            "__default__": mocker.Mock(),
        }
        mocker.patch(
            "kedro.framework.session.session.pipelines", return_value=mock_pipelines
        )
        mock_context = mock_context_class.return_value
        mock_catalog = mock_context._get_catalog.return_value
        mock_runner = mocker.Mock()
        mock_pipeline = mock_context._filter_pipeline.return_value

        with KedroSession.create(_FAKE_PACKAGE_NAME, fake_project) as session:
            session.run(runner=mock_runner, pipeline_name=fake_pipeline_name)

        record_data = {
            "run_id": fake_session_id,
            "project_path": fake_project.as_posix(),
            "env": mock_context.env,
            "kedro_version": kedro_version,
            "tags": None,
            "from_nodes": None,
            "to_nodes": None,
            "node_names": None,
            "from_inputs": None,
            "to_outputs": None,
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

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_run_non_existent_pipeline(self, fake_project, mocker):
        mock_runner = mocker.Mock()

        pattern = (
            "Failed to find the pipeline named 'doesnotexist'. "
            "It needs to be generated and returned "
            "by the 'register_pipelines' function."
        )
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            with KedroSession.create(_FAKE_PACKAGE_NAME, fake_project) as session:
                session.run(runner=mock_runner, pipeline_name="doesnotexist")

    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("fake_pipeline_name", [None, _FAKE_PIPELINE_NAME])
    def test_run_exception(  # pylint: disable=too-many-locals
        self,
        fake_project,
        fake_session_id,
        fake_pipeline_name,
        mock_context_class,
        mocker,
    ):
        """Test exception being raise during the run"""
        mock_hook = mocker.patch(
            "kedro.framework.session.session.get_hook_manager"
        ).return_value.hook
        mock_pipelines = {
            _FAKE_PIPELINE_NAME: mocker.Mock(),
            "__default__": mocker.Mock(),
        }
        mocker.patch(
            "kedro.framework.session.session.pipelines", return_value=mock_pipelines
        )
        mock_context = mock_context_class.return_value
        mock_catalog = mock_context._get_catalog.return_value
        error = FakeException("You shall not pass!")
        mock_runner = mocker.Mock()
        mock_runner.run.side_effect = error  # runner.run() raises an error
        mock_pipeline = mock_context._filter_pipeline.return_value

        with pytest.raises(FakeException), KedroSession.create(
            _FAKE_PACKAGE_NAME, fake_project
        ) as session:
            session.run(runner=mock_runner, pipeline_name=fake_pipeline_name)

        record_data = {
            "run_id": fake_session_id,
            "project_path": fake_project.as_posix(),
            "env": mock_context.env,
            "kedro_version": kedro_version,
            "tags": None,
            "from_nodes": None,
            "to_nodes": None,
            "node_names": None,
            "from_inputs": None,
            "to_outputs": None,
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


@pytest.mark.usefixtures("mock_settings")
def test_setup_logging_using_absolute_path(fake_project, mocked_logging):
    KedroSession.create(_FAKE_PACKAGE_NAME, fake_project)

    mocked_logging.assert_called_once()
    call_args = mocked_logging.call_args[0][0]

    expected_log_filepath = (fake_project / "logs" / "info.log").as_posix()
    actual_log_filepath = call_args["info_file_handler"]["filename"]
    assert actual_log_filepath == expected_log_filepath
