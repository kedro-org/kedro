"""Tests for NodeSnapshot, GroupSnapshot, PipelineSnapshot models and their builders."""

from __future__ import annotations

import importlib.util
import inspect
from functools import partial
from pathlib import Path

import pytest

from kedro.inspection.models import (
    GroupSnapshot,
    NodeSnapshot,
    NodeSourceSnapshot,
    PipelineSnapshot,
)
from kedro.inspection.snapshot import (
    _build_group_snapshots,
    _build_pipeline_snapshots,
    _node_to_snapshot,
    _resolve_node_source,
)
from kedro.pipeline import Pipeline, node, pipeline


@pytest.fixture
def project_path(tmp_path):
    return tmp_path.resolve()


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


@pytest.fixture
def grouped_pipeline():
    """Two namespaced pipelines joined by `model_input_table`, plus one loose node."""
    data_processing = pipeline(
        [
            node(_identity, "companies", "preprocessed", name="preprocess"),
            node(_identity, "preprocessed", "model_input_table", name="create_table"),
        ],
        namespace="data_processing",
        inputs={"companies"},
        outputs={"model_input_table"},
    )
    data_science = pipeline(
        [
            node(
                _first,
                ["model_input_table", "params:model_options"],
                "regressor",
                name="train",
            ),
            node(
                _first, ["regressor", "model_input_table"], "metrics", name="evaluate"
            ),
        ],
        namespace="data_science",
        inputs={"model_input_table"},
        parameters={"params:model_options"},
    )
    report = node(_identity, "model_input_table", "report", name="make_report")
    return data_processing + data_science + Pipeline([report])


def _identity(x):
    return x


def _first(*args):
    return args[0]


