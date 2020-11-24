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
from copy import deepcopy
from pathlib import Path

import pytest

from kedro import __version__ as kedro_version
from kedro.framework.project import _generate_toml_config
from kedro.framework.project.metadata import KedroConfigParserError


class TestPyProjectTomlGeneration:
    PACKAGE_NAME = "mypackage"
    PACKAGE_PATH = Path(f"/tmp/path/to/{PACKAGE_NAME}")
    CONF_PATH = Path("/path/to/config/pyproject.toml")

    EXPECTED_DATA = {
        "tool": {
            "kedro": {
                "package_name": PACKAGE_NAME,
                "project_name": PACKAGE_NAME,
                "project_version": kedro_version,
                "source_dir": str(PACKAGE_PATH.parent),
            }
        }
    }

    @staticmethod
    @pytest.fixture(autouse=True)
    def load_obj_mock(mocker):
        yield mocker.patch(
            "kedro.framework.project.metadata.load_obj", side_effect=AttributeError
        )

    @staticmethod
    @pytest.fixture(autouse=True)
    def is_file_mock(mocker):
        yield mocker.patch.object(Path, "is_file", return_value=False)

    @staticmethod
    @pytest.fixture
    def anyconfig_dump_mock(mocker):
        yield mocker.patch("anyconfig.dump")

    @staticmethod
    @pytest.fixture
    def anyconfig_load_mock(mocker):
        yield mocker.patch("anyconfig.load")

    def test_toml_is_missing_with_context_path(
        self, anyconfig_dump_mock, load_obj_mock
    ):
        load_obj_mock.side_effect = None

        expected_data = deepcopy(self.EXPECTED_DATA)
        expected_data["tool"]["kedro"][
            "context_path"
        ] = f"{self.PACKAGE_NAME}.run.ProjectContext"

        _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

        anyconfig_dump_mock.assert_called_once_with(expected_data, self.CONF_PATH)

    @pytest.mark.parametrize("exception", [ModuleNotFoundError, AttributeError])
    def test_toml_is_missing_no_context_path(
        self, anyconfig_dump_mock, load_obj_mock, exception
    ):
        load_obj_mock.side_effect = exception

        _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

        anyconfig_dump_mock.assert_called_once_with(self.EXPECTED_DATA, self.CONF_PATH)

    def test_toml_exists_with_kedro_section(
        self, is_file_mock, anyconfig_dump_mock, anyconfig_load_mock
    ):
        is_file_mock.return_value = True
        anyconfig_load_mock.return_value = {"tool": {"kedro": {}}}

        _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

        assert not anyconfig_dump_mock.called

    def test_existing_toml_is_broken(self, is_file_mock, anyconfig_load_mock):
        is_file_mock.return_value = True
        anyconfig_load_mock.side_effect = Exception

        pattern = f"Failed to parse '{self.CONF_PATH}' file"
        with pytest.raises(KedroConfigParserError, match=re.escape(pattern)):
            _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

    def test_toml_exists_without_kedro_section_in_tool(
        self, is_file_mock, anyconfig_dump_mock, anyconfig_load_mock
    ):
        is_file_mock.return_value = True
        existing_data = {"tool": {"isort": {"line_length": 80}}}
        anyconfig_load_mock.return_value = deepcopy(existing_data)

        _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

        expected_data = deepcopy(self.EXPECTED_DATA["tool"])
        # `[tool.*]` section exists
        # `anyconfig.dump()` should be called with `existing_data` updated with
        # Kedro configuration
        existing_data["tool"].update(expected_data)

        anyconfig_dump_mock.assert_called_once_with(existing_data, self.CONF_PATH)

    def test_toml_exists_without_kedro_section_and_tool(
        self, is_file_mock, anyconfig_dump_mock, anyconfig_load_mock
    ):
        is_file_mock.return_value = True
        existing_data = {"notool": {"isort": {"line_length": 80}}}
        anyconfig_load_mock.return_value = deepcopy(existing_data)

        _generate_toml_config(self.CONF_PATH.parent, self.PACKAGE_PATH)

        expected_data = deepcopy(self.EXPECTED_DATA["tool"])
        # `[tool.*]` section doesn't exist
        # `anyconfig.dump()` should be called with `existing_data` updated with
        # Kedro configuration
        existing_data["tool"] = expected_data

        anyconfig_dump_mock.assert_called_once_with(existing_data, self.CONF_PATH)
