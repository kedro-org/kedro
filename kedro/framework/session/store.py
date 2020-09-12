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
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict

from kedro.utils import load_obj


class BaseSessionStore(UserDict):
    """``BaseSessionStore`` is the base class for all session stores.
    ``BaseSessionStore`` is an ephemeral store implementation that doesn't
    persist the session data.
    """

    def __init__(self, path: str, session_id: str):
        self._path = path
        self._session_id = session_id
        super().__init__(self.read())

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> "BaseSessionStore":
        """Create a session store instance using the configuration provided.

        Args:
            config: Session store config dictionary.

        Raises:
            ValueError: When the function fails to create the session store
                from its config.

        Returns:
            An instance of an ``BaseSessionStore`` subclass.
        """
        config = deepcopy(config)

        class_obj = config.pop("type", BaseSessionStore)
        if isinstance(class_obj, str):
            class_obj = load_obj(class_obj, BaseSessionStore.__module__)

        classpath = f"{class_obj.__module__}.{class_obj.__qualname__}"

        if not issubclass(class_obj, BaseSessionStore):
            raise ValueError(
                f"Store type `{classpath}` is invalid: "
                f"it must extend `BaseSessionStore`."
            )

        try:
            store = class_obj(**config)
        except TypeError as err:
            raise ValueError(
                f"\n{err}.\nStore config must only contain arguments valid "
                f"for the constructor of `{classpath}`."
            ) from err
        except Exception as err:
            raise ValueError(
                f"\n{err}.\nFailed to instantiate session store of type `{classpath}`."
            ) from err
        return store

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(__name__)

    def read(self) -> Dict[str, Any]:
        """Read the data from the session store.

        Returns:
            A mapping containing the session store data.
        """
        self._logger.warning(
            "`read()` not implemented for `%s`. Assuming empty store.",
            self.__class__.__name__,
        )
        return {}

    def save(self):
        """Persist the session store"""
        self._logger.warning(
            "`save()` not implemented for `%s`. Skipping the step.",
            self.__class__.__name__,
        )


class ShelveStore(BaseSessionStore):
    """Stores the session data on disk using `shelve` package."""

    @property
    def _location(self) -> Path:
        return Path(self._path).expanduser().resolve() / self._session_id / "store"

    def read(self) -> Dict[str, Any]:
        """Read the data from disk using `shelve` package."""
        data = {}  # type: Dict[str, Any]
        try:
            with shelve.open(str(self._location), flag="r") as _sh:
                data = dict(_sh)
        except dbm.error:
            pass
        return data

    def save(self) -> None:
        """Save the data on disk using `shelve` package."""
        self._location.parent.mkdir(parents=True, exist_ok=True)

        with shelve.open(str(self._location)) as _sh:
            keys_to_del = _sh.keys() - self.data.keys()
            for key in keys_to_del:
                del _sh[key]

            _sh.update(self.data)
