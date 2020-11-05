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

import re
import sys
from pathlib import Path

import pytest
import toml

from kedro import __version__ as kedro_version
from kedro.framework.context import (
    KedroContextError,
    load_context,
    load_package_context,
)
from kedro.framework.project.metadata import _get_project_metadata


@pytest.fixture(autouse=True)
def mock_logging_config(mocker):
    # Disable logging.config.dictConfig in KedroContext._setup_logging as
    # it changes logging.config and affects other unit tests
    mocker.patch("logging.config.dictConfig")


def _create_kedro_config(project_path, payload):
    kedro_conf = project_path / "pyproject.toml"
    kedro_conf.parent.mkdir(parents=True, exist_ok=True)
    toml_str = toml.dumps(payload)
    kedro_conf.write_text(toml_str)


@pytest.mark.usefixtures("fake_project_cli")
class TestLoadContext:
    def test_valid_context(self, fake_repo_path, mocker):
        """Test getting project context."""
        get_project_metadata_mock = mocker.patch(
            "kedro.framework.context.context._get_project_metadata",
            wraps=_get_project_metadata,
        )
        result = load_context(str(fake_repo_path))
        assert result.project_name == "Test Project"
        assert result.project_version == kedro_version
        assert str(fake_repo_path.resolve() / "src") in sys.path
        get_project_metadata_mock.assert_called_with(fake_repo_path)

    def test_valid_context_with_env(self, mocker, monkeypatch, fake_repo_path):
        """Test getting project context when Kedro config environment is
        specified in the environment variable.
        """
        mocker.patch("kedro.config.config.ConfigLoader.get")
        monkeypatch.setenv("KEDRO_ENV", "my_fake_env")
        result = load_context(str(fake_repo_path))
        assert result.env == "my_fake_env"

    def test_invalid_path(self, tmp_path):
        """Test for loading context from an invalid path. """
        other_path = tmp_path / "other"
        other_path.mkdir()
        pattern = "Could not find the project configuration file 'pyproject.toml'"
        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            load_context(str(other_path))

    def test_pyproject_toml_has_missing_mandatory_keys(self, fake_repo_path):
        payload = {
            "tool": {
                "kedro": {"fake_key": "fake_value", "project_version": kedro_version}
            }
        }
        _create_kedro_config(fake_repo_path, payload)

        pattern = (
            "Missing required keys ['context_path', 'package_name', 'project_name'] "
            "from 'pyproject.toml'."
        )
        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            load_context(str(fake_repo_path))

    def test_pyproject_toml_has_extra_keys(self, fake_repo_path, fake_package_name):
        project_name = "Test Project"
        payload = {
            "tool": {
                "kedro": {
                    "context_path": f"{fake_package_name}.run.ProjectContext",
                    "project_version": kedro_version,
                    "project_name": project_name,
                    "package_name": fake_package_name,
                    "unexpected_key": "hello",
                }
            }
        }
        _create_kedro_config(fake_repo_path, payload)

        pattern = (
            "Found unexpected keys in 'pyproject.toml'. Make sure it "
            "only contains the following keys: ['context_path', "
            "'package_name', 'project_name', 'project_version', 'source_dir']."
        )
        with pytest.raises(RuntimeError, match=re.escape(pattern)):
            load_context(str(fake_repo_path))

    @pytest.mark.parametrize("source_dir", ["src", "./src", "./src/"])
    def test_pyproject_toml_valid_source_dir(
        self, monkeypatch, fake_package_name, fake_repo_path, source_dir,
    ):
        """Test for loading context from a valid source dir."""
        # test we are also adding source_dir to PYTHONPATH as well
        monkeypatch.delenv("PYTHONPATH")

        project_name = "Test Project"
        payload = {
            "tool": {
                "kedro": {
                    "context_path": f"{fake_package_name}.run.ProjectContext",
                    "project_version": kedro_version,
                    "project_name": project_name,
                    "package_name": fake_package_name,
                    "source_dir": source_dir,
                }
            }
        }
        _create_kedro_config(fake_repo_path, payload)

        result = load_context(str(fake_repo_path))
        assert result.project_name == project_name
        assert result.project_version == kedro_version
        assert str(fake_repo_path.resolve() / source_dir) in sys.path

    @pytest.mark.parametrize(
        "source_dir", ["../", "../src/", "./src/../..", "/User/user/root_project"]
    )
    def test_pyproject_toml_invalid_source_dir_pattern(
        self, fake_repo_path, source_dir, fake_package_name
    ):
        """Test for invalid pattern for source_dir that is not relative to the project path.
        """
        payload = {
            "tool": {
                "kedro": {
                    "context_path": f"{fake_package_name}.run.ProjectContext",
                    "source_dir": source_dir,
                    "project_version": kedro_version,
                    "project_name": "Test Project",
                    "package_name": fake_package_name,
                }
            }
        }
        _create_kedro_config(fake_repo_path, payload)
        source_path = (fake_repo_path / Path(source_dir).expanduser()).resolve()

        pattern = (
            f"Source path '{source_path}' has to be relative to your project root "
            f"'{fake_repo_path.resolve()}'"
        )
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            load_context(str(fake_repo_path))

    def test_source_path_does_not_exist(self, fake_repo_path, fake_package_name):
        """Test for a valid source_dir pattern, but it does not exist.
        """
        source_dir = "non_existent"
        payload = {
            "tool": {
                "kedro": {
                    "context_path": f"{fake_package_name}.run.ProjectContext",
                    "source_dir": source_dir,
                    "package_name": fake_package_name,
                    "project_version": kedro_version,
                    "project_name": "Test Project",
                }
            }
        }
        _create_kedro_config(fake_repo_path, payload)
        non_existent_path = (fake_repo_path / source_dir).expanduser().resolve()

        pattern = f"Source path '{non_existent_path}' cannot be found"
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            load_context(str(fake_repo_path))

    def test_pyproject_toml_default_source_dir(self, fake_repo_path, fake_package_name):
        """If source dir is missing (it is by default), `src` is used to import package
           due to backward compatibility.
        """
        project_name = "Test Project"
        payload = {
            "tool": {
                "kedro": {
                    "context_path": f"{fake_package_name}.run.ProjectContext",
                    "project_version": kedro_version,
                    "project_name": project_name,
                    "package_name": fake_package_name,
                }
            }
        }
        _create_kedro_config(fake_repo_path, payload)

        result = load_context(str(fake_repo_path))
        assert result.project_name == project_name
        assert result.project_version == kedro_version
        assert str(fake_repo_path.resolve() / "src") in sys.path


class TestLoadPackageContext:
    """Test loading context for running a Kedro project package
    """

    def test_load_valid_package_context(self, fake_repo_path, fake_package_name):
        result = load_package_context(
            project_path=fake_repo_path, package_name=fake_package_name
        )
        assert result.project_name == "Test Project"
        assert result.project_version == kedro_version

    def test_load_invalid_package_context(self, fake_repo_path):
        fake_package_name = "i-dont-exist"
        pattern = (
            f"Cannot load context object from {fake_package_name}.run.ProjectContext "
            f"for package {fake_package_name}."
        )
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            load_package_context(
                project_path=fake_repo_path, package_name=fake_package_name
            )
