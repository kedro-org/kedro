import pytest

from kedro.contrib.idempotent.idempotent_node import IdempotentNode
from kedro.pipeline import node


# Different dummy func based on the number of arguments
def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


@pytest.fixture
def simple_tuple_node_list():
    return [
        (identity, "A", "B"),
        (biconcat, ["A", "B"], "C"),
        (identity, "C", ["D", "E"]),
        (biconcat, ["H", "I"], ["J", "K"]),
        (identity, "J", dict(result="K")),
        (biconcat, ["J", "K"], dict(result="L")),
        (identity, dict(input1="J"), "L"),
        (identity, dict(input1="J"), ["L", "M"]),
        (identity, dict(input1="J"), dict(result="K")),
        (constant_output, None, "M"),
        (biconcat, ["N", "O"], None),
        (lambda x: None, "F", "G"),
        (lambda x: ("a", "b"), "G", ["X", "Y"]),
    ]


class TestIdempotentNode:

    def test_should_have_different_uuids(self, simple_tuple_node_list):
        for tup in simple_tuple_node_list:
            node1 = IdempotentNode(*tup)
            node2 = IdempotentNode(*tup)
            assert node1.generate_idempotency_id() != node2.generate_idempotency_id()
