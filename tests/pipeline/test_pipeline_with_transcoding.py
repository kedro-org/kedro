# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.
from itertools import chain

import pytest

import kedro
from kedro.pipeline import Pipeline, node
from kedro.pipeline.pipeline import OutputNotUniqueError, _get_transcode_compatible_name


# Different dummy func based on the number of arguments
def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


def triconcat(input1: str, input2: str, input3: str):
    return input1 + input2 + input3  # pragma: no cover


def _get_node_names(pipeline):
    return {n.name for n in pipeline.nodes}


@pytest.fixture
def pipeline_with_transcoded_names():
    return {
        "nodes": [
            node(identity, "A", "B@pandas", name="node1"),
            node(identity, "B@pandas", "C", name="node2"),
            node(identity, "B@spark", "D", name="node3"),
        ],
        "expected": [
            {node(identity, "A", "B@pandas", name="node1")},  # no dependency
            {
                node(identity, "B@pandas", "C", name="node2"),  # one dependency
                node(identity, "B@spark", "D", name="node3"),
            },
        ],
        "free_inputs": ["A"],
        "outputs": ["C", "D"],
    }


@pytest.fixture
def pipeline_with_transcoded_free_input():
    return {
        "nodes": [
            node(identity, "B@pandas", "C", name="node1"),
            node(identity, "C", "D", name="node2"),
        ],
        "expected": [
            {node(identity, "B@pandas", "C", name="node1")},
            {node(identity, "C", "D", name="node2")},
        ],
        "free_inputs": ["B@pandas"],
        "outputs": ["D"],
    }


@pytest.fixture
def pipeline_with_duplicate_transcoded_inputs():
    return {
        "nodes": [
            node(identity, "A", "B@pandas", name="node1"),
            node(biconcat, ["B@spark", "B@pandas"], "C", name="node2"),
        ],
        "expected": [
            {node(identity, "A", "B@pandas", name="node1")},
            {node(biconcat, ["B@spark", "B@pandas"], "C", name="node2")},
        ],
        "free_inputs": ["A"],
        "outputs": ["C"],
    }


@pytest.fixture
def complex_pipeline():
    pipeline = Pipeline(
        [
            node(triconcat, ["H@node1", "I", "M"], "N", name="node1"),
            node(identity, "H@node2", "I", name="node2"),
            node(identity, "F", ["G", "M"], name="node3"),
            node(identity, "E", ["F", "H@node4"], name="node4"),
            node(identity, "D", None, name="node5"),
            node(identity, "C", "D", name="node6"),
            node(identity, "B@node7", ["C", "E"], name="node7"),
            node(identity, "A", ["B@node8", "L"], name="node8"),
            node(constant_output, None, "A", name="node9"),
            node(identity, "B@node10", None, name="node10"),
        ]
    )
    return pipeline


@pytest.fixture(
    params=[
        "pipeline_with_transcoded_names",
        "pipeline_with_transcoded_free_input",
        "pipeline_with_duplicate_transcoded_inputs",
    ]
)
def input_data(request):
    return request.getfixturevalue(request.param)


class TestValidPipeline:
    def test_grouped_nodes(self, input_data):
        """Check if grouped_nodes func groups the nodes correctly"""
        nodes_input = input_data["nodes"]
        expected = input_data["expected"]
        pipeline = Pipeline(nodes_input)

        grouped = pipeline.grouped_nodes
        # Flatten a list of grouped nodes
        assert pipeline.nodes == list(chain.from_iterable(grouped))
        # Check each grouped node matches with expected group
        assert all(g == e for g, e in zip(grouped, expected))

    def test_free_input(self, input_data):
        nodes = input_data["nodes"]
        inputs = input_data["free_inputs"]

        pipeline = Pipeline(nodes)

        assert pipeline.inputs() == set(inputs)

    def test_outputs(self, input_data):
        nodes = input_data["nodes"]
        outputs = input_data["outputs"]

        pipeline = Pipeline(nodes)

        assert pipeline.outputs() == set(outputs)

    def test_pipeline_to_json(self, input_data):
        nodes = input_data["nodes"]
        json_rep = Pipeline(nodes).to_json()
        for pipeline_node in nodes:
            assert pipeline_node.name in json_rep
            assert all(node_input in json_rep for node_input in pipeline_node.inputs)
            assert all(node_output in json_rep for node_output in pipeline_node.outputs)

        assert kedro.__version__ in json_rep


