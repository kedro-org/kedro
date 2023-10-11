import re
from itertools import chain

import pytest

import kedro
from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.pipeline.pipeline import (
    CircularDependencyError,
    ConfirmNotUniqueError,
    OutputNotUniqueError,
    _strip_transcoding,
    _transcode_split,
)


class TestTranscodeHelpers:
    def test_split_no_transcode_part(self):
        assert _transcode_split("abc") == ("abc", "")

    def test_split_with_transcode(self):
        assert _transcode_split("abc@def") == ("abc", "def")

    def test_split_too_many_parts(self):
        with pytest.raises(ValueError):
            _transcode_split("abc@def@ghi")

    def test_get_transcode_compatible_name(self):
        assert _strip_transcoding("abc@def") == "abc"


# Different dummy func based on the number of arguments
def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


def triconcat(input1: str, input2: str, input3: str):
    return input1 + input2 + input3  # pragma: no cover


@pytest.fixture
def branchless_pipeline():
    return {
        "nodes": [
            node(identity, "E", None),
            node(identity, "D", "E"),
            node(identity, "C", "D"),
            node(identity, "A", "B"),
            node(identity, "B", "C"),
            node(constant_output, None, "A"),
        ],
        "expected": [
            {node(constant_output, None, "A")},
            {node(identity, "A", "B")},
            {node(identity, "B", "C")},
            {node(identity, "C", "D")},
            {node(identity, "D", "E")},
            {node(identity, "E", None)},
        ],
        "free_inputs": [],
        "outputs": [],
    }


@pytest.fixture
def pipeline_list_with_lists():
    return {
        "nodes": [
            node(triconcat, ["H", "I", "M"], "N", name="node1"),
            node(identity, "H", "I", name="node2"),
            node(identity, "F", ["G", "M"], name="node3"),
            node(identity, "E", ["F", "H"], name="node4"),
            node(identity, "D", None, name="node5"),
            node(identity, "C", "D", name="node6", tags=["foo"]),
            node(identity, "B", ["C", "E"], name="node7", tags=["foo"]),
            node(identity, "A", ["B", "L"], name="node8"),
            node(constant_output, None, "A", name="node9"),
        ],
        "expected": [
            {node(constant_output, None, "A", name="node9")},
            {node(identity, "A", ["B", "L"], name="node8")},
            {node(identity, "B", ["C", "E"], name="node7", tags=["foo"])},
            {
                node(identity, "C", "D", name="node6", tags=["foo"]),
                node(identity, "E", ["F", "H"], name="node4"),
            },
            {
                node(identity, "D", None, name="node5"),
                node(identity, "H", "I", name="node2"),
                node(identity, "F", ["G", "M"], name="node3"),
            },
            {node(triconcat, ["H", "I", "M"], "N", name="node1")},
        ],
        "free_inputs": [],
        "outputs": ["L", "G", "N"],
    }


@pytest.fixture
def pipeline_with_dicts():
    return {
        "nodes": [
            node(triconcat, ["H", "I", "M"], "N", name="node1"),
            node(identity, "H", "I", name="node2"),
            node(identity, "F", {"M": "M", "N": "G"}, name="node3"),
            node(identity, "E", {"O": "F", "P": "H"}, name="node4"),  # NOQA
            node(identity, {"input1": "D"}, None, name="node5"),
            node(identity, "C", "D", name="node6", tags=["foo"]),
            node(identity, "B", {"P": "C", "Q": "E"}, name="node7", tags=["foo"]),
            node(identity, "A", {"R": "B", "S": "L"}, name="node8"),
            node(constant_output, None, "A", name="node9"),
        ],
        "expected": [
            {node(constant_output, None, "A", name="node9")},
            {node(identity, "A", {"R": "B", "S": "L"}, name="node8")},
            {node(identity, "B", {"P": "C", "Q": "E"}, name="node7", tags=["foo"])},
            {
                node(identity, "C", "D", name="node6", tags=["foo"]),
                node(identity, "E", {"O": "F", "P": "H"}, name="node4"),  # NOQA
            },
            {
                node(identity, {"input1": "D"}, None, name="node5"),
                node(identity, "H", "I", name="node2"),
                node(identity, "F", {"M": "M", "N": "G"}, name="node3"),
            },
            {node(triconcat, ["H", "I", "M"], "N", name="node1")},
        ],
        "free_inputs": [],
        "outputs": ["L", "G", "N"],
    }


