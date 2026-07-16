"""Tests for NodeSnapshot, PipelineSnapshot models and their builders."""

from __future__ import annotations

import importlib.util
import inspect
from functools import partial
from pathlib import Path

import pytest

from kedro.inspection.models import NodeSnapshot, NodeSourceSnapshot, PipelineSnapshot
from kedro.inspection.snapshot import _build_pipeline_snapshots, _node_to_snapshot
from kedro.pipeline import Pipeline, node


def _identity(x):
    return x


def _load_external_function(tmp_path):
    module_path = tmp_path / "external_nodes.py"
    module_path.write_text(
        "def external_identity(x):\n    return x\n",
        encoding="utf-8",
    )
    spec = importlib.util.spec_from_file_location(
        "external_nodes_for_inspection", module_path
    )
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.external_identity, module_path


@pytest.fixture
def project_root():
    return Path(__file__).resolve().parents[2]


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


class TestNodeSourceSnapshot:
    def test_instantiation(self):
        snapshot = NodeSourceSnapshot(
            filepath="src/my_package/pipeline.py",
            line_start=10,
            line_end=12,
        )
        assert snapshot.filepath == "src/my_package/pipeline.py"
        assert snapshot.line_start == 10
        assert snapshot.line_end == 12


class TestNodeToSnapshot:
    def test_populates_all_fields(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.name == simple_node.name
        assert snapshot.func_name == "_identity"
        assert snapshot.namespace == simple_node.namespace
        assert snapshot.inputs == simple_node.inputs
        assert snapshot.outputs == simple_node.outputs

    def test_tags_are_sorted(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.tags == sorted(simple_node.tags)

    def test_namespace_populated(self, namespaced_node):
        snapshot = _node_to_snapshot(namespaced_node)
        assert snapshot.namespace == "data_science"

    def test_returns_node_snapshot_instance(self, simple_node):
        assert isinstance(_node_to_snapshot(simple_node), NodeSnapshot)

    def test_named_partial_func_name_warns(self):
        partial_node = node(
            partial(_identity),
            inputs="raw",
            outputs="processed",
            name="partial_node",
        )

        with pytest.warns(UserWarning, match="made from a 'partial' function"):
            snapshot = _node_to_snapshot(partial_node)

        assert snapshot.name == "partial_node"
        assert snapshot.func_name == "<partial>"

    def test_source_populated_for_normal_function(self, simple_node, project_root):
        snapshot = _node_to_snapshot(simple_node, project_path=project_root)
        lines, line_start = inspect.getsourcelines(_identity)

        assert snapshot.source == NodeSourceSnapshot(
            filepath=str(Path(__file__).resolve().relative_to(project_root)),
            line_start=line_start,
            line_end=line_start + len(lines) - 1,
        )

    def test_source_populated_for_partial(self, project_root):
        partial_node = node(
            partial(_identity),
            inputs="raw",
            outputs="processed",
            name="partial_node",
        )

        with pytest.warns(UserWarning, match="made from a 'partial' function"):
            snapshot = _node_to_snapshot(partial_node, project_path=project_root)
        lines, line_start = inspect.getsourcelines(_identity)

        assert snapshot.source == NodeSourceSnapshot(
            filepath=str(Path(__file__).resolve().relative_to(project_root)),
            line_start=line_start,
            line_end=line_start + len(lines) - 1,
        )

    def test_source_is_none_for_uninspectable_callable(self):
        len_node = node(len, inputs="raw", outputs="processed", name="len_node")

        snapshot = _node_to_snapshot(len_node)

        assert snapshot.source is None

    def test_source_is_none_for_lambda(self):
        lambda_node = node(
            lambda raw: raw,
            inputs="raw",
            outputs="processed",
            name="lambda_node",
        )

        snapshot = _node_to_snapshot(lambda_node)

        assert snapshot.source is None

    def test_source_uses_absolute_filepath_outside_project(
        self, tmp_path, project_root
    ):
        external_func, module_path = _load_external_function(tmp_path)
        external_node = node(
            external_func,
            inputs="raw",
            outputs="processed",
            name="external_node",
        )

        snapshot = _node_to_snapshot(external_node, project_path=project_root)

        assert snapshot.source is not None
        assert snapshot.source.filepath == str(module_path.resolve())


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

    def test_nodes_receive_project_relative_source(self, simple_pipeline, project_root):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline}, project_path=project_root
        )

        assert snapshots[0].nodes[0].source is not None
        assert snapshots[0].nodes[0].source.filepath == str(
            Path(__file__).resolve().relative_to(project_root)
        )

    def test_empty_registry_returns_empty_list(self):
        assert _build_pipeline_snapshots({}) == []

    def test_none_pipelines_are_skipped(self, simple_pipeline):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline, "broken": None}
        )
        assert len(snapshots) == 1
        assert snapshots[0].name == "__default__"
