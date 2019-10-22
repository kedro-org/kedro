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
# pylint: disable=unused-argument

import sys
import tempfile
from pathlib import Path

import pytest
import yaml

from kedro.cli.cli import _create_project

TEST_REPO_NAME = "fake_repo"


@pytest.fixture(scope="session")
def fake_root_dir():
    with tempfile.TemporaryDirectory() as tmp_root:
        yield Path(tmp_root)


@pytest.fixture(scope="session")
def fake_repo_path(fake_root_dir):
    return fake_root_dir / TEST_REPO_NAME


@pytest.fixture(scope="session")
def fake_repo_config_path(fake_root_dir):
    repo_config = {
        "output_dir": str(fake_root_dir),
        "project_name": "Test Project",
        "repo_name": TEST_REPO_NAME,
        "python_package": "fake_package",
        "include_example": True,
    }
    config_path = fake_root_dir / "repo_config.yml"

    with open(str(config_path), "w") as fd:
        yaml.safe_dump(repo_config, fd)

    return config_path


@pytest.fixture(autouse=True, scope="session")
def fake_repo(fake_repo_path: Path, fake_repo_config_path: Path):
    _create_project(str(fake_repo_config_path), verbose=True)

    # NOTE: Here we load a couple of modules, as they would be imported in
    # the code and tests.
    # It's safe to remove the new entries from path due to the python
    # module caching mechanism. Any `reload` on it will not work though.
    old_path = sys.path.copy()
    sys.path = [str(fake_repo_path), str(fake_repo_path / "src")] + sys.path

    import kedro_cli  # noqa: F401 pylint: disable=import-error,unused-import

    # `load_context` will try to `import fake_package`,
    # will fail without this line:
    import fake_package  # noqa: F401 pylint: disable=import-error,unused-import

    sys.path = old_path


@pytest.fixture(scope="session")
def fake_kedro_cli(fake_repo):
    """
    A small helper to pass kedro_cli into tests without importing.
    It only becomes available after `fake_repo` fixture is applied,
    that's why it can't be done on module level.
    """
    import kedro_cli  # pylint: disable=import-error

    return kedro_cli