@pytest.fixture
def free_input_needed_pipeline():
    return {
        "nodes": [
            node(identity, "A", "B", name="node1"),  # 'A' needs to be free
            node(identity, "B", "C", name="node2"),
            node(identity, "C", "D", name="node3"),
        ],
        "expected": [
            {node(identity, "A", "B", name="node1")},
            {node(identity, "B", "C", name="node2")},
            {node(identity, "C", "D", name="node3")},
        ],
        "free_inputs": ["A"],
        "outputs": ["D"],
    }


@pytest.fixture
def disjoint_pipeline():
    # Two separate pipelines: A->B->C and D->E->F
    return {
        "nodes": [
            node(identity, "A", "B", name="node1"),
            node(identity, "B", "C", name="node2"),
            node(identity, "E", "F", name="node3"),  # disjoint part D->E->F
            node(identity, "D", "E", name="node4"),
        ],
        "expected": [
            {
                node(identity, "A", "B", name="node1"),
                node(identity, "D", "E", name="node4"),
            },
            {
                node(identity, "B", "C", name="node2"),
                node(identity, "E", "F", name="node3"),
            },
        ],
        "free_inputs": ["A", "D"],
        "outputs": ["C", "F"],
    }


@pytest.fixture
def pipeline_input_duplicated():
    return {
        "nodes": [
            node(biconcat, ["A", "A"], "B", name="node1"),  # input duplicate
            node(identity, "B", "C", name="node2"),
            node(identity, "C", "D", name="node3"),
        ],
        "expected": [
            {node(biconcat, ["A", "A"], "B", name="node1")},
            {node(identity, "B", "C", name="node2")},
            {node(identity, "C", "D", name="node3")},
        ],
        "free_inputs": ["A"],
        "outputs": ["D"],
    }


@pytest.fixture
def str_node_inputs_list():
    return {
        "nodes": [
            node(biconcat, ["input1", "input2"], ["input3"], name="node1"),
            node(identity, "input3", "input4", name="node2"),
        ],
        "expected": [
            {node(biconcat, ["input1", "input2"], ["input3"], name="node1")},
            {node(identity, "input3", "input4", name="node2")},
        ],
        "free_inputs": ["input1", "input2"],
        "outputs": ["input4"],
    }


@pytest.fixture
def complex_pipeline(pipeline_list_with_lists):
    nodes = pipeline_list_with_lists["nodes"]
    pipeline = modular_pipeline(nodes)
    return pipeline


@pytest.fixture(
    params=[
        "branchless_pipeline",
        "pipeline_list_with_lists",
        "pipeline_with_dicts",
        "free_input_needed_pipeline",
        "disjoint_pipeline",
        "pipeline_input_duplicated",
        "str_node_inputs_list",
    ]
)
def input_data(request):
    return request.getfixturevalue(request.param)


class TestValidPipeline:
    def test_nodes(self, str_node_inputs_list):
        nodes = str_node_inputs_list["nodes"]
        pipeline = modular_pipeline(nodes)

        assert set(pipeline.nodes) == set(nodes)

    def test_grouped_nodes(self, input_data):
        """Check if grouped_nodes func groups the nodes correctly"""
        nodes_input = input_data["nodes"]
        expected = input_data["expected"]
        pipeline = modular_pipeline(nodes_input)

        grouped = pipeline.grouped_nodes
        # Flatten a list of grouped nodes
        assert pipeline.nodes == list(chain.from_iterable(grouped))
        # Check each grouped node matches with the expected group, the order is
        # non-deterministic, so we are only checking they have the same set of nodes.
        assert all(set(g) == e for g, e in zip(grouped, expected))

    def test_free_input(self, input_data):
        nodes = input_data["nodes"]
        inputs = input_data["free_inputs"]

        pipeline = modular_pipeline(nodes)

        assert pipeline.inputs() == set(inputs)

    def test_outputs(self, input_data):
        nodes = input_data["nodes"]
        outputs = input_data["outputs"]

        pipeline = modular_pipeline(nodes)

        assert pipeline.outputs() == set(outputs)

    def test_empty_case(self):
        """Empty pipeline is possible"""
        modular_pipeline([])

    def test_initialized_with_tags(self):
        pipeline = modular_pipeline(
            [node(identity, "A", "B", tags=["node1", "p1"]), node(identity, "B", "C")],
            tags=["p1", "p2"],
        )

        node1 = pipeline.grouped_nodes[0].pop()
        node2 = pipeline.grouped_nodes[1].pop()
        assert node1.tags == {"node1", "p1", "p2"}
        assert node2.tags == {"p1", "p2"}

    def test_node_dependencies(self, complex_pipeline):
        expected = {
            "node1": {"node2", "node3", "node4"},
            "node2": {"node4"},
            "node3": {"node4"},
            "node4": {"node7"},
            "node5": {"node6"},
            "node6": {"node7"},
            "node7": {"node8"},
            "node8": {"node9"},
            "node9": set(),
        }
        actual = {
            child.name: {parent.name for parent in parents}
            for child, parents in complex_pipeline.node_dependencies.items()
        }
        assert actual == expected


