"""Tests for NodeSnapshot, PipelineSnapshot models and their builders."""

from __future__ import annotations

import dataclasses

import pytest

from kedro.inspection.models import NodeSnapshot, PipelineSnapshot
from kedro.inspection.snapshot import _build_pipeline_snapshots, _node_to_snapshot
from kedro.pipeline import Pipeline, node


def _identity(x):
    return x


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
    def test_construction_defaults(self):
        snapshot = NodeSnapshot(name="my_node")
        assert snapshot.name == "my_node"
        assert snapshot.namespace is None
        assert snapshot.tags == []
        assert snapshot.inputs == []
        assert snapshot.outputs == []

    def test_dict_serialization(self):
        snapshot = NodeSnapshot(
            name="my_node",
            namespace="ns",
            tags=["a"],
            inputs=["x"],
            outputs=["y"],
        )
        assert dataclasses.asdict(snapshot) == {
            "name": "my_node",
            "namespace": "ns",
            "tags": ["a"],
            "inputs": ["x"],
            "outputs": ["y"],
        }


class TestNodeToSnapshot:
    def test_populates_all_fields(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.name == simple_node.name
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


class TestPipelineSnapshot:
    def test_construction(self):
        node_snap = NodeSnapshot(name="n", inputs=["a"], outputs=["b"])
        snapshot = PipelineSnapshot(name="my_pipe", nodes=[node_snap])
        assert snapshot.name == "my_pipe"
        assert snapshot.nodes == [node_snap]
        assert snapshot.inputs == []
        assert snapshot.outputs == []

    def test_dict_serialization(self):
        node_snap = NodeSnapshot(name="n", inputs=["a"], outputs=["b"])
        snapshot = PipelineSnapshot(
            name="pipe", nodes=[node_snap], inputs=["a"], outputs=["b"]
        )
        result = dataclasses.asdict(snapshot)
        assert result["name"] == "pipe"
        assert result["nodes"][0]["name"] == "n"


class TestBuildPipelineSnapshots:
    def test_returns_correct_name(self, mocker, simple_pipeline):
        mocker.patch(
            "kedro.inspection.snapshot.pipelines",
            {"data_processing": simple_pipeline},
        )
        snapshots = _build_pipeline_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].name == "data_processing"

    def test_nodes_in_execution_order(self, mocker):
        n1 = node(_identity, inputs="raw", outputs="intermediate", name="n1")
        n2 = node(_identity, inputs="intermediate", outputs="final", name="n2")
        pipeline = Pipeline([n2, n1])  # intentionally reversed
        mocker.patch("kedro.inspection.snapshot.pipelines", {"__default__": pipeline})

        snapshots = _build_pipeline_snapshots()
        node_names = [n.name for n in snapshots[0].nodes]
        assert node_names == [n.name for n in pipeline.nodes]

    def test_pipeline_inputs_and_outputs(self, mocker, simple_pipeline):
        mocker.patch(
            "kedro.inspection.snapshot.pipelines", {"__default__": simple_pipeline}
        )
        snapshots = _build_pipeline_snapshots()
        assert snapshots[0].inputs == sorted(simple_pipeline.inputs())
        assert snapshots[0].outputs == sorted(simple_pipeline.outputs())

    def test_empty_registry_returns_empty_list(self, mocker):
        mocker.patch("kedro.inspection.snapshot.pipelines", {})
        assert _build_pipeline_snapshots() == []

    def test_none_pipelines_are_skipped(self, mocker, simple_pipeline):
        mocker.patch(
            "kedro.inspection.snapshot.pipelines",
            {"__default__": simple_pipeline, "broken": None},
        )
        snapshots = _build_pipeline_snapshots()
        assert len(snapshots) == 1
        assert snapshots[0].name == "__default__"
