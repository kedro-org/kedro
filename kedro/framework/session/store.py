"""This module implements a dict-like store object used to persist Kedro sessions."""
from __future__ import annotations

import logging
from collections import UserDict
from typing import Any


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

    def read(self) -> dict[str, Any]:
        """Read the data from the session store.

        Returns:
            A mapping containing the session store data.
        """
        self._logger.debug(
            "'read()' not implemented for '%s'. Assuming empty store.",
            self.__class__.__name__,
        )
        return {}

    def save(self):
        """Persist the session store"""
        self._logger.debug(
            "'save()' not implemented for '%s'. Skipping the step.",
            self.__class__.__name__,
        )
