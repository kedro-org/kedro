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
import logging
from pathlib import Path

import pytest

from kedro.framework.session.store import BaseSessionStore, ShelveStore

FAKE_SESSION_ID = "fake_session_id"
STORE_LOGGER_NAME = "kedro.framework.session.store"


class TestBaseStore:
    def test_init(self, caplog):
        path = "fake_path"
        store = BaseSessionStore(path, FAKE_SESSION_ID)
        assert store == dict()
        assert store._path == path
        assert store._session_id == FAKE_SESSION_ID

        expected_log_messages = [
            "`read()` not implemented for `BaseSessionStore`. Assuming empty store."
        ]
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.INFO
        ]
        assert actual_log_messages == expected_log_messages

    def test_save(self, caplog):
        path = "fake_path"
        store = BaseSessionStore(path, FAKE_SESSION_ID)
        store.save()
        assert store == dict()

        expected_log_messages = [
            "`read()` not implemented for `BaseSessionStore`. Assuming empty store.",
            "`save()` not implemented for `BaseSessionStore`. Skipping the step.",
        ]
        actual_log_messages = [
            rec.getMessage()
            for rec in caplog.records
            if rec.name == STORE_LOGGER_NAME and rec.levelno == logging.INFO
        ]
        assert actual_log_messages == expected_log_messages


@pytest.fixture
def shelve_path(tmp_path):
    return Path(tmp_path / "path" / "to" / "sessions")


class TestShelveStore:
    def test_empty(self, shelve_path):
        shelve = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        assert shelve == dict()
        assert shelve._location == shelve_path / FAKE_SESSION_ID / "store"
        assert not shelve_path.exists()

    def test_save(self, shelve_path):
        assert not shelve_path.exists()

        shelve = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        shelve["shelve_path"] = shelve_path
        shelve.save()

        assert (shelve_path / FAKE_SESSION_ID).is_dir()

        reloaded = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        assert reloaded == {"shelve_path": shelve_path}

    def test_update(self, shelve_path):
        shelve = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        shelve["shelve_path"] = shelve_path
        shelve.save()

        shelve.update(new_key="new_value")
        del shelve["shelve_path"]
        reloaded = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        assert reloaded == {"shelve_path": shelve_path}  # changes not saved yet

        shelve.save()
        reloaded = ShelveStore(str(shelve_path), FAKE_SESSION_ID)
        assert reloaded == {"new_key": "new_value"}
