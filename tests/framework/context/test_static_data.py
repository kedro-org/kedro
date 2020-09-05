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
from pathlib import Path

import pytest

from kedro.framework.context import (
    KedroContextError,
    get_static_project_data,
    validate_source_path,
)


class TestValidateSourcePath:
    @pytest.mark.parametrize(
        "source_dir", [".", "src", "./src", "src/nested", "src/nested/nested"]
    )
    def test_valid_source_path(self, tmp_path, source_dir):
        source_path = (tmp_path / source_dir).resolve()
        source_path.mkdir(parents=True, exist_ok=True)
        validate_source_path(source_path, tmp_path.resolve())

    @pytest.mark.parametrize("source_dir", ["..", "src/../..", "~"])
    def test_invalid_source_path(self, tmp_path, source_dir):
        source_dir = Path(source_dir).expanduser()
        source_path = (tmp_path / source_dir).resolve()
        source_path.mkdir(parents=True, exist_ok=True)

        pattern = re.escape(
            f"Source path '{source_path}' has to be relative to your project root "
            f"'{tmp_path.resolve()}'"
        )
        with pytest.raises(KedroContextError, match=pattern):
            validate_source_path(source_path, tmp_path.resolve())

    def test_non_existent_source_path(self, tmp_path):
        source_path = (tmp_path / "non_existent").resolve()

        pattern = re.escape(f"Source path '{source_path}' cannot be found.")
        with pytest.raises(KedroContextError, match=pattern):
            validate_source_path(source_path, tmp_path.resolve())


class TestGetStaticProjectData:
    project_path = Path.cwd()

    def test_no_config_files(self, mocker):
        mocker.patch.object(Path, "is_file", return_value=False)

        pattern = (
            f"Could not find any of configuration files '.kedro.yml, pyproject.toml' "
            f"in {self.project_path}"
        )
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            get_static_project_data(self.project_path)

    def test_kedro_yml_invalid_format(self, tmp_path):
        """Test for loading context from an invalid path. """
        kedro_yml_path = tmp_path / ".kedro.yml"
        kedro_yml_path.write_text("!!")  # Invalid YAML
        pattern = "Failed to parse '.kedro.yml' file"
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            get_static_project_data(str(tmp_path))

    def test_toml_invalid_format(self, tmp_path):
        """Test for loading context from an invalid path. """
        toml_path = tmp_path / "pyproject.toml"
        toml_path.write_text("!!")  # Invalid TOML
        pattern = "Failed to parse 'pyproject.toml' file"
        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            get_static_project_data(str(tmp_path))

    def test_valid_yml_file_exists(self, mocker):
        # Both yml and toml files exist
        mocker.patch.object(Path, "is_file", return_value=True)
        mocker.patch("anyconfig.load", return_value={})

        static_data = get_static_project_data(self.project_path)

        # Using default source directory
        assert static_data == {
            "source_dir": self.project_path / "src",
            "config_file": self.project_path / ".kedro.yml",
        }

    def test_valid_toml_file(self, mocker):
        # .kedro.yml doesn't exists
        mocker.patch.object(Path, "is_file", side_effect=[False, True])
        mocker.patch("anyconfig.load", return_value={"tool": {"kedro": {}}})

        static_data = get_static_project_data(self.project_path)

        # Using default source directory
        assert static_data == {
            "source_dir": self.project_path / "src",
            "config_file": self.project_path / "pyproject.toml",
        }

    def test_toml_file_without_kedro_section(self, mocker):
        mocker.patch.object(Path, "is_file", side_effect=[False, True])
        mocker.patch("anyconfig.load", return_value={})

        pattern = "There's no '[tool.kedro]' section in the 'pyproject.toml'."

        with pytest.raises(KedroContextError, match=re.escape(pattern)):
            get_static_project_data(self.project_path)

    def test_source_dir_specified_in_yml(self, mocker):
        mocker.patch.object(Path, "is_file", side_effect=[True, False])
        source_dir = "test_dir"
        mocker.patch("anyconfig.load", return_value={"source_dir": source_dir})

        static_data = get_static_project_data(self.project_path)

        assert static_data["source_dir"] == self.project_path / source_dir

    def test_source_dir_specified_in_toml(self, mocker):
        mocker.patch.object(Path, "is_file", side_effect=[False, True])
        source_dir = "test_dir"
        mocker.patch(
            "anyconfig.load",
            return_value={"tool": {"kedro": {"source_dir": source_dir}}},
        )

        static_data = get_static_project_data(self.project_path)

        assert static_data["source_dir"] == self.project_path / source_dir
