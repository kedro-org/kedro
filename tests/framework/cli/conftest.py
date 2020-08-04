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

"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import sys
import tempfile
from importlib import import_module
from os import makedirs
from pathlib import Path

import yaml
from click.testing import CliRunner
from pytest import fixture

from kedro.framework.cli.cli import cli

MOCKED_HOME = "user/path/"
REPO_NAME = "dummy_project"
PACKAGE_NAME = "dummy_package"


@fixture(name="cli_runner")
def cli_runner_fixture():
    runner = CliRunner()
    with runner.isolated_filesystem():
        makedirs(MOCKED_HOME)
        yield runner


@fixture
def entry_points(mocker):
    return mocker.patch("pkg_resources.iter_entry_points")


@fixture
def entry_point(mocker, entry_points):
    ep = mocker.MagicMock()
    entry_points.return_value = [ep]
    return ep


@fixture(scope="module")
def fake_root_dir():
    # using tempfile as tmp_path fixture doesn't support module scope
    with tempfile.TemporaryDirectory() as tmp_root:
        yield Path(tmp_root).resolve()


@fixture(scope="module")
def fake_package_path(fake_root_dir):
    return fake_root_dir.resolve() / REPO_NAME / "src" / PACKAGE_NAME


@fixture(scope="module")
def fake_repo_path(fake_root_dir):
    return fake_root_dir.resolve() / REPO_NAME


@fixture(scope="module")
def dummy_config(fake_root_dir):
    config = {
        "project_name": "Dummy Project",
        "repo_name": REPO_NAME,
        "python_package": PACKAGE_NAME,
        "output_dir": str(fake_root_dir),
    }

    config_path = fake_root_dir / "dummy_config.yml"
    with config_path.open("w") as f:
        yaml.dump(config, f)

    return config_path


@fixture(scope="module")
def dummy_project(fake_root_dir, dummy_config):
    CliRunner().invoke(
        cli, ["new", "-c", str(dummy_config), "--starter", "pandas-iris"]
    )
    project_path = fake_root_dir / REPO_NAME
    src_path = project_path / "src"

    # NOTE: Here we load a couple of modules, as they would be imported in
    # the code and tests.
    # It's safe to remove the new entries from path due to the python
    # module caching mechanism. Any `reload` on it will not work though.
    old_path = sys.path.copy()
    sys.path = [str(project_path), str(src_path)] + sys.path

    import_module("kedro_cli")
    import_module(PACKAGE_NAME)

    sys.path = old_path

    yield project_path

    del sys.modules["kedro_cli"]
    del sys.modules[PACKAGE_NAME]


@fixture(scope="module")
def fake_kedro_cli(dummy_project):  # pylint: disable=unused-argument
    """
    A small helper to pass kedro_cli into tests without importing.
    It only becomes available after `dummy_project` fixture is applied,
    that's why it can't be done on module level.
    """
    yield import_module("kedro_cli")


@fixture
def chdir_to_dummy_project(dummy_project, monkeypatch):
    monkeypatch.chdir(str(dummy_project))


@fixture
def patch_log(mocker):
    mocker.patch("logging.config.dictConfig")
