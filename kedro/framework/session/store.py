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
# pylint: disable=too-many-ancestors
"""This module implements a dict-like store object used to persist Kedro sessions."""
import dbm
import logging
import shelve
from collections import UserDict
from multiprocessing import Lock
from pathlib import Path
from typing import Any, Dict


class BaseSessionStore(UserDict):
    """``BaseSessionStore`` is the base class for all session stores.
    ``BaseSessionStore`` is an ephemeral store implementation that doesn't
    persist the session data.
    """

    def __init__(self, path: str, session_id: str):
        self._path = path
        self._session_id = session_id
        super().__init__(self.read())

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def read(self) -> Dict[str, Any]:
        """Read the data from the session store.

        Returns:
            A mapping containing the session store data.
        """
        self._logger.info(
            "`read()` not implemented for `%s`. Assuming empty store.",
            self.__class__.__name__,
        )
        return {}

    def save(self):
        """Persist the session store"""
        self._logger.info(
            "`save()` not implemented for `%s`. Skipping the step.",
            self.__class__.__name__,
        )


class ShelveStore(BaseSessionStore):
    """Stores the session data on disk using `shelve` package."""

    _lock = Lock()

    @property
    def _location(self) -> Path:
        return Path(self._path).expanduser().resolve() / self._session_id / "store"

    def read(self) -> Dict[str, Any]:
        """Read the data from disk using `shelve` package."""
        data = {}  # type: Dict[str, Any]
        try:
            with shelve.open(str(self._location), flag="r") as _sh:  # nosec
                data = dict(_sh)
        except dbm.error:
            pass
        return data

    def save(self) -> None:
        """Save the data on disk using `shelve` package."""
        location = self._location
        location.parent.mkdir(parents=True, exist_ok=True)

        with self._lock, shelve.open(str(location)) as _sh:  # nosec
            keys_to_del = _sh.keys() - self.data.keys()
            for key in keys_to_del:
                del _sh[key]

            _sh.update(self.data)
