"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import os
import sys

import pytest


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
