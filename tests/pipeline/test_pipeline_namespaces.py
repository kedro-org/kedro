import warnings

import pytest

from kedro.pipeline import Pipeline, node


def identity(x):
    return x


def branching(x):
    return x, x


def test_pipeline_with_interrupted_namespace():
    # Create a pipeline with an interrupted namespace
    nodes = [
        node(identity, "A", "B", name="node1", namespace="ns1"),
        node(identity, "B", "C", name="node2"),  # No namespace interrupts the flow
        node(identity, "C", "D", name="node3", namespace="ns1"),  # Namespace comes back
    ]

    # Capture warnings during pipeline creation
    with pytest.warns() as warns:
        Pipeline(nodes)

        assert len(warns) == 1
        assert (
            "Namespace 'ns1' is interrupted by nodes ['node2'] and thus invalid."
            in str(warns[0].message)
        )


def test_pipeline_with_continuous_namespace():
    # Create a pipeline with continuous namespace
    nodes = [
        node(identity, "A", "B", name="node1", namespace="ns1"),
        node(identity, "B", "C", name="node2", namespace="ns1"),
        node(identity, "C", "D", name="node3", namespace="ns1"),
    ]

    # No warning should be raised
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # Convert warnings to exceptions
        Pipeline(nodes)


def test_pipeline_with_child_namespace():
    # Create a pipeline with child namespaces
    nodes = [
        node(identity, "A", "B", name="node1", namespace="ns1"),
        node(identity, "B", "C", name="node2", namespace="ns1.child"),
        node(identity, "C", "D", name="node3", namespace="ns1"),
    ]

    # No warning should be raised as child namespaces are allowed
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Pipeline(nodes)


def test_pipeline_with_parallel_namespaces():
    # Create a pipeline with parallel branches having different namespaces
    nodes = [
        node(branching, "A", ["B", "C"], name="source", namespace="common"),
        node(identity, "B", "D", name="node1", namespace="ns1"),
        node(identity, "C", "E", name="node2", namespace="ns2"),
    ]

    # No warning should be raised for parallel namespaces
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        Pipeline(nodes)


def test_pipeline_with_complex_namespace_interruption():
    # Create a more complex pipeline with namespace interruption
    nodes = [
        node(identity, "A", "B", name="node1", namespace="ns1"),
        node(identity, "C", "D", name="node2", namespace="ns1.child.grandchild"),
        node(identity, "D", "E", name="node3", namespace="ns2"),  # Different namespace
        node(
            identity, "E", "F", name="node4", namespace="ns1.child"
        ),  # Back to original namespace
        node(
            identity, "F", "G", name="node5", namespace="ns1"
        ),  # Back to original namespace
    ]

    # Should warn about both interrupted namespaces
    with pytest.warns() as warns:
        Pipeline(nodes)

    # Check that both warning messages are present
    warn_msgs = [str(w.message) for w in warns]
    assert (
        "Namespace 'ns1.child' is interrupted by nodes ['ns2.node3'] and thus invalid."
        in warn_msgs
    )
    assert (
        "Namespace 'ns1' is interrupted by nodes ['ns2.node3', 'ns1.child.node4'] and thus invalid."
        in warn_msgs
    )