class TestInvalidPipeline:
    def test_transcoded_inputs_outputs(self):
        """Nodes must not refer to a dataset without the separator if
        it is referenced later on in the catalog.
        """
        pattern = "The following datasets are used with transcoding, "
        pattern += "but were referenced without the separator: B."
        with pytest.raises(ValueError, match=pattern):
            Pipeline(
                [
                    node(identity, "A", "B", name="node1"),
                    node(identity, "B@pandas", "C", name="node2"),
                    node(identity, "B@spark", "D", name="node3"),
                    node(biconcat, ["A", "D"], "E", name="node4"),
                ]
            )

    def test_duplicates_in_transcoded_outputs(self):
        with pytest.raises(OutputNotUniqueError, match="['B']"):
            Pipeline(
                [
                    node(identity, "A", "B@pandas", name="node1"),
                    node(identity, "A", "B@spark", name="node2"),
                ]
            )


class TestComplexPipelineWithTranscoding:
    """
    Pipeline used for the underlying test cases is presented
    in the diagram below, where numbers are nodes and letters
    are datasets.

                  +---+
                  |   |
                  | 9 |
                  |   |
                  +-+-+
                    |
                  +-+-+
                  | A |
                  +-+-+
                    |
                  +-+-+
                  |   |
                  | 8 |
                  |   |
                  +-+-+
    +----+          |
    |    |  +---+   |   +---+
    | 10 +--+ B +---+---+ L |
    |    |  +-+-+       +---+
    +----+    |
            +-+-+
            |   |
            | 7 |
            |   |
            +-+-+
              |
      +---+   |   +---+
      | C +---+---+ E |
      +-+-+       +-+-+
        |           |
      +-+-+       +-+-+
      |   |       |   |
      | 6 |       | 4 |
      |   |       |   |
      +-+-+       +-+-+
        |           |
      +-+-+   +---+ | +---+
      | D |   | F +-+-+ H +-+
      +-+-+   +-+-+   +-+-+ |
        |       |       |   |
      +-+-+   +-+-+     | +-+-+
      |   |   |   |     | |   |
      | 5 |   | 3 |     | | 2 |
      |   |   |   |     | |   |
      +---+   +-+-+     | +-+-+
                |       |   |
          +---+ | +---+ | +-+-+
          | G +-+-+ M | | | I |
          +---+   +-+-+ | +-+-+
                    |   |   |
                    +-------+
                        |
                      +-+-+
                      |   |
                      | 1 |
                      |   |
                      +-+-+
                        |
                      +-+-+
                      | N |
                      +---+

    """

    def test_only_nodes_with_inputs(self, complex_pipeline):
        p = complex_pipeline.only_nodes_with_inputs("H@node2")
        assert _get_node_names(p) == {"node2"}

    def test_only_nodes_with_inputs_transcoded_name(self, complex_pipeline):
        p = complex_pipeline.only_nodes_with_inputs("H")
        assert _get_node_names(p) == {"node1", "node2"}

    def test_only_nodes_with_inputs_duplicate_transcoded_names(self, complex_pipeline):
        p1 = complex_pipeline.only_nodes_with_inputs("H", "H@node1")
        p2 = complex_pipeline.only_nodes_with_inputs("H")

        assert _get_node_names(p1) == _get_node_names(p2)

    def test_only_nodes_with_inputs_inexistent_inputs(self, complex_pipeline):
        pattern = r"Pipeline does not contain data_sets named \['Z'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.only_nodes_with_inputs("Z")

    def test_from_inputs(self, complex_pipeline):
        p = complex_pipeline.from_inputs("H@node1")
        assert _get_node_names(p) == {"node1"}

        p = complex_pipeline.from_inputs("H@node2")
        assert _get_node_names(p) == {"node1", "node2"}

    def test_from_inputs_traverses_transcoded(self, complex_pipeline):
        p = complex_pipeline.from_inputs("E")
        assert _get_node_names(p) == {"node4", "node3", "node2", "node1"}

    def test_from_inputs_traverses_transcoded_on_correct_branch(self, complex_pipeline):
        """Test that from_inputs intercepts only the correct branch at top layer (B@node7),
        but traverses transcoded nodes (H) found further down the graph."""

        p = complex_pipeline.from_inputs("B@node7", "L")
        assert _get_node_names(p) == {"node{}".format(i) for i in range(1, 8)}

    def test_from_inputs_transcode_compatible_name(self, complex_pipeline):
        p = complex_pipeline.from_inputs("H")
        assert _get_node_names(p) == {"node1", "node2"}

    def test_from_inputs_duplicate_transcoded_names(self, complex_pipeline):
        p1 = complex_pipeline.from_inputs("H", "H@node4")
        p2 = complex_pipeline.from_inputs("H")

        assert _get_node_names(p1) == _get_node_names(p2)

    def test_from_inputs_inexistent_inputs(self, complex_pipeline):
        pattern = r"Pipeline does not contain data_sets named \['Z'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.from_inputs("Z")

    def test_only_nodes_with_outputs(self, complex_pipeline):
        p1 = complex_pipeline.only_nodes_with_outputs("H@node4")
        p2 = complex_pipeline.only_nodes_with_outputs("H@node2")

        assert _get_node_names(p1) == {"node4"}
        assert _get_node_names(p2) == set()

    def test_only_nodes_with_outputs_transcode_compatible_name(self, complex_pipeline):
        p = complex_pipeline.only_nodes_with_outputs("H")
        assert _get_node_names(p) == {"node4"}

    def test_only_nodes_with_outputs_duplicate_transcoded_names(self, complex_pipeline):
        p1 = complex_pipeline.only_nodes_with_outputs("H", "H@node4")
        p2 = complex_pipeline.only_nodes_with_outputs("H")

        assert _get_node_names(p1) == _get_node_names(p2)

    def test_only_nodes_with_outputs_inexistent_outputs(self, complex_pipeline):
        pattern = r"Pipeline does not contain data_sets named \['Z'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.only_nodes_with_outputs("Z")

    def test_to_outputs(self, complex_pipeline):
        p1 = complex_pipeline.to_outputs("H@node4")
        p2 = complex_pipeline.to_outputs("H@node2")

        assert _get_node_names(p1) == {"node4", "node7", "node8", "node9"}
        assert _get_node_names(p2) == set()

    def test_to_outputs_traverses_transcoded(self, complex_pipeline):
        """Test that to_outputs traverses transcoded nodes (B) found further up the graph."""
        p = complex_pipeline.to_outputs("H@node4", "D")
        assert _get_node_names(p) == {"node4", "node6", "node7", "node8", "node9"}

    def test_to_outputs_transcoded_name(self, complex_pipeline):
        p = complex_pipeline.to_outputs("H")
        assert _get_node_names(p) == {"node4", "node7", "node8", "node9"}

    def test_to_outputs_duplicate_transcoded_names(self, complex_pipeline):
        p1 = complex_pipeline.to_outputs("H", "H@node4")
        p2 = complex_pipeline.to_outputs("H")

        assert _get_node_names(p1) == _get_node_names(p2)

    def test_to_outputs_inexistent_outputs(self, complex_pipeline):
        pattern = r"Pipeline does not contain data_sets named \['Z'\]"
        with pytest.raises(ValueError, match=pattern):
            complex_pipeline.to_outputs("Z")


class TestGetTranscodeCompatibleName:
    def test_get_transcode_compatible_name(self):
        dataset_name = "mydata@pandas"
        assert _get_transcode_compatible_name(dataset_name) == "mydata"

    def test_get_transcode_compatible_name_no_separator(self):
        dataset_name = "mydata"
        assert _get_transcode_compatible_name(dataset_name) == dataset_name

    def test_get_transcode_compatible_name_multiple_separators(self):
        dataset_name = "mydata@formA@formB"
        pattern = "Expected maximum 1 transcoding separator, "
        pattern += "found 2 instead: 'mydata@formA@formB'"

        with pytest.raises(ValueError, match=pattern):
            _get_transcode_compatible_name(dataset_name)