@pytest.fixture
def pipeline_with_circle():
    return [
        node(identity, "A", "B", name="node1"),
        node(identity, "B", "C", name="node2"),
        node(identity, "C", "A", name="node3"),  # circular dependency
    ]


@pytest.fixture
def non_unique_node_outputs():
    return [
        node(identity, "A", ["B", "C"], name="node1"),
        node(identity, "C", ["D", "E", "F"], name="node2"),
        # D, E non-unique
        node(identity, "B", {"out1": "D", "out2": "E"}, name="node3"),
        node(identity, "D", ["E"], name="node4"),  # E non-unique
    ]


class TestInvalidPipeline:
    def test_circle_case(self, pipeline_with_circle):
        pattern = "Circular dependencies"
        with pytest.raises(CircularDependencyError, match=pattern):
            modular_pipeline(pipeline_with_circle)

    def test_unique_outputs(self, non_unique_node_outputs):
        with pytest.raises(OutputNotUniqueError, match=r"\['D', 'E'\]"):
            modular_pipeline(non_unique_node_outputs)

    def test_none_case(self):
        with pytest.raises(ValueError, match="is None"):
            modular_pipeline(None)

    def test_duplicate_free_nodes(self):
        pattern = (
            "Pipeline nodes must have unique names. The following node "
            "names appear more than once:\n\nFree nodes:\n  - same_name"
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            modular_pipeline(
                [
                    node(identity, "in1", "out1", name="same_name"),
                    node(identity, "in2", "out2", name="same_name"),
                ]
            )

        pipeline = modular_pipeline([node(identity, "in1", "out1", name="same_name")])
        another_node = node(identity, "in2", "out2", name="same_name")
        with pytest.raises(ValueError, match=re.escape(pattern)):
            # 'pipeline' passes the check, 'another_node' doesn't
            modular_pipeline([pipeline, another_node])

    def test_duplicate_nodes_in_pipelines(self):
        pipeline = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output", "output1"], name="node")]
        )
        pattern = (
            r"Pipeline nodes must have unique names\. The following node "
            r"names appear more than once\:\n\nPipeline\(\[.+\]\)\:\n  \- node"
        )
        with pytest.raises(ValueError, match=pattern):
            # the first 'pipeline' passes the check, the second doesn't
            modular_pipeline([pipeline, pipeline])

        another_node = node(identity, "in1", "out1", name="node")
        with pytest.raises(ValueError, match=pattern):
            # 'another_node' passes the check, 'pipeline' doesn't
            modular_pipeline([another_node, pipeline])

    def test_bad_combine_node(self):
        """Node cannot be combined to pipeline."""
        fred = node(identity, "input", "output")
        pipeline = modular_pipeline([fred])
        with pytest.raises(TypeError):
            pipeline + fred

    def test_bad_combine_int(self):
        """int cannot be combined to pipeline, tests __radd__"""
        fred = node(identity, "input", "output")
        pipeline = modular_pipeline([fred])
        with pytest.raises(TypeError):
            _ = 1 + pipeline

    def test_conflicting_names(self):
        """Node names must be unique."""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output1"], name="a")]
        )
        new_pipeline = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output2"], name="a")]
        )
        pattern = (
            "Pipeline nodes must have unique names. The following node names "
            "appear more than once:\n\nFree nodes:\n  - a"
        )
        with pytest.raises(ValueError, match=re.escape(pattern)):
            pipeline1 + new_pipeline

    def test_conflicting_outputs(self):
        """Node outputs must be unique."""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output", "output1"], name="a")]
        )
        new_pipeline = modular_pipeline(
            [node(biconcat, ["input", "input2"], ["output", "output2"], name="b")]
        )
        with pytest.raises(OutputNotUniqueError, match=r"\['output'\]"):
            pipeline1 + new_pipeline

    def test_duplicate_node_confirms(self):
        """Test that non-unique dataset confirms break pipeline concatenation"""
        pipeline1 = modular_pipeline(
            [node(identity, "input1", "output1", confirms="other")]
        )
        pipeline2 = modular_pipeline(
            [node(identity, "input2", "output2", confirms=["other", "output2"])]
        )
        with pytest.raises(ConfirmNotUniqueError, match=r"\['other'\]"):
            pipeline1 + pipeline2


