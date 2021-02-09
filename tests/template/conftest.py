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

import sys
import tempfile
from importlib import import_module
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from kedro.framework.cli.cli import cli

_FAKE_REPO_NAME = "fake_repo"
_FAKE_PACKAGE_NAME = "fake_package"


@pytest.fixture
def fake_package_name():
    return _FAKE_PACKAGE_NAME


@pytest.fixture(scope="session")
def fake_root_dir():
    try:
        with tempfile.TemporaryDirectory() as tmp_root:
            yield Path(tmp_root)
    # On Windows `PermissionError` is raised from time to time
    # while `tmp_root` removing.
    except PermissionError:  # pragma: no cover
        pass


@pytest.fixture(scope="session")
def fake_repo_path(fake_root_dir):
    return fake_root_dir.resolve() / _FAKE_REPO_NAME


@pytest.fixture(scope="session")
def fake_repo_config_path(fake_root_dir):
    repo_config = {
        "output_dir": str(fake_root_dir),
        "project_name": "Test Project",
        "repo_name": _FAKE_REPO_NAME,
        "python_package": _FAKE_PACKAGE_NAME,
    }
    config_path = fake_root_dir / "repo_config.yml"

    with config_path.open("w") as fd:
        yaml.safe_dump(repo_config, fd)

    return config_path


@pytest.fixture(scope="session")
def fake_project_cli(fake_repo_path: Path, fake_repo_config_path: Path):
    starter_path = Path(__file__).parents[2].resolve()
    starter_path = starter_path / "features" / "steps" / "test_starter"
    CliRunner().invoke(
        cli, ["new", "-c", str(fake_repo_config_path), "--starter", str(starter_path)],
    )

    # NOTE: Here we load a couple of modules, as they would be imported in
    # the code and tests.
    # It's safe to remove the new entries from path due to the python
    # module caching mechanism. Any `reload` on it will not work though.
    old_path = sys.path.copy()
    sys.path = [str(fake_repo_path), str(fake_repo_path / "src")] + sys.path

    # `load_context` will try to `import fake_package`,
    # will fail without this line:
    import_module(_FAKE_PACKAGE_NAME)

    yield import_module(f"{_FAKE_PACKAGE_NAME}.cli")

    sys.path = old_path
    del sys.modules[_FAKE_PACKAGE_NAME]


@pytest.fixture
def chdir_to_dummy_project(fake_repo_path, monkeypatch):
    monkeypatch.chdir(str(fake_repo_path))
