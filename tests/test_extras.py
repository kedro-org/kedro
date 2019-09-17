# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
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
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test Kedro extras."""
from pathlib import Path

import pytest
from extras import ipython_loader
from extras.ipython_loader import locate_ipython_startup_dir


@pytest.fixture
def dummy_project_dir(tmp_path):
    # wrap in str is needed for Python 3.5
    # since tmp_path is not directly compatible with Path in that version
    root = Path(str(tmp_path)).resolve() / "dummy_project"
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
        expected_message = "Startup script `{}` successfully executed".format(
            startup_script
        )

        assert getattr(ipython_loader, "dummy_project_var1") == 111
        assert len(caplog.records) == 1
        assert caplog.records[0].message == expected_message

    def test_run_bad_script(self, dummy_project_dir, bad_startup_script, caplog):
        ipython_loader.run_startup_scripts(dummy_project_dir)
        expected_error_message = (
            "Startup script `{}` failed:\n"
            "ValueError: bad script!".format(bad_startup_script)
        )
        assert len(caplog.records) == 1
        assert caplog.records[0].message == expected_error_message

    def test_run_both_scripts(
        self, dummy_project_dir, startup_script, bad_startup_script, caplog
    ):
        ipython_loader.run_startup_scripts(dummy_project_dir)
        expected_error_message = (
            "Startup script `{}` failed:\n"
            "ValueError: bad script!".format(bad_startup_script)
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
        expected_message = "Startup script `{}` successfully executed".format(
            script_path
        )
        assert caplog.records[0].message == expected_message
