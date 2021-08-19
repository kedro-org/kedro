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
import shutil

import pytest

from kedro.framework.project import settings


@pytest.fixture(autouse=True)
def mocked_logging(mocker):
    # Disable logging.config.dictConfig in KedroSession._setup_logging as
    # it changes logging.config and affects other unit tests
    return mocker.patch("logging.config.dictConfig")


@pytest.fixture(autouse=True)
def cleanup_pipelines(fake_repo_path, fake_package_path):
    pipes_path = fake_package_path / "pipelines"
    old_pipelines = {p.name for p in pipes_path.iterdir() if p.is_dir()}
    requirements_txt = fake_repo_path / "src" / "requirements.txt"
    requirements = requirements_txt.read_text()
    yield

    # remove created pipeline files after the test
    created_pipelines = {
        p.name for p in pipes_path.iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    created_pipelines -= old_pipelines

    for pipeline in created_pipelines:
        shutil.rmtree(str(pipes_path / pipeline))

        confs = fake_repo_path / settings.CONF_ROOT
        for each in confs.rglob(f"*{pipeline}*"):  # clean all pipeline config files
            if each.is_file():
                each.unlink()

        dirs_to_delete = (
            dirpath
            for pattern in ("parameters", "catalog")
            for dirpath in confs.rglob(pattern)
            if dirpath.is_dir() and not any(dirpath.iterdir())
        )
        for dirpath in dirs_to_delete:
            dirpath.rmdir()

        tests = fake_repo_path / "src" / "tests" / "pipelines" / pipeline
        if tests.is_dir():
            shutil.rmtree(str(tests))

    # remove requirements.in and reset requirements.txt
    requirements_in = fake_repo_path / "src" / "requirements.in"
    if requirements_in.exists():
        requirements_in.unlink()
    requirements_txt.write_text(requirements)


@pytest.fixture
def cleanup_dist(fake_repo_path):
    yield
    dist_dir = fake_repo_path / "src" / "dist"
    if dist_dir.exists():
        shutil.rmtree(str(dist_dir))
