# pylint: disable=import-outside-toplevel,reimported
import pytest

from kedro.extras.extensions.ipython import load_ipython_extension, reload_kedro
from kedro.framework.startup import ProjectMetadata
from kedro.pipeline import Pipeline


@pytest.fixture(autouse=True)
def project_path(mocker, tmp_path):
    path = tmp_path
    mocker.patch("kedro.extras.extensions.ipython.default_project_path", path)


@pytest.fixture(autouse=True)
def cleanup_pipeline():
    yield
    from kedro.framework.project import pipelines

    pipelines.configure()


PACKAGE_NAME = "fake_page_name"
PROJECT_NAME = "fake_project_name"
PROJECT_VERSION = "0.1"


class TestLoadKedroObjects:
    def test_load_kedro_objects(
        self, tmp_path, mocker, caplog
    ):  # pylint: disable=too-many-locals
        from kedro.extras.extensions.ipython import default_project_path

        assert default_project_path == tmp_path

        kedro_path = tmp_path / "here"

        fake_metadata = ProjectMetadata(
            source_dir=tmp_path / "src",  # default
            config_file=tmp_path / "pyproject.toml",
            package_name=PACKAGE_NAME,
            project_name=PROJECT_NAME,
            project_version=PROJECT_VERSION,
            project_path=tmp_path,
        )
        my_pipelines = {"ds": Pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch(
            "kedro.framework.project._ProjectPipelines._get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        mocker.patch("kedro.framework.startup.configure_project")
        mocker.patch(
            "kedro.framework.startup.bootstrap_project", return_value=fake_metadata
        )
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch(
            "kedro.framework.cli.load_entry_points", return_value=[mock_line_magic]
        )
        mock_register_line_magic = mocker.patch(
            "IPython.core.magic.register_line_magic"
        )
        mock_session_create = mocker.patch(
            "kedro.framework.session.KedroSession.create"
        )
        mock_ipython = mocker.patch("IPython.get_ipython")

        reload_kedro(kedro_path)

        mock_session_create.assert_called_once_with(
            PACKAGE_NAME, kedro_path, env=None, extra_params=None
        )
        mock_ipython().push.assert_called_once_with(
            variables={
                "context": mock_session_create().load_context(),
                "catalog": mock_session_create().load_context().catalog,
                "session": mock_session_create(),
                "pipelines": my_pipelines,
            }
        )
        mock_register_line_magic.assert_called_once()

        expected_path = kedro_path.expanduser().resolve()
        expected_message = f"Updated path to Kedro project: {expected_path}"

        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages
        from kedro.extras.extensions.ipython import default_project_path

        # make sure global variable updated
        assert default_project_path == expected_path

    def test_load_kedro_objects_extra_args(self, tmp_path, mocker):
        fake_metadata = ProjectMetadata(
            source_dir=tmp_path / "src",  # default
            config_file=tmp_path / "pyproject.toml",
            package_name=PACKAGE_NAME,
            project_name=PROJECT_NAME,
            project_version=PROJECT_VERSION,
            project_path=tmp_path,
        )
        mocker.patch("kedro.framework.project.configure_project")
        mocker.patch(
            "kedro.framework.startup.bootstrap_project", return_value=fake_metadata
        )
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch(
            "kedro.framework.cli.load_entry_points", return_value=[mock_line_magic]
        )
        mock_register_line_magic = mocker.patch(
            "IPython.core.magic.register_line_magic"
        )
        mock_session_create = mocker.patch(
            "kedro.framework.session.KedroSession.create"
        )
        mock_ipython = mocker.patch("IPython.get_ipython")

        reload_kedro(tmp_path, env="env1", extra_params={"key": "val"})

        mock_session_create.assert_called_once_with(
            PACKAGE_NAME, tmp_path, env="env1", extra_params={"key": "val"}
        )
        mock_ipython().push.assert_called_once_with(
            variables={
                "context": mock_session_create().load_context(),
                "catalog": mock_session_create().load_context().catalog,
                "session": mock_session_create(),
                "pipelines": {},
            }
        )
        assert mock_register_line_magic.call_count == 1

    def test_load_kedro_objects_no_path(self, tmp_path, caplog, mocker):
        from kedro.extras.extensions.ipython import default_project_path

        assert default_project_path == tmp_path

        fake_metadata = ProjectMetadata(
            source_dir=tmp_path / "src",  # default
            config_file=tmp_path / "pyproject.toml",
            package_name=PACKAGE_NAME,
            project_name=PROJECT_NAME,
            project_version=PROJECT_VERSION,
            project_path=tmp_path,
        )
        my_pipelines = {"ds": Pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch(
            "kedro.framework.project._ProjectPipelines._get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        mocker.patch("kedro.framework.project.settings.configure")
        mocker.patch("kedro.framework.session.session.validate_settings")
        mocker.patch("kedro.framework.session.KedroSession._setup_logging")
        mocker.patch(
            "kedro.framework.startup.bootstrap_project", return_value=fake_metadata
        )
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch(
            "kedro.framework.cli.load_entry_points", return_value=[mock_line_magic]
        )
        mocker.patch("IPython.core.magic.register_line_magic")
        mocker.patch("kedro.framework.session.KedroSession.load_context")
        mocker.patch("IPython.get_ipython")

        reload_kedro()

        expected_message = f"No path argument was provided. Using: {tmp_path}"
        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages

        from kedro.extras.extensions.ipython import default_project_path

        # make sure global variable stayed the same
        assert default_project_path == tmp_path


class TestLoadIPythonExtension:
    def test_load_extension_missing_dependency(self, mocker):
        mocker.patch(
            "kedro.extras.extensions.ipython.reload_kedro", side_effect=ImportError
        )
        mocker.patch(
            "kedro.extras.extensions.ipython._find_kedro_project",
            return_value=mocker.Mock(),
        )
        mock_ipython = mocker.patch("IPython.get_ipython")

        with pytest.raises(ImportError):
            load_ipython_extension(mocker.Mock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

    def test_load_extension_not_in_kedro_project(self, mocker, caplog):
        mocker.patch(
            "kedro.extras.extensions.ipython._find_kedro_project", return_value=None
        )
        mock_ipython = mocker.patch("IPython.get_ipython")

        load_ipython_extension(mocker.Mock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = (
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        assert expected_message in log_messages
