from random import random

import pytest

from kedro.framework.hooks import create_hook_manager
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline, node


def source():
    return "stuff"


def identity(arg):
    return arg


def sink(arg):  # pylint: disable=unused-argument
    pass


def fan_in(*args):
    return args


def exception_fn(arg):
    raise Exception("test exception")


def return_none(arg):
    arg = None
    return arg


def return_not_serializable(arg):  # pylint: disable=unused-argument
    return lambda x: x


@pytest.fixture
def catalog():
    return DataCatalog()


@pytest.fixture
def hook_manager():
    return create_hook_manager()


@pytest.fixture
def fan_out_fan_in():
    return Pipeline(
        [
            node(identity, "A", "B"),
            node(identity, "B", "C"),
            node(identity, "B", "D"),
            node(identity, "B", "E"),
            node(fan_in, ["C", "D", "E"], "Z"),
        ]
    )


@pytest.fixture
def branchless_no_input_pipeline():
    """The pipeline runs in the order A->B->C->D->E."""
    return Pipeline(
        [
            node(identity, "D", "E", name="node1"),
            node(identity, "C", "D", name="node2"),
            node(identity, "A", "B", name="node3"),
            node(identity, "B", "C", name="node4"),
            node(random, None, "A", name="node5"),
        ]
    )


@pytest.fixture
def branchless_pipeline():
    return Pipeline(
        [
            node(identity, "ds1", "ds2", name="node1"),
            node(identity, "ds2", "ds3", name="node2"),
        ]
    )


@pytest.fixture
def saving_result_pipeline():
    return Pipeline([node(identity, "ds", "dsX")])


@pytest.fixture
def saving_none_pipeline():
    return Pipeline(
        [node(random, None, "A"), node(return_none, "A", "B"), node(identity, "B", "C")]
    )
