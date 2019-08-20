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

import shutil
import sys
from pathlib import Path

import pytest

from kedro.cli.cli import _create_project


@pytest.fixture(scope="session")
def project_path():
    return Path(__file__).parent / "fake_project"


@pytest.fixture(autouse=True, scope="function")
def fake_project(project_path: Path):
    shutil.rmtree(str(project_path), ignore_errors=True)
    _create_project(str(Path(__file__).parent / "project_config.yml"), verbose=True)

    (project_path / "__init__.py").touch()
    (project_path / "src" / "__init__.py").touch()

    path_to_add = str(project_path.parent)
    if path_to_add not in sys.path:
        sys.path = [path_to_add] + sys.path

    import fake_project.kedro_cli  # pylint: disable=import-error

    yield fake_project
    shutil.rmtree(str(project_path))
