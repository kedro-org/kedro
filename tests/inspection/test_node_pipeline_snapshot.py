"""Tests for node and pipeline inspection snapshots."""

from __future__ import annotations

import functools
import inspect
import os
from pathlib import Path

import pytest

from kedro.inspection.models import NodeSnapshot, NodeSourceSnapshot, PipelineSnapshot
from kedro.inspection.snapshot import (
    _build_pipeline_snapshots,
    _extract_node_func,
    _get_node_source_snapshot,
    _node_to_snapshot,
)
from kedro.pipeline import Pipeline, node


def _identity(x):
    return x


def _wraps_decorator(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


def _closure_decorator(func):
    def wrapper(*args, **kwargs):
        return func(*args, **kwargs)

    return wrapper


@_wraps_decorator
def _decorated_with_wraps(x):
    return x


@_closure_decorator
def _decorated_without_wraps(x):
    return x


_MODULE_DIR = Path(__file__).parent


@pytest.fixture
def simple_node():
    return node(
        _identity,
        inputs="raw",
        outputs="processed",
        name="identity_node",
        tags=["tag_b", "tag_a"],
    )


@pytest.fixture
def namespaced_node():
    return node(
        _identity,
        inputs="raw",
        outputs="processed",
        name="identity_node",
        namespace="data_science",
    )


@pytest.fixture
def simple_pipeline(simple_node):
    return Pipeline([simple_node])


class TestNodeSnapshot:
    def test_instantiation_defaults(self):
        snapshot = NodeSnapshot(name="my_node")
        assert snapshot.name == "my_node"
        assert snapshot.namespace is None
        assert snapshot.tags == []
        assert snapshot.inputs == []
        assert snapshot.outputs == []
        assert snapshot.func_name is None


class TestNodeToSnapshot:
    def test_populates_all_fields(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.name == simple_node.name
        assert snapshot.namespace == simple_node.namespace
        assert snapshot.inputs == simple_node.inputs
        assert snapshot.outputs == simple_node.outputs

    def test_func_name_populated(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.func_name == "_identity"

    def test_tags_are_sorted(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.tags == sorted(simple_node.tags)

    def test_namespace_populated(self, namespaced_node):
        snapshot = _node_to_snapshot(namespaced_node)
        assert snapshot.namespace == "data_science"

    def test_returns_node_snapshot_instance(self, simple_node):
        assert isinstance(_node_to_snapshot(simple_node), NodeSnapshot)


class TestPipelineSnapshot:
    def test_instantiation(self):
        node_snap = NodeSnapshot(name="n", inputs=["a"], outputs=["b"])
        snapshot = PipelineSnapshot(name="my_pipe", nodes=[node_snap])
        assert snapshot.name == "my_pipe"
        assert snapshot.nodes == [node_snap]
        assert snapshot.inputs == []
        assert snapshot.outputs == []


class TestBuildPipelineSnapshots:
    def test_returns_correct_name(self, simple_pipeline):
        snapshots = _build_pipeline_snapshots({"data_processing": simple_pipeline})
        assert len(snapshots) == 1
        assert snapshots[0].name == "data_processing"

    def test_nodes_in_execution_order(self):
        n1 = node(_identity, inputs="raw", outputs="intermediate", name="n1")
        n2 = node(_identity, inputs="intermediate", outputs="final", name="n2")
        pipeline = Pipeline([n2, n1])  # intentionally reversed

        snapshots = _build_pipeline_snapshots({"__default__": pipeline})
        node_names = [n.name for n in snapshots[0].nodes]
        assert node_names == [n.name for n in pipeline.nodes]

    def test_pipeline_inputs_and_outputs(self, simple_pipeline):
        snapshots = _build_pipeline_snapshots({"__default__": simple_pipeline})
        assert snapshots[0].inputs == sorted(simple_pipeline.inputs())
        assert snapshots[0].outputs == sorted(simple_pipeline.outputs())

    def test_empty_registry_returns_empty_list(self):
        assert _build_pipeline_snapshots({}) == []

    def test_none_pipelines_are_skipped(self, simple_pipeline):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline, "broken": None}
        )
        assert len(snapshots) == 1
        assert snapshots[0].name == "__default__"


class TestNodeSourceSnapshot:
    def test_instantiation_defaults(self):
        snapshot = NodeSourceSnapshot(name="my_node")
        assert snapshot.name == "my_node"
        assert snapshot.func_name is None
        assert snapshot.source_filepath is None
        assert snapshot.source_line_start is None
        assert snapshot.source_line_end is None
        assert snapshot.code is None

    def test_all_fields_set(self):
        snapshot = NodeSourceSnapshot(
            name="my_node",
            func_name="_identity",
            source_filepath="src/my_project/nodes.py",
            source_line_start=10,
            source_line_end=15,
            code="def _identity(x):\n    return x\n",
        )
        assert snapshot.func_name == "_identity"
        assert snapshot.source_filepath == "src/my_project/nodes.py"
        assert snapshot.source_line_start == 10
        assert snapshot.source_line_end == 15
        assert snapshot.code == "def _identity(x):\n    return x\n"


class TestExtractNodeFunc:
    def test_plain_function_unchanged(self):
        assert _extract_node_func(_identity) is _identity

    def test_bound_method_unwrapped(self):
        class _MyClass:
            def method(self, x):
                return x

        obj = _MyClass()
        result = _extract_node_func(obj.method)
        assert result is _MyClass.method

    def test_partial_unwrapped(self):
        partial_func = functools.partial(_identity, 42)
        result = _extract_node_func(partial_func)
        assert result is _identity

    def test_wrapped_decorator_unwrapped(self):
        result = _extract_node_func(_decorated_with_wraps)
        assert result is _decorated_with_wraps.__wrapped__

    def test_closure_decorator_unwrapped(self):
        result = _extract_node_func(_decorated_without_wraps)
        assert result.__name__ == "_decorated_without_wraps"


class TestGetNodeSourceSnapshot:
    def test_returns_source_snapshot_for_known_node(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path
        )
        assert isinstance(snapshot, NodeSourceSnapshot)
        assert snapshot.name == "identity_node"
        assert snapshot.func_name == "_identity"

    def test_source_filepath_and_line_range_populated(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path, include_code=False
        )
        assert snapshot.source_filepath is not None
        assert snapshot.source_line_start is not None
        assert snapshot.source_line_end is not None
        assert snapshot.source_line_end >= snapshot.source_line_start

    def test_code_populated_when_include_code_true(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path, include_code=True
        )
        assert snapshot.code is not None
        assert "def _identity" in snapshot.code

    @pytest.mark.parametrize(
        "decorated_func,node_name,expected_source",
        [
            (_decorated_with_wraps, "wraps_decorated_node", "_decorated_with_wraps"),
            (
                _decorated_without_wraps,
                "closure_decorated_node",
                "_decorated_without_wraps",
            ),
        ],
    )
    def test_decorated_node_code_uses_wrapped_function_source(
        self, decorated_func, node_name, expected_source, tmp_path
    ):
        decorated_node = node(
            decorated_func, inputs="raw", outputs="processed", name=node_name
        )
        pipeline_dict = {"__default__": Pipeline([decorated_node])}

        snapshot = _get_node_source_snapshot(node_name, pipeline_dict, tmp_path)

        assert snapshot.code is not None
        assert f"def {expected_source}" in snapshot.code
        assert "def wrapper" not in snapshot.code

    def test_code_is_none_when_include_code_false(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path, include_code=False
        )
        assert snapshot.code is None

    def test_line_range_matches_inspect(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path
        )
        _, expected_start = inspect.getsourcelines(_identity)
        assert snapshot.source_line_start == expected_start

    def test_raises_key_error_for_unknown_node(self, simple_node, tmp_path):
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        with pytest.raises(KeyError, match="no_such_node"):
            _get_node_source_snapshot("no_such_node", pipeline_dict, tmp_path)

    def test_node_found_across_multiple_pipelines(self, simple_node, tmp_path):
        other_node = node(_identity, inputs="a", outputs="b", name="other_node")
        pipeline_dict = {
            "pipe_a": Pipeline([other_node]),
            "pipe_b": Pipeline([simple_node]),
        }
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path
        )
        assert snapshot.name == "identity_node"

    def test_none_pipelines_are_skipped(self, simple_node, tmp_path):
        pipeline_dict = {"broken": None, "__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path
        )
        assert snapshot.name == "identity_node"

    def test_source_filepath_is_project_relative_when_inside_project(
        self, simple_node
    ):
        # Use this file's directory so the source path becomes relative.
        project_path = _MODULE_DIR
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, project_path
        )
        assert snapshot.source_filepath is not None
        assert not os.path.isabs(snapshot.source_filepath)

    def test_source_filepath_is_absolute_when_outside_project(
        self, simple_node, tmp_path
    ):
        # tmp_path is unrelated to the source file, so the path stays absolute.
        pipeline_dict = {"__default__": Pipeline([simple_node])}
        snapshot = _get_node_source_snapshot(
            "identity_node", pipeline_dict, tmp_path
        )
        assert snapshot.source_filepath is not None
        assert os.path.isabs(snapshot.source_filepath)