class TestPipelineOperators:
    def test_combine_add(self):
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input2"], "output2", name="b")]
        )
        new_pipeline = pipeline1 + pipeline2
        assert new_pipeline.inputs() == {"input", "input1", "input2"}
        assert new_pipeline.outputs() == {"output1", "output2"}
        assert {n.name for n in new_pipeline.nodes} == {"a", "b"}

    def test_combine_sum(self):
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input2"], "output2", name="b")]
        )
        new_pipeline = sum([pipeline1, pipeline2])
        assert new_pipeline.inputs() == {"input", "input1", "input2"}
        assert new_pipeline.outputs() == {"output1", "output2"}
        assert {n.name for n in new_pipeline.nodes} == {"a", "b"}

    def test_remove(self):
        """Create a pipeline of 3 nodes and remove one of them"""
        pipeline1 = modular_pipeline(
            [
                node(biconcat, ["input", "input1"], "output1", name="a"),
                node(biconcat, ["input", "input2"], "output2", name="b"),
                node(biconcat, ["input", "input3"], "output3", name="c"),
            ]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input2"], "output2", name="b")]
        )
        new_pipeline = pipeline1 - pipeline2
        assert new_pipeline.inputs() == {"input", "input1", "input3"}
        assert new_pipeline.outputs() == {"output1", "output3"}
        assert {n.name for n in new_pipeline.nodes} == {"a", "c"}

    def test_remove_with_partial_intersection(self):
        """Create a pipeline of 3 nodes and remove one of them using a pipeline
        that contains a partial match.
        """
        pipeline1 = modular_pipeline(
            [
                node(biconcat, ["input", "input1"], "output1", name="a"),
                node(biconcat, ["input", "input2"], "output2", name="b"),
                node(biconcat, ["input", "input3"], "output3", name="c"),
            ]
        )
        pipeline2 = modular_pipeline(
            [
                node(biconcat, ["input", "input2"], "output2", name="b"),
                node(biconcat, ["input", "input4"], "output4", name="d"),
            ]
        )
        new_pipeline = pipeline1 - pipeline2
        assert new_pipeline.inputs() == {"input", "input1", "input3"}
        assert new_pipeline.outputs() == {"output1", "output3"}
        assert {n.name for n in new_pipeline.nodes} == {"a", "c"}

    def test_remove_empty_from_pipeline(self):
        """Remove an empty pipeline"""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        pipeline2 = modular_pipeline([])
        new_pipeline = pipeline1 - pipeline2
        assert new_pipeline.inputs() == pipeline1.inputs()
        assert new_pipeline.outputs() == pipeline1.outputs()
        assert {n.name for n in new_pipeline.nodes} == {"a"}

    def test_remove_from_empty_pipeline(self):
        """Remove node from an empty pipeline"""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        pipeline2 = modular_pipeline([])
        new_pipeline = pipeline2 - pipeline1
        assert new_pipeline.inputs() == pipeline2.inputs()
        assert new_pipeline.outputs() == pipeline2.outputs()
        assert not new_pipeline.nodes

    def test_remove_all_nodes(self):
        """Remove an entire pipeline"""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input1"], "output1", name="a")]
        )
        new_pipeline = pipeline1 - pipeline2
        assert new_pipeline.inputs() == set()
        assert new_pipeline.outputs() == set()
        assert not new_pipeline.nodes

    def test_invalid_remove(self):
        p = modular_pipeline([])
        pattern = r"unsupported operand type\(s\) for -: 'Pipeline' and 'str'"
        with pytest.raises(TypeError, match=pattern):
            p - "hello"

    def test_combine_same_node(self):
        """Multiple (identical) pipelines are possible"""
        pipeline1 = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output"], name="a")]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input1"], ["output"], name="a")]
        )
        new_pipeline = pipeline1 + pipeline2
        assert new_pipeline.inputs() == {"input", "input1"}
        assert new_pipeline.outputs() == {"output"}
        assert {n.name for n in new_pipeline.nodes} == {"a"}

    def test_intersection(self):
        pipeline1 = modular_pipeline(
            [
                node(biconcat, ["input", "input1"], "output1", name="a"),
                node(biconcat, ["input", "input2"], "output2", name="b"),
            ]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input2"], "output2", name="b")]
        )
        new_pipeline = pipeline1 & pipeline2
        assert new_pipeline.inputs() == {"input", "input2"}
        assert new_pipeline.outputs() == {"output2"}
        assert {n.name for n in new_pipeline.nodes} == {"b"}

    def test_invalid_intersection(self):
        p = modular_pipeline([])
        pattern = r"unsupported operand type\(s\) for &: 'Pipeline' and 'str'"
        with pytest.raises(TypeError, match=pattern):
            p & "hello"

    def test_union(self):
        pipeline1 = modular_pipeline(
            [
                node(biconcat, ["input", "input1"], "output1", name="a"),
                node(biconcat, ["input", "input2"], "output2", name="b"),
            ]
        )
        pipeline2 = modular_pipeline(
            [node(biconcat, ["input", "input2"], "output2", name="b")]
        )
        new_pipeline = pipeline1 | pipeline2
        assert new_pipeline.inputs() == {"input", "input1", "input2"}
        assert new_pipeline.outputs() == {"output1", "output2"}
        assert {n.name for n in new_pipeline.nodes} == {"a", "b"}

    def test_invalid_union(self):
        p = modular_pipeline([])
        pattern = r"unsupported operand type\(s\) for |: 'Pipeline' and 'str'"
        with pytest.raises(TypeError, match=pattern):
            p | "hello"

    def test_node_unique_confirms(self):
        """Test that unique dataset confirms don't break pipeline concatenation"""
        pipeline1 = modular_pipeline(
            [node(identity, "input1", "output1", confirms="output1")]
        )
        pipeline2 = modular_pipeline(
            [node(identity, "input2", "output2", confirms="other")]
        )
        pipeline3 = modular_pipeline([node(identity, "input3", "output3")])
        combined = pipeline1 + pipeline2 + pipeline3
        assert len(combined.nodes) == 3

    def test_connected_pipeline(self, disjoint_pipeline):
        """Connect two separate pipelines."""
        nodes = disjoint_pipeline["nodes"]
        subpipeline = modular_pipeline(nodes, tags=["subpipeline"])

        assert len(subpipeline.inputs()) == 2
        assert len(subpipeline.outputs()) == 2

        pipeline = modular_pipeline(
            [node(identity, "C", "D", name="connecting_node"), subpipeline], tags="main"
        )

        assert len(pipeline.nodes) == 1 + len(nodes)
        assert len(pipeline.inputs()) == 1
        assert len(pipeline.outputs()) == 1


