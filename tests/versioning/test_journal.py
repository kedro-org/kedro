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
# pylint: disable=protected-access

import json
import logging
import logging.config
from importlib import reload

import pytest

from kedro.versioning.journal import Journal, _git_sha


@pytest.fixture()
def setup_logging(tmp_path):
    config = {
        "version": 1,
        "loggers": {
            "kedro.journal": {
                "level": "INFO",
                "handlers": ["journal_file_handler"],
                "propagate": False,
            }
        },
        "handlers": {
            "journal_file_handler": {
                "class": "kedro.versioning.journal.JournalFileHandler",
                "level": "INFO",
                "base_dir": str(tmp_path),
            }
        },
    }
    reload(logging)
    logging.config.dictConfig(config)


@pytest.fixture
def fake_git_sha(mocker):
    return mocker.patch("kedro.versioning.journal._git_sha", return_value="git_sha")


@pytest.mark.usefixtures("fake_git_sha")
class TestJournal:
    @pytest.mark.usefixtures("setup_logging")
    def test_context_record(self, tmp_path):
        """Test journal initialisation"""
        record_data = {"run_id": "fake_id", "project_path": str(tmp_path)}
        journal = Journal(record_data)
        file_path = list(tmp_path.glob("journal_*"))

        assert len(file_path) == 1
        assert journal.run_id in str(file_path[0])
        log = json.loads(file_path[0].read_text())
        assert log["type"] == "ContextJournalRecord"
        assert log["project_path"] == str(tmp_path)
        assert log["git_sha"] == "git_sha"
        assert "run_id" in log

    def test_invalid_context_record(self, tmp_path, caplog):
        record_data = {
            "run_id": "fake_id",
            "project_path": str(tmp_path),
            "blah": lambda x: x,
        }
        _ = Journal(record_data)

        assert "Unable to record" in caplog.record_tuples[0][2]

    @pytest.mark.usefixtures("setup_logging")
    def test_log_catalog(self, tmp_path):
        record_data = {"run_id": "fake_id", "project_path": str(tmp_path)}
        journal = Journal(record_data)
        journal.log_catalog("fake_data", "fake_operation", "fake_version")
        file_path = list(tmp_path.glob("journal_*"))

        assert journal.run_id in str(file_path[0])
        assert len(file_path) == 1
        with file_path[0].open() as log_file:
            context_log = json.loads(log_file.readline())
            catalog_log = json.loads(log_file.readline())
            assert catalog_log["type"] == "DatasetJournalRecord"
            assert catalog_log["name"] == "fake_data"
            assert catalog_log["operation"] == "fake_operation"
            assert catalog_log["version"] == "fake_version"
            assert catalog_log["run_id"] == context_log["run_id"]


def test_git_sha(tmp_path, mocker):
    mocker.patch("subprocess.check_output", return_value="mocked_return".encode())
    result = _git_sha(tmp_path)
    assert result == "mocked_return"


def test_invalid_git_sha(tmp_path, caplog):
    _git_sha(tmp_path)
    assert "Unable to git describe" in caplog.record_tuples[0][2]
