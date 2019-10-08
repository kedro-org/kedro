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

import os
import sys

import pytest

import kedro
from kedro.context import KedroContextError, load_context


class TestLoadContext:
    def test_valid_context(self, mocker, fake_repo_path):
        """Test getting project context."""
        # Disable logging.config.dictConfig in KedroContext._setup_logging as
        # it changes logging.config and affects other unit tests
        mocker.patch("logging.config.dictConfig")
        result = load_context(str(fake_repo_path))
        assert result.project_name == "Test Project"
        assert result.project_version == kedro.__version__
        assert str(fake_repo_path.resolve() / "src") in sys.path
        assert os.getcwd() == str(fake_repo_path.resolve())

    def test_invalid_path(self, tmp_path):
        """Test for loading context from an invalid path. """
        other_path = tmp_path / "other"
        other_path.mkdir()
        pattern = r"Could not find '\.kedro\.yml'"
        with pytest.raises(KedroContextError, match=pattern):
            load_context(str(other_path))

    def test_kedro_yml_invalid_format(self, fake_repo_path):
        """Test for loading context from an invalid path. """
        kedro_yml_path = fake_repo_path / ".kedro.yml"
        kedro_yml_path.write_text("!!")  # Invalid YAML
        pattern = r"Failed to parse '\.kedro\.yml' file"
        with pytest.raises(KedroContextError, match=pattern):
            load_context(str(fake_repo_path))

    def test_kedro_yml_has_no_context_path(self, fake_repo_path):
        """Test for loading context from an invalid path. """
        kedro_yml_path = fake_repo_path / ".kedro.yml"
        kedro_yml_path.write_text("fake_key: fake_value\n")
        pattern = r"'\.kedro\.yml' doesn't have a required `context_path` field"
        with pytest.raises(KedroContextError, match=pattern):
            load_context(str(fake_repo_path))