class TestPipelineDescribe:
    def test_names_only(self, str_node_inputs_list):
        pipeline = modular_pipeline(str_node_inputs_list["nodes"])
        description = pipeline.describe()

        desc = description.split("\n")
        test_desc = [
            "#### Pipeline execution order ####",
            "Inputs: input1, input2",
            "",
            "node1",
            "node2",
            "",
            "Outputs: input4",
            "##################################",
        ]

        assert len(desc) == len(test_desc)
        for res, example in zip(desc, test_desc):
            assert res == example

    def test_full(self, str_node_inputs_list):
        pipeline = modular_pipeline(str_node_inputs_list["nodes"])
        description = pipeline.describe(names_only=False)

        desc = description.split("\n")
        test_desc = [
            "#### Pipeline execution order ####",
            "Inputs: input1, input2",
            "",
            "node1: biconcat([input1;input2]) -> [input3]",
            "node2: identity([input3]) -> [input4]",
            "",
            "Outputs: input4",
            "##################################",
        ]

        assert len(desc) == len(test_desc)
        for res, example in zip(desc, test_desc):
            assert res == example


@pytest.fixture
def nodes_with_tags():
    return [
        node(identity, "E", None, name="node1"),
        node(identity, "D", "E", name="node2", tags=["tag1", "tag2"]),
        node(identity, "C", "D", name="node3"),
        node(identity, "A", "B", name="node4", tags=["tag2"]),
        node(identity, "B", "C", name="node5"),
        node(constant_output, None, "A", name="node6", tags=["tag1"]),
    ]


