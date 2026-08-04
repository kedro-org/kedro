"""Tests for NodeSnapshot, PipelineSnapshot models and their builders."""

from __future__ import annotations

import importlib.util
import inspect
from functools import partial
from pathlib import Path

import pytest

from kedro.inspection.models import NodeSnapshot, NodeSourceSnapshot, PipelineSnapshot
from kedro.inspection.snapshot import (
    _build_pipeline_snapshots,
    _node_to_snapshot,
    _resolve_node_source,
)
from kedro.pipeline import Pipeline, node


@pytest.fixture
def project_path(tmp_path):
    return tmp_path


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
def node_with_project_source(project_path):
    func = _load_func_from_project(
        project_path,
        "def process(x):\n    return x\n",
        "process",
    )
    return node(func, inputs="raw", outputs="processed", name="process_node")


@pytest.fixture
def simple_pipeline(simple_node):
    return Pipeline([simple_node])


@pytest.fixture
def pipeline_with_project_source(node_with_project_source):
    return Pipeline([node_with_project_source])


def _identity(x):
    return x


def _load_func_from_project(project_path: Path, source: str, func_name: str):
    """Load a function defined in a module file under ``project_path``."""
    nodes_file = project_path / "src" / "pkg" / "nodes.py"
    nodes_file.parent.mkdir(parents=True)
    nodes_file.write_text(source)

    spec = importlib.util.spec_from_file_location("nodes", nodes_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, func_name)


class TestNodeSourceSnapshot:
    def test_instantiation(self):
        source = NodeSourceSnapshot(
            filepath="src/pkg/pipelines/nodes.py",
            line_start=10,
            line_end=15,
        )
        assert source.filepath == "src/pkg/pipelines/nodes.py"
        assert source.line_start == 10
        assert source.line_end == 15


class TestNodeSnapshot:
    def test_instantiation_defaults(self):
        snapshot = NodeSnapshot(name="my_node", func_name="my_func")
        assert snapshot.name == "my_node"
        assert snapshot.func_name == "my_func"
        assert snapshot.namespace is None
        assert snapshot.tags == []
        assert snapshot.inputs == []
        assert snapshot.outputs == []
        assert snapshot.source is None

    def test_func_name_is_keyword_only(self):
        snapshot = NodeSnapshot("my_node", "my_namespace", func_name="my_func")
        assert snapshot.func_name == "my_func"
        assert snapshot.namespace == "my_namespace"

        with pytest.raises(TypeError, match="func_name"):
            NodeSnapshot("my_node", "my_namespace")


class TestResolveNodeSource:
    def test_returns_none_for_partial(self):
        assert _resolve_node_source(partial(_identity), Path("/project")) is None

    def test_returns_none_for_lambda(self):
        assert _resolve_node_source(lambda x: x, Path("/project")) is None

    def test_returns_none_for_builtin(self):
        assert _resolve_node_source(len, Path("/project")) is None

    def test_returns_none_when_getsourcelines_fails(self, mocker, project_path):
        func = _load_func_from_project(
            project_path,
            "def my_func(x):\n    return x\n",
            "my_func",
        )
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcelines",
            side_effect=OSError("no source"),
        )
        assert _resolve_node_source(func, project_path) is None

    def test_returns_none_when_source_file_cannot_be_resolved(
        self, mocker, project_path
    ):
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcefile", return_value=None
        )
        assert _resolve_node_source(_identity, project_path) is None

    def test_returns_none_when_source_is_unreadable(self, mocker, project_path):
        func = _load_func_from_project(
            project_path,
            "def my_func(x):\n    return x\n",
            "my_func",
        )
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcelines",
            side_effect=OSError("permission denied"),
        )
        assert _resolve_node_source(func, project_path) is None

    def test_filepath_is_project_relative_when_inside_project(self, project_path):
        expected_source = "def my_func(x):\n    return x\n"
        func = _load_func_from_project(project_path, expected_source, "my_func")

        source = _resolve_node_source(func, project_path)
        source_lines, line_start = inspect.getsourcelines(func)

        assert source == NodeSourceSnapshot(
            filepath="src/pkg/nodes.py",
            line_start=line_start,
            line_end=line_start + len(source_lines) - 1,
        )
        assert "".join(source_lines) == expected_source

    def test_returns_none_when_outside_project(self, project_path):
        assert _resolve_node_source(_identity, project_path) is None


