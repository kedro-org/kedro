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

"""Test kedro extras located in `extras/` folder."""
from pathlib import Path

import extras.kedro_project_loader as loader
import pytest
from extras.kedro_project_loader import locate_project_root


@pytest.fixture
def dummy_project_dir(tmp_path):
    root = tmp_path / "dummy_project"
    root.mkdir()
    (root / "kedro_cli.py").touch()
    startup_path = root / ".ipython" / "profile_default" / "startup"
    startup_path.mkdir(parents=True)
    script = "dummy_project_var1 = 111"
    (startup_path / "startup_script.py").write_text(script, encoding="utf-8")
    yield root.resolve()


@pytest.fixture
def nested_project_dir(dummy_project_dir):
    nested = dummy_project_dir / "some_dir" / "another_dummy_project"
    nested.mkdir(parents=True)
    (nested / "kedro_cli.py").touch()
    yield nested.resolve()


class TestLocateKedroProject:
    """Test locating Kedro project."""

    def test_locate(self, dummy_project_dir):
        assert locate_project_root(dummy_project_dir) == dummy_project_dir
        assert (
            locate_project_root(dummy_project_dir / "kedro_cli.py") == dummy_project_dir
        )

        path = dummy_project_dir / "notebooks" / "foo" / "bar"
        path.mkdir(parents=True)
        assert locate_project_root(path) == dummy_project_dir

    def test_locate_nested(self, nested_project_dir, dummy_project_dir):
        assert locate_project_root(nested_project_dir) == nested_project_dir
        assert locate_project_root(nested_project_dir.parent) == dummy_project_dir

        path = nested_project_dir / "notebooks" / "foo" / "bar"
        path.mkdir(parents=True)
        assert locate_project_root(path) == nested_project_dir

        path = dummy_project_dir / "other" / "dir"
        path.mkdir(parents=True)
        assert locate_project_root(path) == dummy_project_dir

    @pytest.mark.usefixtures("dummy_project_dir")
    def test_locate_no_project(self, tmp_path):
        assert locate_project_root(tmp_path) is None
        assert locate_project_root(Path("/")) is None


class TestStartupKedroProject:
    """Test running Kedro project IPython startup scripts."""

    def test_load(self, dummy_project_dir):
        loader.startup_kedro_project(dummy_project_dir)
        assert getattr(loader, "dummy_project_var1") == 111

    def test_load_exception(self, dummy_project_dir):
        bad_script_path = (
            dummy_project_dir
            / ".ipython"
            / "profile_default"
            / "startup"
            / "bad_script.py"
        )
        script = """raise ValueError('bad_script!')"""
        bad_script_path.write_text(script, encoding="utf-8")
        loader.startup_kedro_project(dummy_project_dir)
        errors = list(loader.load_kedro_errors.values())
        assert len(errors) == 1
        assert isinstance(errors[0], ValueError)
        assert str(errors[0]) == "bad_script!"


def test_modify_globals():
    """Test modify_globals context manager."""
    with loader.modify_globals(__file__="new_file_value", some_new_key=999):
        assert loader.__file__ == "new_file_value"
        assert getattr(loader, "some_new_key") == 999
    assert loader.__file__ != "new_file_value"
    assert not hasattr(loader, "some_new_key")


def test_main(mocker, dummy_project_dir):
    """Test running kedro_project_loader."""
    mocker.patch("pathlib.Path.cwd", return_value=dummy_project_dir)
    script_path = (
        dummy_project_dir
        / ".ipython"
        / "profile_default"
        / "startup"
        / "startup_script.py"
    )
    script_path.write_text("dummy_project_var2 = 2222", encoding="utf-8")
    loader.main()
    assert getattr(loader, "dummy_project_var2") == 2222
