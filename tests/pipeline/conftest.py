import pytest


@pytest.fixture(autouse=True)
def reset_dotted_dataset_name_warned():
    """Reset the dotted dataset name warning flag before and after each test."""
    from kedro.pipeline.node import Node

    if hasattr(Node, "__dotted_dataset_name_warned__"):
        delattr(Node, "__dotted_dataset_name_warned__")
    yield
    if hasattr(Node, "__dotted_dataset_name_warned__"):
        delattr(Node, "__dotted_dataset_name_warned__")
