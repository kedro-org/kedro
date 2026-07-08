"""Tests for NodeSnapshot, PipelineSnapshot models and their builders."""

from __future__ import annotations

import functools
from pathlib import Path

import pytest

from kedro.inspection.models import NodeSnapshot, NodeSourceSnapshot, PipelineSnapshot
from kedro.inspection.snapshot import (
    _build_pipeline_snapshots,
    _extract_node_source,
    _node_to_snapshot,
)
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
    def test_instantiation_defaults(self):
        snapshot = NodeSnapshot(name="my_node")
        assert snapshot.name == "my_node"
        assert snapshot.namespace is None
        assert snapshot.tags == []
        assert snapshot.inputs == []
        assert snapshot.outputs == []


class TestNodeToSnapshot:
    def test_populates_all_fields(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.name == simple_node.name
        assert snapshot.namespace == simple_node.namespace
        assert snapshot.inputs == simple_node.inputs
        assert snapshot.outputs == simple_node.outputs

    def test_func_name_always_populated(self, simple_node):
        snapshot = _node_to_snapshot(simple_node)
        assert snapshot.func_name == "_identity"

    def test_func_name_populated_regardless_of_include_source(self, simple_node, tmp_path):
        for mode in (False, "refs", "full"):
            snap = _node_to_snapshot(simple_node, project_path=tmp_path, include_source=mode)
            assert snap.func_name == "_identity"

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


# ---------------------------------------------------------------------------
# Source extraction tests
# ---------------------------------------------------------------------------


def _decorated_func(x):
    return x


def _make_partial_node(tmp_path):
    from functools import partial

    p = partial(_identity, 1)
    return node(p, inputs=None, outputs="out", name="partial_node")


class TestExtractNodeSource:
    def test_refs_populates_location_fields(self, simple_node, tmp_path):
        src = _extract_node_source(simple_node, tmp_path, "refs")
        assert isinstance(src, NodeSourceSnapshot)
        assert src.func_name == "_identity"
        # _identity is defined in this test file, which lives outside tmp_path
        assert src.filepath is not None
        assert src.filepath.endswith("test_node_pipeline_snapshot.py")
        assert isinstance(src.line_start, int)
        assert isinstance(src.line_end, int)
        assert src.line_end >= src.line_start
        assert src.code is None  # "refs" must NOT populate code

    def test_full_populates_source_code(self, simple_node, tmp_path):
        src = _extract_node_source(simple_node, tmp_path, "full")
        assert src.code is not None
        assert "def _identity" in src.code

    def test_filepath_is_relative_when_inside_project(self, tmp_path):
        """When the function file lives under project_path the path is relative."""
        import importlib
        import sys
        import textwrap

        source = textwrap.dedent(
            """\
            def my_func(x):
                return x
            """
        )
        mod_file = tmp_path / "my_module.py"
        mod_file.write_text(source)

        spec = importlib.util.spec_from_file_location("my_module", mod_file)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        sys.modules["my_module"] = mod

        try:
            n = node(mod.my_func, inputs="x", outputs="y", name="my_node")
            src = _extract_node_source(n, tmp_path, "refs")
            assert src.filepath == "my_module.py"
        finally:
            del sys.modules["my_module"]

    def test_filepath_is_absolute_when_outside_project(self, simple_node, tmp_path):
        """When the function file is outside project_path the path stays absolute."""
        unrelated_path = tmp_path / "other_project"
        unrelated_path.mkdir()
        src = _extract_node_source(simple_node, unrelated_path, "refs")
        assert src.filepath is not None
        assert Path(src.filepath).is_absolute()

    def test_partial_unwrapped_to_underlying_func(self, tmp_path):
        from functools import partial

        p = partial(_identity, 1)
        n = node(p, inputs=None, outputs="out", name="partial_node")
        src = _extract_node_source(n, tmp_path, "refs")
        # func_name comes from node._func_name (may be "<partial>")
        assert src.func_name is not None
        # Source should still be found for the unwrapped _identity
        assert src.line_start is not None

    def test_builtin_returns_none_fields(self, tmp_path):
        """Built-in functions like ``len`` cannot be source-inspected."""
        n = node(len, inputs="x", outputs="y", name="len_node")
        src = _extract_node_source(n, tmp_path, "full")
        assert src.filepath is None
        assert src.line_start is None
        assert src.line_end is None
        assert src.code is None


class TestNodeToSnapshotWithSource:
    def test_include_source_false_does_not_populate_source(self, simple_node, tmp_path):
        snap = _node_to_snapshot(simple_node, project_path=tmp_path, include_source=False)
        assert snap.func_name == "_identity"  # always present
        assert snap.source is None             # source block absent

    def test_include_source_refs_populates_location_not_code(self, simple_node, tmp_path):
        snap = _node_to_snapshot(simple_node, project_path=tmp_path, include_source="refs")
        assert snap.source is not None
        assert snap.source.func_name == "_identity"
        assert snap.source.filepath is not None
        assert snap.source.line_start is not None
        assert snap.source.line_end is not None
        assert snap.source.code is None

    def test_include_source_full_populates_all_fields(self, simple_node, tmp_path):
        snap = _node_to_snapshot(simple_node, project_path=tmp_path, include_source="full")
        assert snap.source is not None
        assert snap.source.func_name == "_identity"
        assert snap.source.code is not None
        assert "def _identity" in snap.source.code

    def test_no_project_path_skips_source_even_when_requested(self, simple_node):
        """If project_path is None, source extraction is skipped silently."""
        snap = _node_to_snapshot(simple_node, project_path=None, include_source="full")
        assert snap.source is None

    def test_structural_fields_still_populated(self, simple_node, tmp_path):
        snap = _node_to_snapshot(simple_node, project_path=tmp_path, include_source="refs")
        assert snap.name == simple_node.name
        assert snap.inputs == simple_node.inputs
        assert snap.outputs == simple_node.outputs
        assert snap.tags == sorted(simple_node.tags)


class TestBuildPipelineSnapshotsWithSource:
    def test_include_source_refs_propagated_to_nodes(self, simple_pipeline, tmp_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline},
            project_path=tmp_path,
            include_source="refs",
        )
        for n in snapshots[0].nodes:
            assert n.source is not None
            assert n.source.func_name is not None
            assert n.source.filepath is not None
            assert n.source.code is None

    def test_include_source_full_propagated_to_nodes(self, simple_pipeline, tmp_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": simple_pipeline},
            project_path=tmp_path,
            include_source="full",
        )
        for n in snapshots[0].nodes:
            assert n.source is not None
            assert n.source.code is not None