class TestPipelineTags:
    def test_tag_existing_pipeline(self, branchless_pipeline):
        pipeline = modular_pipeline(branchless_pipeline["nodes"])
        pipeline = pipeline.tag(["new_tag"])
        assert all("new_tag" in n.tags for n in pipeline.nodes)

    def test_pipeline_single_tag(self, branchless_pipeline):
        p1 = modular_pipeline(branchless_pipeline["nodes"], tags="single_tag")
        p2 = modular_pipeline(branchless_pipeline["nodes"]).tag("single_tag")

        for pipeline in (p1, p2):
            assert all("single_tag" in n.tags for n in pipeline.nodes)


@pytest.fixture
def pipeline_with_namespaces():
    return modular_pipeline(
        [
            node(identity, "A", "B", name="node1", namespace="katie"),
            node(identity, "B", "C", name="node2", namespace="lisa"),
            node(identity, "C", "D", name="node3", namespace="john"),
            node(identity, "D", "E", name="node4", namespace="katie.lisa"),
            node(identity, "E", "F", name="node5", namespace="lisa.john"),
            node(identity, "F", "G", name="node6", namespace="katie.lisa.john"),
        ]
    )


class TestPipelineFilter:
    def test_no_filters(self, complex_pipeline):
        filtered_pipeline = complex_pipeline.filter()
        assert filtered_pipeline is not complex_pipeline
        assert set(filtered_pipeline.nodes) == set(complex_pipeline.nodes)

    @pytest.mark.parametrize(
        "filter_method,expected_nodes",
        [
            ({"tags": ["foo"]}, {"node6", "node7"}),
            ({"from_nodes": ["node4"]}, {"node1", "node2", "node3", "node4"}),
            ({"to_nodes": ["node4"]}, {"node9", "node8", "node7", "node4"}),
            ({"node_names": ["node4", "node5"]}, {"node4", "node5"}),
            ({"from_inputs": ["F"]}, {"node1", "node3"}),
            ({"to_outputs": ["F"]}, {"node4", "node7", "node8", "node9"}),
        ],
    )
    def test_one_filter(self, filter_method, expected_nodes, complex_pipeline):
        filtered_pipeline = complex_pipeline.filter(**filter_method)
        nodes = {node.name for node in filtered_pipeline.nodes}
        assert nodes == expected_nodes

    def test_namespace_filter(self, pipeline_with_namespaces):
        filtered_pipeline = pipeline_with_namespaces.filter(node_namespace="katie")
        nodes = {node.name for node in filtered_pipeline.nodes}
        assert nodes == {"katie.node1", "katie.lisa.node4", "katie.lisa.john.node6"}

    def test_two_filters(self, complex_pipeline):
        filtered_pipeline = complex_pipeline.filter(
            from_nodes=["node4"], to_outputs=["M"]
        )
        nodes = {node.name for node in filtered_pipeline.nodes}
        assert nodes == {"node3", "node4"}

    def test_three_filters(self, complex_pipeline):
        filtered_pipeline = complex_pipeline.filter(
            from_nodes=["node4"], to_outputs=["M"], node_names=["node3"]
        )
        nodes = {node.name for node in filtered_pipeline.nodes}
        assert nodes == {"node3"}

    def test_filter_no_nodes(self, complex_pipeline):
        with pytest.raises(ValueError, match="Pipeline contains no nodes"):
            complex_pipeline.filter(
                from_nodes=["node4"],
                to_outputs=["M"],
                node_names=["node3"],
                to_nodes=["node4"],
            )


