"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import os
import sys

import pytest

from kedro.io.core import AbstractDataset


@pytest.fixture(autouse=True)
def preserve_system_context():
    """
    Revert some changes to the application context tests do to isolate them.
    """
    old_path = sys.path.copy()
    old_cwd = os.getcwd()
    yield
    sys.path = old_path

    if os.getcwd() != old_cwd:
        os.chdir(old_cwd)  # pragma: no cover


class PersistentTestDataset(AbstractDataset):
    def __init__(self, load=None, save=None, exists=None):
        self._load_fn = load or (lambda: None)
        self._save_fn = save or (lambda data: None)
        self._exists_fn = exists
        if exists is not None:
            # Dynamically add _exists only if exists is provided
            self._exists = lambda: self._exists_fn()

    def _load(self):
        return self._load_fn()

    def _save(self, data):
        self._save_fn(data)

    def _describe(self) -> dict:
        return {}


@pytest.fixture
def persistent_test_dataset():
    return PersistentTestDataset
