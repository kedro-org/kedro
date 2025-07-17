"""
This file contains the fixtures that are reusable by any tests within
this directory. You don't need to import the fixtures as pytest will
discover them automatically. More info here:
https://docs.pytest.org/en/latest/fixture.html
"""

import os
import sys

import pytest
import pandas as pd


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


@pytest.fixture
def dummy_dataframe():
    """Return a dummy pandas DataFrame for testing."""
    return pd.DataFrame({"col1": [1, 2], "col2": [4, 5], "col3": [5, 6]})


@pytest.fixture
def dummy_dataframe_simple():
    """Return a simple dummy pandas DataFrame for testing."""
    return pd.DataFrame({"test": [1, 2]})