class TestNodeToSnapshot:
    def test_populates_all_fields(self, simple_node, project_path):
        snapshot = _node_to_snapshot(simple_node, project_path)
        assert snapshot.name == simple_node.name
        assert snapshot.func_name == "_identity"
        assert snapshot.namespace == simple_node.namespace
        assert snapshot.inputs == simple_node.inputs
        assert snapshot.outputs == simple_node.outputs

    def test_tags_are_sorted(self, simple_node, project_path):
        snapshot = _node_to_snapshot(simple_node, project_path)
        assert snapshot.tags == sorted(simple_node.tags)

    def test_namespace_populated(self, namespaced_node, project_path):
        snapshot = _node_to_snapshot(namespaced_node, project_path)
        assert snapshot.namespace == "data_science"

    def test_returns_node_snapshot_instance(self, simple_node, project_path):
        assert isinstance(_node_to_snapshot(simple_node, project_path), NodeSnapshot)

    def test_populates_source_when_function_is_in_project(
        self, node_with_project_source, project_path
    ):
        snapshot = _node_to_snapshot(node_with_project_source, project_path)
        assert snapshot.source == NodeSourceSnapshot(
            filepath="src/pkg/nodes.py",
            line_start=1,
            line_end=2,
        )

    def test_source_is_none_for_out_of_project_function(
        self, simple_node, project_path
    ):
        snapshot = _node_to_snapshot(simple_node, project_path)
        assert snapshot.source is None

    def test_source_is_none_for_partial(self, project_path):
        partial_node = node(
            partial(_identity),
            inputs="raw",
            outputs="processed",
            name="partial_node",
        )

        with pytest.warns(UserWarning, match="made from a 'partial' function"):
            snapshot = _node_to_snapshot(partial_node, project_path)

        assert snapshot.name == "partial_node"
        assert snapshot.func_name == "<partial>"
        assert snapshot.source is None


class TestPipelineSnapshot:
    def test_instantiation(self):
        node_snap = NodeSnapshot(
            name="n", func_name="identity", inputs=["a"], outputs=["b"]
        )
        snapshot = PipelineSnapshot(name="my_pipe", nodes=[node_snap])
        assert snapshot.name == "my_pipe"
        assert snapshot.nodes == [node_snap]
        assert snapshot.inputs == []
        assert snapshot.outputs == []


class TestBuildPipelineSnapshots:
    def test_returns_correct_name(self, simple_pipeline, project_path):
        snapshots = _build_pipeline_snapshots(
            {"data_processing": simple_pipeline}, project_path
        )
        assert len(snapshots) == 1
        assert snapshots[0].name == "data_processing"

    def test_nodes_in_execution_order(self, project_path):
        n1 = node(_identity, inputs="raw", outputs="intermediate", name="n1")
        n2 = node(_identity, inputs="intermediate", outputs="final", name="n2")
        pipeline = Pipeline([n2, n1])  # intentionally reversed

        snapshots = _build_pipeline_snapshots({"__default__": pipeline}, project_path)
        node_names = [n.name for n in snapshots[0].nodes]
        assert node_names == [n.name for n in pipeline.nodes]

    def test_pipeline_inputs_and_outputs(self, simple_pipeline, project_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline}, project_path
        )
        assert snapshots[0].inputs == sorted(simple_pipeline.inputs())
        assert snapshots[0].outputs == sorted(simple_pipeline.outputs())

    def test_empty_registry_returns_empty_list(self, project_path):
        assert _build_pipeline_snapshots({}, project_path) == []

    def test_none_pipelines_are_skipped(self, simple_pipeline, project_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline, "broken": None},
            project_path,
        )
        assert len(snapshots) == 1
        assert snapshots[0].name == "__default__"

    def test_nodes_include_source_metadata(
        self, pipeline_with_project_source, project_path
    ):
        snapshots = _build_pipeline_snapshots(
            {"__default__": pipeline_with_project_source}, project_path
        )
        assert snapshots[0].nodes[0].source == NodeSourceSnapshot(
            filepath="src/pkg/nodes.py",
            line_start=1,
            line_end=2,
        )
