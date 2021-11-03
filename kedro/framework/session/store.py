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