def _load_func_from_project(project_path: Path, source: str, func_name: str):
    """Load a function defined in a module file under ``project_path``."""
    nodes_file = project_path / "src" / "pkg" / "nodes.py"
    nodes_file.parent.mkdir(parents=True)
    nodes_file.write_text(source)

    spec = importlib.util.spec_from_file_location("nodes", nodes_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return getattr(module, func_name)


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

    def test_returns_none_when_getsourcelines_raises_type_error(
        self, mocker, project_path
    ):
        func = _load_func_from_project(
            project_path,
            "def my_func(x):\n    return x\n",
            "my_func",
        )
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcelines",
            side_effect=TypeError("source code not available"),
        )
        assert _resolve_node_source(func, project_path) is None

    def test_returns_none_when_source_file_cannot_be_resolved(
        self, mocker, project_path
    ):
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcefile", return_value=None
        )
        assert _resolve_node_source(_identity, project_path) is None

    def test_returns_none_when_getsourcefile_raises(self, mocker, project_path):
        mocker.patch(
            "kedro.inspection.snapshot.inspect.getsourcefile",
            side_effect=OSError("no file"),
        )
        assert _resolve_node_source(_identity, project_path) is None

    def test_returns_none_for_callable_class_instance(self, project_path):
        """Callable class instances are valid Node funcs but have no resolvable source."""
        source = (
            "class Processor:\n" "    def __call__(self, x):\n" "        return x\n"
        )
        nodes_file = project_path / "src" / "pkg" / "nodes.py"
        nodes_file.parent.mkdir(parents=True)
        nodes_file.write_text(source)

        spec = importlib.util.spec_from_file_location("nodes", nodes_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        processor = module.Processor()

        assert _resolve_node_source(processor, project_path) is None

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

    def test_source_location_uses_unwrapped_function(self, project_path):
        module_source = (
            "import functools\n\n"
            "def my_func(x):\n"
            "    return x\n\n"
            "def decorator(fn):\n"
            "    @functools.wraps(fn)\n"
            "    def wrapper(*args, **kwargs):\n"
            "        return fn(*args, **kwargs)\n"
            "    return wrapper\n\n"
            "wrapped_my_func = decorator(my_func)\n"
        )
        nodes_file = project_path / "src" / "pkg" / "nodes.py"
        nodes_file.parent.mkdir(parents=True)
        nodes_file.write_text(module_source)

        spec = importlib.util.spec_from_file_location("nodes", nodes_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        wrapped_func = module.wrapped_my_func

        source = _resolve_node_source(wrapped_func, project_path)
        unwrapped_func = inspect.unwrap(wrapped_func)
        source_lines, line_start = inspect.getsourcelines(unwrapped_func)

        assert source == NodeSourceSnapshot(
            filepath="src/pkg/nodes.py",
            line_start=line_start,
            line_end=line_start + len(source_lines) - 1,
        )
        assert "def my_func" in "".join(source_lines)

    def test_returns_none_when_outside_project(self, project_path):
        """Out-of-project functions return None rather than an absolute filepath."""
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
        assert snapshot.group_by == "namespace"
        assert snapshot.groups == []


class TestGroupSnapshot:
    def test_instantiation_defaults(self):
        snapshot = GroupSnapshot(name="data_science", type="namespace")
        assert snapshot.name == "data_science"
        assert snapshot.type == "namespace"
        assert snapshot.nodes == []
        assert snapshot.dependencies == []
        assert snapshot.inputs == []
        assert snapshot.outputs == []


class TestBuildGroupSnapshots:
    def test_groups_follow_namespaces(self, grouped_pipeline):
        groups = _build_group_snapshots(grouped_pipeline)

        assert [(g.name, g.type) for g in groups] == [
            ("data_processing", "namespace"),
            ("data_science", "namespace"),
            ("make_report", "nodes"),
        ]

    def test_nodes_are_in_execution_order(self, grouped_pipeline):
        groups = {g.name: g for g in _build_group_snapshots(grouped_pipeline)}

        assert groups["data_processing"].nodes == [
            "data_processing.preprocess",
            "data_processing.create_table",
        ]
        assert groups["data_science"].nodes == [
            "data_science.train",
            "data_science.evaluate",
        ]
        assert groups["make_report"].nodes == ["make_report"]

    def test_dependencies_name_upstream_groups(self, grouped_pipeline):
        groups = {g.name: g for g in _build_group_snapshots(grouped_pipeline)}

        assert groups["data_processing"].dependencies == []
        assert groups["data_science"].dependencies == ["data_processing"]
        assert groups["make_report"].dependencies == ["data_processing"]

    def test_inputs_are_read_but_not_produced_by_the_group(self, grouped_pipeline):
        groups = {g.name: g for g in _build_group_snapshots(grouped_pipeline)}

        assert groups["data_processing"].inputs == ["companies"]
        assert groups["data_science"].inputs == [
            "model_input_table",
            "params:model_options",
        ]
        assert groups["make_report"].inputs == ["model_input_table"]

    def test_outputs_are_read_by_another_group_or_final(self, grouped_pipeline):
        groups = {g.name: g for g in _build_group_snapshots(grouped_pipeline)}

        assert groups["data_processing"].outputs == ["model_input_table"]
        assert groups["data_science"].outputs == ["data_science.metrics"]
        assert groups["make_report"].outputs == ["report"]

    def test_datasets_used_only_inside_a_group_are_not_listed(self, grouped_pipeline):
        groups = _build_group_snapshots(grouped_pipeline)

        listed = {name for g in groups for name in (*g.inputs, *g.outputs)}
        assert "data_processing.preprocessed" not in listed
        assert "data_science.regressor" not in listed

    def test_dataset_read_inside_and_outside_its_group_is_an_output(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "table", name="make", namespace="a"),
                node(_identity, "table", "summary", name="summarise", namespace="a"),
                node(_identity, "table", "scored", name="score", namespace="b"),
            ]
        )

        groups = {g.name: g for g in _build_group_snapshots(pipe)}

        assert groups["a"].outputs == ["summary", "table"]
        assert groups["b"].inputs == ["table"]

    def test_transcoded_names_keep_each_groups_spelling(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "table@spark", name="make", namespace="a"),
                node(_identity, "table@pandas", "scored", name="score", namespace="b"),
            ]
        )

        groups = {g.name: g for g in _build_group_snapshots(pipe)}

        assert groups["a"].outputs == ["table@spark"]
        assert groups["b"].inputs == ["table@pandas"]

    def test_transcoded_dataset_used_inside_one_group_is_not_listed(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "table@spark", name="make", namespace="a"),
                node(_identity, "table@pandas", "scored", name="score", namespace="a"),
            ]
        )

        (group,) = _build_group_snapshots(pipe)

        assert group.inputs == ["raw"]
        assert group.outputs == ["scored"]

    def test_nested_namespaces_group_by_top_level(self):
        pipe = Pipeline(
            [
                node(_identity, "raw", "cleaned", name="clean", namespace="a.prep"),
                node(
                    _identity, "cleaned", "features", name="build", namespace="a.feat"
                ),
            ]
        )

        (group,) = _build_group_snapshots(pipe)

        assert group.name == "a"
        assert group.nodes == ["a.prep.clean", "a.feat.build"]
        assert group.inputs == ["raw"]
        assert group.outputs == ["features"]

    def test_empty_pipeline_has_no_groups(self):
        assert _build_group_snapshots(Pipeline([])) == []

    def test_group_by_none_makes_every_node_a_group(self, grouped_pipeline):
        groups = _build_group_snapshots(grouped_pipeline, group_by=None)

        assert [g.name for g in groups] == [n.name for n in grouped_pipeline.nodes]
        assert {g.type for g in groups} == {"nodes"}
        by_name = {g.name: g for g in groups}
        assert by_name["data_science.train"].inputs == [
            "model_input_table",
            "params:model_options",
        ]
        assert by_name["data_science.train"].outputs == ["data_science.regressor"]

    def test_unsupported_group_by_raises(self, grouped_pipeline):
        with pytest.raises(ValueError, match="Unsupported group_by strategy"):
            _build_group_snapshots(grouped_pipeline, group_by="tags")


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

    def test_groups_are_populated(self, grouped_pipeline, project_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": grouped_pipeline}, project_path
        )
        assert snapshots[0].groups == _build_group_snapshots(grouped_pipeline)
        assert [g.name for g in snapshots[0].groups] == [
            "data_processing",
            "data_science",
            "make_report",
        ]

    def test_group_by_is_passed_to_group_builder(self, grouped_pipeline, project_path):
        snapshots = _build_pipeline_snapshots(
            {"__default__": grouped_pipeline}, project_path, group_by=None
        )
        assert snapshots[0].groups == _build_group_snapshots(
            grouped_pipeline, group_by=None
        )

    @pytest.mark.parametrize(
        "group_by, expected",
        [
            ("namespace", "namespace"),
            ("NAMESPACE", "namespace"),
            (None, "none"),
            ("none", "none"),
        ],
    )
    def test_group_by_is_recorded_on_the_snapshot(
        self, grouped_pipeline, project_path, group_by, expected
    ):
        snapshots = _build_pipeline_snapshots(
            {"__default__": grouped_pipeline}, project_path, group_by=group_by
        )
        assert snapshots[0].group_by == expected

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
