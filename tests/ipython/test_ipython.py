# pylint: disable=import-outside-toplevel
from pathlib import Path

import pytest
from IPython.core.error import UsageError
from IPython.testing.globalipapp import get_ipython

from kedro.framework.startup import ProjectMetadata
from kedro.ipython import _resolve_project_path, load_ipython_extension, reload_kedro
from kedro.pipeline import Pipeline


@pytest.fixture(autouse=True)
def cleanup_pipeline():
    yield
    from kedro.framework.project import pipelines

    pipelines.configure()


@pytest.fixture(scope="module")  # get_ipython() twice will result in None
def ipython():
    ipython = get_ipython()
    load_ipython_extension(ipython)
    return ipython


PACKAGE_NAME = "fake_package_name"
PROJECT_NAME = "fake_project_name"
PROJECT_VERSION = "0.1"


@pytest.mark.skip()
class TestLoadKedroObjects:
    def test_load_kedro_objects(self, tmp_path, mocker, caplog):
        kedro_path = tmp_path / "here"

        fake_metadata = ProjectMetadata(
            source_dir=kedro_path / "src",  # default
            config_file=kedro_path / "pyproject.toml",
            package_name=PACKAGE_NAME,
            project_name=PROJECT_NAME,
            project_version=PROJECT_VERSION,
            project_path=kedro_path,
        )
        my_pipelines = {"ds": Pipeline([])}

        def my_register_pipeline():
            return my_pipelines

        mocker.patch(
            "kedro.framework.project._ProjectPipelines._get_pipelines_registry_callable",
            return_value=my_register_pipeline,
        )
        mocker.patch("kedro.framework.startup.configure_project")
        mocker.patch("kedro.ipython.bootstrap_project", return_value=fake_metadata)
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch("kedro.ipython.load_entry_points", return_value=[mock_line_magic])
        mock_register_line_magic = mocker.patch("kedro.ipython.register_line_magic")
        mock_session_create = mocker.patch("kedro.ipython.KedroSession.create")
        mock_ipython = mocker.patch("kedro.ipython.get_ipython")

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

    def test_load_kedro_objects_extra_args(self, tmp_path, mocker):
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
        mocker.patch("kedro.ipython.configure_project")
        mocker.patch("kedro.ipython.bootstrap_project", return_value=fake_metadata)
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch("kedro.ipython.load_entry_points", return_value=[mock_line_magic])
        mock_register_line_magic = mocker.patch("kedro.ipython.register_line_magic")
        mock_session_create = mocker.patch("kedro.ipython.KedroSession.create")
        mock_ipython = mocker.patch("kedro.ipython.get_ipython")

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

    def test_load_kedro_objects_no_path(
        self, tmp_path, caplog, mocker, ipython
    ):  # pylint: disable=unused-argument
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

        mocker.patch("kedro.ipython.configure_project")
        mocker.patch("kedro.ipython.bootstrap_project", return_value=fake_metadata)
        mock_line_magic = mocker.Mock()
        mock_line_magic.__name__ = "abc"
        mocker.patch("kedro.ipython.load_entry_points", return_value=[mock_line_magic])
        mocker.patch("kedro.ipython.register_line_magic")
        mocker.patch("kedro.ipython.KedroSession.create")
        mocker.patch("kedro.ipython.get_ipython")
        mocker.patch("kedro.ipython._find_kedro_project", return_value=tmp_path)

        reload_kedro()

        expected_message = (
            f"Resolved project path as: {tmp_path}.\nTo set a different path, run "
            "'%reload_kedro <project_root>'"
        )
        log_messages = [record.getMessage() for record in caplog.records]
        assert expected_message in log_messages