class TestPipelineFilterHelpers:
    """Node selection functions called by Pipeline.filter."""

    @pytest.mark.parametrize(
        "tags,expected_nodes",
        [
            (["tag1"], ["node2", "node6"]),
            (["tag2"], ["node2", "node4"]),
            (["tag2", "tag1"], ["node2", "node4", "node6"]),
            (["tag1", "tag2", "tag-missing"], ["node2", "node4", "node6"]),
            (["tag-missing"], []),
            ([], []),
        ],
    )
    def test_only_nodes_with_tags(self, tags, expected_nodes, nodes_with_tags):
        pipeline = modular_pipeline(nodes_with_tags)

        def get_nodes_with_tags(*tags):
            p = pipeline.only_nodes_with_tags(*tags)
            return sorted(n.name for n in p.nodes)

        assert get_nodes_with_tags(*tags) == expected_nodes

    def test_from_nodes(self, complex_pipeline):
        """New pipeline contain all nodes that depend on node2 and node3."""
        new_pipeline = complex_pipeline.from_nodes("node3", "node2")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 3
        assert nodes == {"node1", "node2", "node3"}

    def test_from_nodes_unknown(self, complex_pipeline):
        pattern = r"Pipeline does not contain nodes named \['missing_node'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.from_nodes("missing_node")

    def test_to_nodes(self, complex_pipeline):
        """New pipeline contain all nodes required by node4 and node6."""
        new_pipeline = complex_pipeline.to_nodes("node4", "node6")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 5
        assert nodes == {"node4", "node6", "node7", "node8", "node9"}

    def test_to_nodes_unknown(self, complex_pipeline):
        pattern = r"Pipeline does not contain nodes named \['missing_node'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.to_nodes("missing_node")

    @pytest.mark.parametrize(
        "target_node_names", [["node2", "node3", "node4", "node8"], ["node1"]]
    )
    def test_only_nodes(self, target_node_names, pipeline_list_with_lists):
        full = modular_pipeline(pipeline_list_with_lists["nodes"])
        partial = full.only_nodes(*target_node_names)
        target_list = list(target_node_names)
        names = map(lambda node_: node_.name, partial.nodes)
        assert sorted(names) == sorted(target_list)

    @pytest.mark.parametrize(
        "target_node_names", [["node2", "node3", "node4", "NaN"], ["invalid"]]
    )
    def test_only_nodes_unknown(self, pipeline_list_with_lists, target_node_names):
        pattern = r"Pipeline does not contain nodes"
        full = modular_pipeline(pipeline_list_with_lists["nodes"])
        with pytest.raises(ValueError, match=pattern):
            full.only_nodes(*target_node_names)

    @pytest.mark.parametrize(
        "non_namespaced_node_name",
        ["node1", "node2", "node3", "node4", "node5", "node6"],
    )
    def test_only_nodes_with_namespacing(
        self, pipeline_with_namespaces, non_namespaced_node_name
    ):
        # Tests that error message will supply correct namespaces.
        # Example of expected error:
        # Pipeline does not contain nodes named ['node1']. Did you mean: ['katie.node1']?
        pattern = (
            rf"Pipeline does not contain nodes named \['{non_namespaced_node_name}'\]\. "
            rf"Did you mean: \['.*\.{non_namespaced_node_name}'\]\?"
        )
        with pytest.raises(ValueError, match=pattern):
            pipeline_with_namespaces.only_nodes(non_namespaced_node_name)

    @pytest.mark.parametrize(
        "non_namespaced_node_names",
        [("node1", "node2"), ("node3", "node4"), ("node5", "node6")],
    )
    def test_only_nodes_with_namespacing_multiple_args(
        self, pipeline_with_namespaces, non_namespaced_node_names
    ):
        # Tests that error message will contain suggestions for all provided arguments.
        # Example of expected error message:
        # "Pipeline does not contain nodes named ['node1', 'node2'].
        # Did you mean: ['katie.node1', 'lisa.node2']?"
        pattern = (
            rf"(('.*\.{non_namespaced_node_names[0]}')+.*"
            rf"('.*\.{non_namespaced_node_names[1]}')+)"
            rf"|"  # use OR operator because ordering is unspecified
            rf"(('.*\.{non_namespaced_node_names[1]}')+.*"
            rf"('.*\.{non_namespaced_node_names[0]}')+)"
        )
        with pytest.raises(ValueError, match=pattern):
            pipeline_with_namespaces.only_nodes(*non_namespaced_node_names)

    @pytest.mark.parametrize(
        "non_namespaced_node_names",
        [("node1", "invalid_node"), ("invalid_node", "node2")],
    )
    def test_only_nodes_with_namespacing_and_invalid_args(
        self, pipeline_with_namespaces, non_namespaced_node_names
    ):
        # Tests error message will still contain namespace suggestions for correct arguments.
        # regex is not specific to node names due to unspecified order
        # Example of expected error message:
        # "Pipeline does not contain nodes named ['node1', 'invalid_node'].
        # Did you mean: ['katie.node1']?"
        pattern = (
            r"Pipeline does not contain nodes named \[.*\]\. Did you mean: \[.*\]\?"
        )
        with pytest.raises(ValueError, match=pattern):
            pipeline_with_namespaces.only_nodes(*non_namespaced_node_names)

    def test_from_inputs(self, complex_pipeline):
        """F and H are inputs of node1, node2 and node3."""
        new_pipeline = complex_pipeline.from_inputs("F", "H")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 3
        assert nodes == {"node1", "node2", "node3"}

    def test_from_inputs_unknown(self, complex_pipeline):
        """W and Z do not exist as inputs."""
        with pytest.raises(ValueError, match=r"\['W', 'Z'\]"):
            complex_pipeline.from_inputs("Z", "W", "E", "C")

    def test_to_outputs(self, complex_pipeline):
        """New pipeline contain all nodes to produce F and H outputs."""
        new_pipeline = complex_pipeline.to_outputs("F", "H")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 4
        assert nodes == {"node4", "node7", "node8", "node9"}

    def test_to_outputs_unknown(self, complex_pipeline):
        with pytest.raises(ValueError, match=r"\['W', 'Z'\]"):
            complex_pipeline.to_outputs("Z", "W", "E", "C")

    @pytest.mark.parametrize(
        "target_namespace,expected_namespaces",
        [
            ("katie", ["katie.lisa.john", "katie.lisa", "katie"]),
            ("lisa", ["lisa.john", "lisa"]),
            ("john", ["john"]),
            ("katie.lisa", ["katie.lisa.john", "katie.lisa"]),
            ("katie.lisa.john", ["katie.lisa.john"]),
        ],
    )
    def test_only_nodes_with_namespace(
        self, target_namespace, expected_namespaces, pipeline_with_namespaces
    ):
        resulting_pipeline = pipeline_with_namespaces.only_nodes_with_namespace(
            target_namespace
        )
        for actual_node, expected_namespace in zip(
            sorted(resulting_pipeline.nodes), expected_namespaces
        ):
            assert actual_node.namespace == expected_namespace

    @pytest.mark.parametrize("namespace", ["katie", None])
    def test_only_nodes_with_namespace_unknown(self, namespace):
        pipeline = modular_pipeline([node(identity, "A", "B", namespace=namespace)])
        pattern = r"Pipeline does not contain nodes"
        with pytest.raises(ValueError, match=pattern):
            pipeline.only_nodes_with_namespace("non_existent")


