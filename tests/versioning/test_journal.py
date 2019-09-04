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
import json

import pytest

from kedro.versioning.journal import VersionJournal, _git_sha


@pytest.fixture
def fake_git_sha(mocker):
    return mocker.patch("kedro.versioning.journal._git_sha", return_value="git_sha")


@pytest.mark.usefixtures("fake_git_sha")
class TestVersionJournal:
    def test_context_record(self, tmp_path, caplog):
        """Test journal initialisation"""
        record_data = {"project_path": str(tmp_path)}
        _ = VersionJournal(record_data)

        result = json.loads(caplog.record_tuples[0][2])
        assert result["type"] == "ContextJournalRecord"
        assert result["project_path"] == str(tmp_path)
        assert result["git_sha"] == "git_sha"
        assert "id" in result

    def test_invalid_context_record(self, tmp_path, caplog):
        record_data = {"project_path": str(tmp_path), "blah": lambda x: x}
        _ = VersionJournal(record_data)
        assert "Unable to record" in caplog.record_tuples[0][2]

    def test_log_catalog(self, tmp_path, caplog):
        record_data = {"project_path": str(tmp_path)}
        journal = VersionJournal(record_data)
        journal.log_catalog("fake_data", "fake_operation", "fake_version")
        context_log = json.loads(caplog.record_tuples[0][2])
        catalog_log = json.loads(caplog.record_tuples[1][2])

        assert catalog_log["type"] == "DatasetJournalRecord"
        assert catalog_log["name"] == "fake_data"
        assert catalog_log["operation"] == "fake_operation"
        assert catalog_log["version"] == "fake_version"
        assert catalog_log["id"] == context_log["id"]


def test_git_sha(tmp_path, mocker):
    mocker.patch("subprocess.check_output", return_value="mocked_return".encode())
    result = _git_sha(tmp_path)
    assert result == "mocked_return"


def test_invalid_git_sha(tmp_path, caplog):
    _git_sha(tmp_path)
    assert "Unable to git describe" in caplog.record_tuples[0][2]
