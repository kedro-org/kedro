import logging
import re
import uuid

import pytest

from kedro import __version__ as kedro_version
from kedro.config.abstract_config import AbstractConfigLoader
from kedro.config.omegaconf_config import OmegaConfigLoader
from kedro.framework.context.context import KedroContext
from kedro.framework.project import (
    LOGGING,
    ValidationError,
    _ProjectSettings,
)
from kedro.framework.session import KedroServiceSession
from kedro.framework.session.abstract_session import KedroSessionError

_FAKE_PIPELINE_NAME = "fake_pipeline"


@pytest.fixture
def fake_run_id(mocker):
    run_id = "fake_run_id"
    mocker.patch(
        "kedro.framework.session.service_session.generate_timestamp",
        return_value=run_id,
    )
    return run_id


class FakeException(Exception):
    """Fake exception class for testing purposes"""


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

    @pytest.mark.usefixtures("mock_settings_config_loader_args")
    def test_load_config_loader_args(self, fake_project, mocker):
        session = KedroServiceSession.create(fake_project)
        result = session._get_config_loader()

        assert isinstance(result, OmegaConfigLoader)
        assert result.config_patterns["catalog"] == [
            "catalog*",
            "catalog*/**",
            "**/catalog*",
        ]
        assert result.config_patterns["spark"] == ["spark/*"]
        mocker.patch(
            "kedro.config.OmegaConfigLoader.__getitem__",
            return_value=["spark/*"],
        )
        assert result["spark"] == ["spark/*"]

    @pytest.mark.usefixtures("mock_settings_config_loader_args")
    def test_config_loader_args_no_env_overwrites_env(self, fake_project, mocker):
        session = KedroServiceSession.create(fake_project)
        result = session._get_config_loader()

        assert isinstance(result, OmegaConfigLoader)
        assert result.base_env == ""
        assert result.default_run_env == ""

    @pytest.mark.usefixtures("mock_settings_config_loader_args_env")
    def test_config_loader_args_overwrite_env(self, fake_project, mocker):
        session = KedroServiceSession.create(fake_project)
        result = session._get_config_loader()

        assert isinstance(result, OmegaConfigLoader)
        assert result.base_env == "something_new"
        assert result.default_run_env == ""

    def test_broken_config_loader(self, mock_settings_file_bad_config_loader_class):
        pattern = (
            "Invalid value 'tests.framework.session.conftest.BadConfigLoader' received "
            "for setting 'CONFIG_LOADER_CLASS'. "
            "It must be a subclass of 'kedro.config.abstract_config.AbstractConfigLoader'."
        )
        mock_settings = _ProjectSettings(
            settings_file=str(mock_settings_file_bad_config_loader_class)
        )
        with pytest.raises(ValidationError, match=re.escape(pattern)):
            assert mock_settings.CONFIG_LOADER_CLASS

    def test_logging_is_not_reconfigure(self, fake_project, caplog, mocker):
        caplog.set_level(logging.DEBUG, logger="kedro")

        mock_logging = mocker.patch.object(LOGGING, "configure")
        session = KedroServiceSession.create(fake_project)
        session.close()

        mock_logging.assert_not_called()

    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("fake_pipeline_name", [None, [_FAKE_PIPELINE_NAME]])
    def test_run(
        self,
        fake_project,
        fake_run_id,
        fake_pipeline_name,
        mock_context_class,
        mock_runner,
        mocker,
    ):
        """Test running the project via the session"""

        mock_hook = mocker.patch(
            "kedro.framework.session.service_session._create_hook_manager"
        ).return_value.hook
        mock_pipelines = mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            return_value={
                _FAKE_PIPELINE_NAME: mocker.Mock(),
                "__default__": mocker.Mock(),
            },
        )
        mock_context = mock_context_class.return_value
        mock_catalog = mock_context._get_catalog.return_value
        mock_runner.__name__ = "SequentialRunner"
        mock_pipeline = (
            mock_pipelines.__getitem__().__radd__.return_value.filter.return_value
        )
        with KedroServiceSession.create(
            project_path=fake_project, session_id="fake_id"
        ) as session:
            session.run(runner=mock_runner, pipeline_names=fake_pipeline_name)

        record_data = {
            "session_id": "fake_id",
            "run_id": fake_run_id,
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
            "runtime_params": {},
            "pipeline_names": fake_pipeline_name or ["__default__"],
            "namespaces": None,
            "runner": mock_runner.__name__,
            "only_missing_outputs": False,
        }

        mock_hook.before_pipeline_run.assert_called_once_with(
            run_params=record_data, pipeline=mock_pipeline, catalog=mock_catalog
        )
        mock_runner.run.assert_called_once_with(
            mock_pipeline,
            mock_catalog,
            session._hook_manager,
            run_id=fake_run_id,
            only_missing_outputs=False,
        )
        mock_hook.after_pipeline_run.assert_called_once_with(
            run_params=record_data,
            run_result=mock_runner.run.return_value,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    def test_run_logs_package_name_when_outside_project(
        self,
        tmp_path,
        mock_package_name,
        mock_context_class,
        mock_runner,
        caplog,
        monkeypatch,
        mocker,
    ):
        """Session run should log configured package name, not current directory."""
        from kedro.framework import project as kedro_project

        monkeypatch.setattr(kedro_project, "PACKAGE_NAME", mock_package_name)

        # Create a temporary directory outside of the project
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        pyproject_path = tmp_path / "pyproject.toml"
        if pyproject_path.exists():
            pyproject_path.unlink()

        # Change the current working directory to the outside directory
        monkeypatch.chdir(outside_dir)

        mocker.patch(
            "kedro.framework.session.service_session._create_hook_manager"
        ).return_value.hook
        mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            return_value={
                _FAKE_PIPELINE_NAME: mocker.Mock(),
                "__default__": mocker.Mock(),
            },
        )
        mock_runner.__name__ = "SequentialRunner"
        with KedroServiceSession.create(
            project_path=tmp_path, session_id="fake_id"
        ) as session:
            session.run(runner=mock_runner)

        assert f"Kedro project {mock_package_name}" in caplog.text

    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("fake_pipeline_name", [None, [_FAKE_PIPELINE_NAME]])
    @pytest.mark.parametrize("match_pattern", [True, False])
    def test_run_thread_runner(
        self,
        fake_project,
        fake_run_id,
        fake_pipeline_name,
        mock_context_class,
        mock_thread_runner,
        mocker,
        match_pattern,
    ):
        """Test running the project via the session"""

        mock_hook = mocker.patch(
            "kedro.framework.session.service_session._create_hook_manager"
        ).return_value.hook

        mock_node1 = mocker.Mock()
        mock_node1.name = "test_node_1"
        mock_node1.outputs = ["output1"]

        mock_node2 = mocker.Mock()
        mock_node2.name = "test_node_2"
        mock_node2.outputs = ["output2"]

        ds_mock = mocker.Mock()
        ds_mock.nodes = [mock_node1, mock_node2]
        ds_mock.datasets.return_value = ["ds_1", "ds_2"]

        filter_mock = mocker.Mock()
        filter_mock.__add__ = mocker.Mock(return_value=ds_mock)
        filter_mock.__radd__ = mocker.Mock(return_value=ds_mock)

        filter_mock.filter.return_value = ds_mock

        mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            {
                _FAKE_PIPELINE_NAME: filter_mock,
                "__default__": filter_mock,
            },
        )
        mocker.patch(
            "kedro.io.data_catalog.CatalogConfigResolver.match_dataset_pattern",
            return_value=match_pattern,
        )

        with KedroServiceSession.create(
            project_path=fake_project, session_id="fake_id"
        ) as session:
            session.run(runner=mock_thread_runner, pipeline_names=fake_pipeline_name)

        mock_context = mock_context_class.return_value
        record_data = {
            "session_id": "fake_id",
            "run_id": fake_run_id,
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
            "runtime_params": {},
            "pipeline_names": fake_pipeline_name or ["__default__"],
            "namespaces": None,
            "runner": mock_thread_runner.__name__,
            "only_missing_outputs": False,
        }
        mock_catalog = mock_context._get_catalog.return_value
        mock_pipeline = filter_mock.filter().filter()

        mock_hook.before_pipeline_run.assert_called_once_with(
            run_params=record_data, pipeline=mock_pipeline, catalog=mock_catalog
        )
        mock_thread_runner.run.assert_called_once_with(
            mock_pipeline,
            mock_catalog,
            session._hook_manager,
            run_id=fake_run_id,
            only_missing_outputs=False,
        )
        mock_hook.after_pipeline_run.assert_called_once_with(
            run_params=record_data,
            run_result=mock_thread_runner.run.return_value,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_run_non_existent_pipeline(self, fake_project, mock_runner, mocker):
        pattern = (
            "Failed to find the pipeline named 'doesnotexist'. "
            "It needs to be generated and returned "
            "by the 'register_pipelines' function."
        )
        mocker.patch(
            "kedro_telemetry.plugin._check_for_telemetry_consent",
            return_value=False,
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            with KedroServiceSession.create(project_path=fake_project) as session:
                session.run(runner=mock_runner, pipeline_names=["doesnotexist"])

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_run_non_existent_pipeline_with_suggestion(
        self, fake_project, mock_runner, mocker
    ):
        """When a non-existent pipeline name has close matches, error includes suggestions."""
        mocker.patch(
            "kedro_telemetry.plugin._check_for_telemetry_consent",
            return_value=False,
        )
        mocker.patch(
            "kedro.framework.session.service_session.get_close_matches",
            return_value=["__default__", "data_engineering"],
        )
        with pytest.raises(ValueError) as exc_info:
            with KedroServiceSession.create(project_path=fake_project) as session:
                session.run(runner=mock_runner, pipeline_names=["__defult__"])
        msg = str(exc_info.value)
        assert "Failed to find the pipeline named '__defult__'" in msg
        assert "Did you mean one of these instead?" in msg
        assert "__default__" in msg

    @pytest.mark.usefixtures("mock_settings_context_class")
    @pytest.mark.parametrize("fake_pipeline_name", [None, [_FAKE_PIPELINE_NAME]])
    def test_run_exception(
        self,
        fake_project,
        fake_run_id,
        fake_pipeline_name,
        mock_context_class,
        mock_runner,
        mocker,
        caplog,
    ):
        """Test exception being raised during the run"""
        mock_hook = mocker.patch(
            "kedro.framework.session.service_session._create_hook_manager"
        ).return_value.hook
        mock_pipelines = mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            return_value={
                _FAKE_PIPELINE_NAME: mocker.Mock(),
                "__default__": mocker.Mock(),
            },
        )
        mock_context = mock_context_class.return_value
        mock_catalog = mock_context._get_catalog.return_value
        error = FakeException("You shall not pass!")
        mock_runner.run.side_effect = error  # runner.run() raises an error
        mock_pipeline = (
            mock_pipelines.__getitem__().__radd__.return_value.filter.return_value
        )

        with pytest.raises(FakeException) as exc_info:
            session = KedroServiceSession.create(
                project_path=fake_project, session_id="fake_id"
            )
            session.run(runner=mock_runner, pipeline_names=fake_pipeline_name)

        record_data = {
            "session_id": "fake_id",
            "run_id": fake_run_id,
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
            "runtime_params": {},
            "pipeline_names": fake_pipeline_name or ["__default__"],
            "namespaces": None,
            "runner": mock_runner.__name__,
            "only_missing_outputs": False,
        }

        mock_hook.on_pipeline_error.assert_called_once_with(
            error=error,
            run_params=record_data,
            pipeline=mock_pipeline,
            catalog=mock_catalog,
        )

        mock_hook.after_pipeline_run.assert_not_called()
        msg = str(exc_info.value)
        assert "You shall not pass!" in msg
        assert isinstance(exc_info.value, FakeException)

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_session_raise_error_with_invalid_runner_instance(
        self, fake_project, mocker
    ):
        mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            return_value={
                "__default__": mocker.Mock(),
            },
        )
        mock_runner_class = mocker.patch("kedro.runner.SequentialRunner")

        session = KedroServiceSession.create(
            project_path=fake_project, session_id="fake_id"
        )
        with pytest.raises(
            KedroSessionError,
            match="KedroServiceSession expect an instance of Runner instead of a class.",
        ):
            # Execute run with SequentialRunner class instead of SequentialRunner()
            session.run(runner=mock_runner_class)

    @pytest.mark.usefixtures("mock_settings_context_class")
    def test_multiple_runs(self, fake_project, mock_runner, mocker):
        """Test that running multiple times in the same session works and generates different run_ids."""
        mocker.patch(
            "kedro.framework.session.service_session._create_hook_manager"
        ).return_value.hook
        mocker.patch(
            "kedro.framework.session.service_session.pipelines",
            return_value={
                _FAKE_PIPELINE_NAME: mocker.Mock(),
                "__default__": mocker.Mock(),
            },
        )
        mock_runner.__name__ = "SequentialRunner"

        with KedroServiceSession.create(
            project_path=fake_project, session_id="fake_id"
        ) as session:
            session.run(
                runner=mock_runner,
                pipeline_names=[_FAKE_PIPELINE_NAME],
                runtime_params={"param1": "value1"},
            )
            first_run_id = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["run_id"]
            )
            first_runtime_params = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["runtime_params"]
            )
            first_session_id = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["session_id"]
            )

            session.run(
                runner=mock_runner,
                pipeline_names=_FAKE_PIPELINE_NAME,
                runtime_params={"param2": "value2"},
            )
            second_run_id = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["run_id"]
            )
            second_runtime_params = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["runtime_params"]
            )
            second_session_id = (
                session._hook_manager.hook.before_pipeline_run.call_args.kwargs[
                    "run_params"
                ]["session_id"]
            )
        assert first_session_id == second_session_id
        assert first_run_id != second_run_id
        assert first_runtime_params == {"param1": "value1"}
        assert second_runtime_params == {"param2": "value2"}