class TestPipelineRunnerHelpers:
    """Node selection functions used in AbstractRunner."""

    def test_only_nodes_with_inputs(self, complex_pipeline):
        """node1 and node2 require H as an input."""
        new_pipeline = complex_pipeline.only_nodes_with_inputs("H")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 2
        assert nodes == {"node1", "node2"}

    def test_only_nodes_with_inputs_unknown(self, complex_pipeline):
        with pytest.raises(ValueError, match="['W', 'Z']"):
            complex_pipeline.only_nodes_with_inputs("Z", "W", "E", "C")

    def test_only_nodes_with_outputs(self, complex_pipeline):
        """node4 require F and H as outputs."""
        new_pipeline = complex_pipeline.only_nodes_with_outputs("F", "H")
        nodes = {node.name for node in new_pipeline.nodes}

        assert len(new_pipeline.nodes) == 1
        assert nodes == {"node4"}

    def test_only_nodes_with_outputs_unknown(self, complex_pipeline):
        with pytest.raises(ValueError, match="['W', 'Z']"):
            complex_pipeline.only_nodes_with_outputs("Z", "W", "E", "C")


def test_pipeline_to_json(input_data):
    nodes = input_data["nodes"]
    json_rep = modular_pipeline(nodes).to_json()
    for pipeline_node in nodes:
        assert pipeline_node.name in json_rep
        assert all(node_input in json_rep for node_input in pipeline_node.inputs)
        assert all(node_output in json_rep for node_output in pipeline_node.outputs)

    assert kedro.__version__ in json_rep
