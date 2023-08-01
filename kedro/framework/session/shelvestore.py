"""This module implements a dict-like store object used to persist Kedro sessions.
This module is separated from store.py to ensure it's only imported when exported explicitly.
"""
from __future__ import annotations

import dbm
import shelve
from multiprocessing import Lock
from pathlib import Path
from typing import Any

from .store import BaseSessionStore


class ShelveStore(BaseSessionStore):
    """Stores the session data on disk using `shelve` package.
    This is an example of how to persist data on disk."""

    _lock = Lock()

    @property
    def _location(self) -> Path:
        return Path(self._path).expanduser().resolve() / self._session_id / "store"

    def read(self) -> dict[str, Any]:
        """Read the data from disk using `shelve` package."""
        data: dict[str, Any] = {}
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
