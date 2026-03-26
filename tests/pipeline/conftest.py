import sys

import pytest


@pytest.fixture(autouse=True)
def reset_warned_dotted_dataset_names():
    """Reset the dotted dataset name warning set before and after each test."""
    node_module = sys.modules["kedro.pipeline.node"]
    node_module._warned_dotted_dataset_names.clear()
    yield
    node_module._warned_dotted_dataset_names.clear()