class TestLoadIPythonExtension:
    def test_load_ipython_extension(self, ipython):
        ipython.magic("load_ext kedro.ipython")

    def test_load_ipython_extension_old_location(self, ipython):
        ipython.magic("load_ext kedro.ipython")

    def test_load_extension_missing_dependency(self, mocker):
        mocker.patch("kedro.ipython.reload_kedro", side_effect=ImportError)
        mocker.patch(
            "kedro.ipython._find_kedro_project",
            return_value=mocker.Mock(),
        )
        mocker.patch("IPython.core.magic.register_line_magic")
        mocker.patch("IPython.core.magic_arguments.magic_arguments")
        mocker.patch("IPython.core.magic_arguments.argument")
        mock_ipython = mocker.patch("IPython.get_ipython")

        with pytest.raises(ImportError):
            load_ipython_extension(mocker.Mock())

        assert not mock_ipython().called
        assert not mock_ipython().push.called

    def test_load_extension_not_in_kedro_project(self, mocker, caplog):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        mocker.patch("IPython.core.magic.register_line_magic")
        mocker.patch("IPython.core.magic_arguments.magic_arguments")
        mocker.patch("IPython.core.magic_arguments.argument")
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

    def test_load_extension_register_line_magic(self, mocker, ipython):

        mocker.patch("kedro.ipython._find_kedro_project")
        mock_reload_kedro = mocker.patch("kedro.ipython.reload_kedro")
        load_ipython_extension(ipython)
        mock_reload_kedro.assert_called_once()

        # Calling the line magic to check if the line magic is available
        ipython.magic("reload_kedro")
        assert mock_reload_kedro.call_count == 2

    @pytest.mark.parametrize(
        "args",
        [
            "",
            ".",
            ". --env=base",
            "--env=base",
            "-e base",
            ". --env=base --params=key:val",
        ],
    )
    def test_line_magic_with_valid_arguments(self, mocker, args, ipython):
        mocker.patch("kedro.ipython._find_kedro_project")
        mocker.patch("kedro.ipython.reload_kedro")

        ipython.magic(f"reload_kedro {args}")

    def test_line_magic_with_invalid_arguments(self, mocker, ipython):
        mocker.patch("kedro.ipython._find_kedro_project")
        mocker.patch("kedro.ipython.reload_kedro")
        load_ipython_extension(ipython)

        with pytest.raises(
            UsageError, match=r"unrecognized arguments: --invalid_arg=dummy"
        ):
            ipython.magic("reload_kedro --invalid_arg=dummy")


class TestProjectPathResolution:
    def test_only_path_specified(self):
        result = _resolve_project_path(path="/test")
        expected = Path("/test").resolve()
        assert result == expected

    def test_only_local_namespace_specified(self):
        class Context:
            _project_path = Path("/test").resolve()

        result = _resolve_project_path(
            local_namespace={"context": Context()}
        )
        expected = Path("/test").resolve()
        assert result == expected

    def test_no_path_no_local_namespace_specified(self, mocker):
        mocker.patch(
            "kedro.ipython._find_kedro_project", return_value=Path("/test").resolve()
        )
        result = _resolve_project_path()
        expected = Path("/test").resolve()
        assert result == expected

    def test_project_path_unresolvable(self, mocker):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        result = _resolve_project_path()
        expected = None
        assert result == expected

    def test_project_path_unresolvable_warning(self, mocker, caplog, ipython):
        mocker.patch("kedro.ipython._find_kedro_project", return_value=None)
        ipython.magic("reload_ext kedro.ipython")
        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = (
            "Kedro extension was registered but couldn't find a Kedro project. "
            "Make sure you run '%reload_kedro <project_root>'."
        )
        assert expected_message in log_messages

    def test_project_path_update(self, caplog):
        class Context:
            def __init__(self, project_path):
                self._project_path = Path(project_path).resolve()

        local_namespace = {"context": Context("/path")}
        updated_path = Path("/updated_path").resolve()
        _resolve_project_path(path=updated_path, local_namespace=local_namespace)

        log_messages = [record.getMessage() for record in caplog.records]
        expected_message = f"Updating path to Kedro project: {updated_path}..."
        assert expected_message in log_messages
