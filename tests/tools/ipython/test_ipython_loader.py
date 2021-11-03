"""Test Kedro extras."""
from pathlib import Path

import pytest

from tools.ipython import ipython_loader
from tools.ipython.ipython_loader import locate_ipython_startup_dir


@pytest.fixture
def dummy_project_dir(tmp_path):
    # need to resolve tmp_path for tests to pass on MacOS
    root = Path(tmp_path / "dummy_project").resolve()
    root.mkdir()
    startup_path = root / ".ipython" / "profile_default" / "startup"
    startup_path.mkdir(parents=True)
    yield root


@pytest.fixture
def nested_project_dir(dummy_project_dir):
    nested = dummy_project_dir / "some_dir" / "another_dummy_project"
    startup_path = nested / ".ipython" / "profile_default" / "startup"
    startup_path.mkdir(parents=True)
    yield nested.resolve()


@pytest.fixture
def startup_script(dummy_project_dir):
    script = "dummy_project_var1 = 111"
    script_path = (
        dummy_project_dir
        / ".ipython"
        / "profile_default"
        / "startup"
        / "01-startup-script.py"
    )
    script_path.write_text(script, encoding="utf-8")
    return script_path


@pytest.fixture
def bad_startup_script(dummy_project_dir):
    script = "raise ValueError('bad script!')"
    script_path = (
        dummy_project_dir
        / ".ipython"
        / "profile_default"
        / "startup"
        / "00-bad-script.py"
    )
    script_path.write_text(script, encoding="utf-8")
    return script_path


class TestIpythonStartupDir:
    """Test locating IPython startup directory."""

    def test_locate(self, dummy_project_dir):
        ipython_dir = dummy_project_dir / ".ipython" / "profile_default" / "startup"
        assert locate_ipython_startup_dir(dummy_project_dir) == ipython_dir

        path = dummy_project_dir / "notebooks" / "foo" / "bar"
        path.mkdir(parents=True)
        assert locate_ipython_startup_dir(path) == ipython_dir

    def test_locate_nested(self, nested_project_dir, dummy_project_dir):
        root_ipython_dir = (
            dummy_project_dir / ".ipython" / "profile_default" / "startup"
        )
        nested_ipython_dir = (
            nested_project_dir / ".ipython" / "profile_default" / "startup"
        )
        assert locate_ipython_startup_dir(nested_project_dir) == nested_ipython_dir
        assert locate_ipython_startup_dir(nested_project_dir.parent) == root_ipython_dir

        path = nested_project_dir / "notebooks" / "foo" / "bar"
        path.mkdir(parents=True)
        assert locate_ipython_startup_dir(path) == nested_ipython_dir

        path = dummy_project_dir / "other" / "dir"
        path.mkdir(parents=True)
        assert locate_ipython_startup_dir(path) == root_ipython_dir

    @pytest.mark.usefixtures("dummy_project_dir")
    def test_locate_no_project(self, tmp_path):
        assert locate_ipython_startup_dir(str(tmp_path)) is None
        assert locate_ipython_startup_dir(Path("/")) is None


class TestRunStartupScripts:
    """Test running IPython startup scripts from the project."""

    def test_run(self, dummy_project_dir, startup_script, caplog):
        ipython_loader.run_startup_scripts(dummy_project_dir)
        expected_message = f"Startup script `{startup_script}` successfully executed"

        assert getattr(ipython_loader, "dummy_project_var1") == 111
        assert len(caplog.records) == 1
        assert caplog.records[0].message == expected_message

    def test_run_bad_script(self, dummy_project_dir, bad_startup_script, caplog):
        ipython_loader.run_startup_scripts(dummy_project_dir)
        expected_error_message = (
            f"Startup script `{bad_startup_script}` failed:\nValueError: bad script!"
        )
        assert len(caplog.records) == 1
        assert caplog.records[0].message == expected_error_message

    def test_run_both_scripts(
        self, dummy_project_dir, startup_script, bad_startup_script, caplog
    ):
        ipython_loader.run_startup_scripts(dummy_project_dir)
        expected_error_message = (
            f"Startup script `{bad_startup_script}` failed:\nValueError: bad script!"
        )
        expected_success_message = "Startup script `{}` successfully executed".format(
            startup_script
        )

        assert len(caplog.records) == 2
        assert caplog.records[0].message == expected_error_message
        assert caplog.records[1].message == expected_success_message

    def test_modify_globals(self):
        """Test modify_globals context manager."""
        with ipython_loader.modify_globals(__file__="new_file_value", new_key=999):
            assert ipython_loader.__file__ == "new_file_value"
            assert getattr(ipython_loader, "new_key") == 999
        assert ipython_loader.__file__ != "new_file_value"
        assert not hasattr(ipython_loader, "some_new_key")

    def test_ipython_loader_main(self, mocker, dummy_project_dir, caplog):
        mocker.patch("pathlib.Path.cwd", return_value=dummy_project_dir)
        script_path = (
            dummy_project_dir
            / ".ipython"
            / "profile_default"
            / "startup"
            / "startup_script.py"
        )
        script_path.write_text("dummy_project_var2 = 2222", encoding="utf-8")
        ipython_loader.main()

        assert getattr(ipython_loader, "dummy_project_var2") == 2222
        assert len(caplog.records) == 1
        expected_message = f"Startup script `{script_path}` successfully executed"
        assert caplog.records[0].message == expected_message
