import pytest

from kedro.pipeline import node, pipeline
from kedro.pipeline.modular_pipeline import ModularPipelineError
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline

# Different dummy func based on the number of arguments


def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


def triconcat(input1: str, input2: str, input3: str):
    return input1 + input2 + input3  # pragma: no cover


class TestPipelineHelper:
    def test_transform_dataset_names(self):
        """
        Rename some datasets, test string, list and dict formats.
        """
        raw_pipeline = modular_pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(biconcat, ["C", "D"], ["E", "F"], name="node2"),
                node(
                    biconcat, {"input1": "H", "input2": "J"}, {"K": "L"}, name="node3"
                ),
            ]
        )

        resulting_pipeline = pipeline(
            raw_pipeline,
            inputs={"A": "A_new", "D": "D_new", "H": "H_new"},
            outputs={"B": "B_new", "E": "E_new", "L": "L_new"},
        )

        # make sure the order is correct
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "A_new"
        assert nodes[0]._outputs == "B_new"

        assert nodes[1]._inputs == ["C", "D_new"]
        assert nodes[1]._outputs == ["E_new", "F"]

        assert nodes[2]._inputs == {"input1": "H_new", "input2": "J"}
        assert nodes[2]._outputs == {"K": "L_new"}

    def test_prefix_dataset_names(self):
        """
        Simple prefixing for dataset of all formats: str, list and dict
        """
        raw_pipeline = modular_pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(biconcat, ["C", "D"], ["E", "F"], name="node2"),
                node(
                    biconcat, {"input1": "H", "input2": "J"}, {"K": "L"}, name="node3"
                ),
            ]
        )
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "PREFIX.A"
        assert nodes[0]._outputs == "PREFIX.B"

        assert nodes[1]._inputs == ["PREFIX.C", "PREFIX.D"]
        assert nodes[1]._outputs == ["PREFIX.E", "PREFIX.F"]

        assert nodes[2]._inputs == {"input1": "PREFIX.H", "input2": "PREFIX.J"}
        assert nodes[2]._outputs == {"K": "PREFIX.L"}

    def test_prefixing_and_renaming(self):
        """
        Prefixing and renaming at the same time.
        Explicitly renamed  datasets should not be prefixed anymore.
        """
        raw_pipeline = modular_pipeline([node(biconcat, ["C", "D"], ["E", "F"])])
        resulting_pipeline = pipeline(
            raw_pipeline,
            namespace="PREFIX",
            inputs={"C": "C_new"},
            outputs={"E": "E_new"},
        )
        assert resulting_pipeline.nodes[0]._inputs == ["C_new", "PREFIX.D"]
        assert resulting_pipeline.nodes[0]._outputs == ["E_new", "PREFIX.F"]

    @pytest.mark.parametrize(
        "inputs,outputs",
        [("A", "D"), (["A"], ["D"]), ({"A"}, {"D"}), ({"A": "A"}, {"D": "D"})],
    )
    def test_prefix_exclude_free_inputs(self, inputs, outputs):
        raw_pipeline = modular_pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
                node(identity, "C", "D", name="node3"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, inputs=inputs, outputs=outputs, namespace="PREFIX"
        )
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "A"
        assert nodes[0]._outputs == "PREFIX.B"

        assert nodes[1]._inputs == "PREFIX.B"
        assert nodes[1]._outputs == "PREFIX.C"

        assert nodes[2]._inputs == "PREFIX.C"
        assert nodes[2]._outputs == "D"

    def test_transform_params_prefix_and_parameters(self):
        """
        Test that transform should prefix all parameters by default.
        """
        raw_pipeline = modular_pipeline(
            [
                node(identity, "parameters", "params:B", name="node1"),
                node(biconcat, ["params:C", "D"], ["parameters", "F"], name="node2"),
                node(
                    biconcat,
                    {"input1": "params:H", "input2": "parameters"},
                    {"K": "L"},
                    name="node3",
                ),
            ]
        )
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")
        nodes = sorted(resulting_pipeline.nodes)
        assert nodes[0]._inputs == "parameters"
        assert nodes[0]._outputs == "params:PREFIX.B"

        assert nodes[1]._inputs == ["params:PREFIX.C", "PREFIX.D"]
        assert nodes[1]._outputs == ["parameters", "PREFIX.F"]

        assert nodes[2]._inputs == {"input1": "params:PREFIX.H", "input2": "parameters"}
        assert nodes[2]._outputs == {"K": "PREFIX.L"}
        assert nodes[2].name == "PREFIX.node3"

    def test_dataset_transcoding_mapping_base_name(self):
        raw_pipeline = modular_pipeline(
            [node(biconcat, ["C@pandas", "D"], ["E@spark", "F"])]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", inputs={"C": "C_new"}
        )

        assert resulting_pipeline.nodes[0]._inputs == ["C_new@pandas", "PREFIX.D"]
        assert resulting_pipeline.nodes[0]._outputs == ["PREFIX.E@spark", "PREFIX.F"]

    def test_dataset_transcoding_mapping_full_dataset(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A@pandas", "B"], "C"),
                node(biconcat, ["A@spark", "C"], "CC"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, inputs={"A@pandas": "Alpha"}, namespace="PREFIX"
        )

        assert resulting_pipeline.nodes[0]._inputs == ["Alpha", "PREFIX.B"]
        assert resulting_pipeline.nodes[0]._outputs == "PREFIX.C"

        assert resulting_pipeline.nodes[1]._inputs == ["PREFIX.A@spark", "PREFIX.C"]
        assert resulting_pipeline.nodes[1]._outputs == "PREFIX.CC"

    def test_empty_input(self):
        raw_pipeline = modular_pipeline([node(constant_output, None, ["A", "B"])])

        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", outputs={"A": "A_new"}
        )
        assert resulting_pipeline.nodes[0]._inputs is None
        assert resulting_pipeline.nodes[0]._outputs == ["A_new", "PREFIX.B"]

    def test_empty_output(self):
        raw_pipeline = modular_pipeline([node(biconcat, ["A", "B"], None)])

        resulting_pipeline = pipeline(
            raw_pipeline, namespace="PREFIX", inputs={"A": "A_new"}
        )
        assert resulting_pipeline.nodes[0]._inputs == ["A_new", "PREFIX.B"]
        assert resulting_pipeline.nodes[0]._outputs is None

    @pytest.mark.parametrize(
        "func, inputs, outputs, inputs_map, outputs_map, expected_missing",
        [
            # Testing inputs
            (identity, "A", "OUT", {"A": "A_new", "B": "C", "D": "E"}, {}, ["B", "D"]),
            (biconcat, ["A", "B"], "OUT", {"C": "D"}, None, ["C"]),
            (biconcat, {"input1": "A", "input2": "B"}, "OUT", {"C": "D"}, {}, ["C"]),
            # Testing outputs
            (identity, "IN", "A", {}, {"A": "A_new", "B": "C", "D": "E"}, ["B", "D"]),
            (identity, "IN", ["A", "B"], None, {"C": "D"}, ["C"]),
            (identity, "IN", {"input1": "A", "input2": "B"}, None, {"C": "D"}, ["C"]),
            # Mix of both
            (identity, "A", "B", {"A": "A_new"}, {"B": "B_new", "C": "D"}, ["C"]),
            (identity, ["A"], ["B"], {"A": "A_new"}, {"B": "B_new", "C": "D"}, ["C"]),
            (
                identity,
                {"input1": "A"},
                {"out1": "B"},
                {"A": "A_new", "C": "D"},
                {"B": "B_new", "C": "D"},
                ["C"],
            ),
        ],
    )
    def test_missing_dataset_name_no_suggestion(
        self, func, inputs, outputs, inputs_map, outputs_map, expected_missing
    ):
        raw_pipeline = modular_pipeline([node(func, inputs, outputs)])

        with pytest.raises(
            ModularPipelineError, match=r"Failed to map datasets and/or parameters"
        ) as e:
            pipeline(
                raw_pipeline, namespace="PREFIX", inputs=inputs_map, outputs=outputs_map
            )
        assert ", ".join(expected_missing) in str(e.value)
        assert " - did you mean one of these instead: " not in str(e.value)

    @pytest.mark.parametrize(
        "func, inputs, outputs, inputs_map, outputs_map, expected_missing, expected_suggestion",
        [
            # Testing inputs
            (identity, "IN", "OUT", {"I": "in"}, {}, ["I"], ["IN"]),
            (
                biconcat,
                ["IN1", "IN2"],
                "OUT",
                {"IN": "input"},
                {},
                ["IN"],
                ["IN2", "IN1"],
            ),
            # Testing outputs
            (identity, "IN", "OUT", {}, {"OUT_": "output"}, ["OUT_"], ["OUT"]),
            (
                identity,
                "IN",
                ["OUT1", "OUT2"],
                {},
                {"OUT": "out"},
                ["OUT"],
                ["OUT2", "OUT1"],
            ),
        ],
    )
    def test_missing_dataset_with_suggestion(
        self,
        func,
        inputs,
        outputs,
        inputs_map,
        outputs_map,
        expected_missing,
        expected_suggestion,
    ):
        raw_pipeline = modular_pipeline([node(func, inputs, outputs)])

        with pytest.raises(
            ModularPipelineError, match=r"Failed to map datasets and/or parameters"
        ) as e:
            pipeline(
                raw_pipeline, namespace="PREFIX", inputs=inputs_map, outputs=outputs_map
            )
        assert ", ".join(expected_missing) in str(e.value)
        assert ", ".join(expected_suggestion) in str(e.value)

    def test_node_properties_preserved(self):
        """
        Check that we don't loose any valuable properties on node cloning.
        Also an explicitly defined name should get prefixed.
        """
        raw_pipeline = modular_pipeline(
            [node(identity, "A", "B", name="node1", tags=["tag1"])]
        )
        resulting_pipeline = pipeline(raw_pipeline, namespace="PREFIX")

        assert resulting_pipeline.nodes[0].name == "PREFIX.node1"
        assert resulting_pipeline.nodes[0].tags == {"tag1"}

    def test_default_node_name_is_namespaced(self):
        """Check that auto-generated node names are also namespaced"""
        raw_pipeline = modular_pipeline([node(identity, "A", "B")])
        first_layer_nested_pipe = pipeline(raw_pipeline, namespace="PREFIX")
        resulting_node = first_layer_nested_pipe.nodes[0]

        assert resulting_node.name.startswith("PREFIX.")
        assert resulting_node.namespace == "PREFIX"

        second_layer_nested_pipe = pipeline(first_layer_nested_pipe, namespace="PRE")
        resulting_node = second_layer_nested_pipe.nodes[0]

        assert resulting_node.name.startswith("PRE.")
        assert resulting_node.namespace == "PRE.PREFIX"

    def test_expose_intermediate_output(self):
        """Check that we don't namespace an intermediary dataset, anywhere it
        is used - either input or output"""
        raw_pipeline = modular_pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
                node(identity, "C", "D", name="node3"),
                node(biconcat, ["D", "params:x"], "X", name="node4"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, outputs={"B": "B_new"}, namespace="ACTUAL"
        )
        actual_nodes = resulting_pipeline.nodes

        assert actual_nodes[0]._outputs == "B_new"
        assert actual_nodes[1]._inputs == "B_new"

        assert actual_nodes[0]._inputs == "ACTUAL.A"
        assert actual_nodes[1]._outputs == "ACTUAL.C"
        assert actual_nodes[2]._inputs == "ACTUAL.C"
        assert actual_nodes[2]._outputs == "ACTUAL.D"

        assert actual_nodes[3]._inputs == ["ACTUAL.D", "params:ACTUAL.x"]
        assert actual_nodes[3]._outputs == "ACTUAL.X"

    def test_parameters_left_intact_when_defined_as_str(self):
        raw_pipeline = modular_pipeline(
            [node(biconcat, ["A", "params:x"], "AA", name="node1")]
        )
        resulting_pipeline = pipeline(
            raw_pipeline, outputs={"AA": "B"}, parameters="x", namespace="PREFIX"
        )
        actual_nodes = resulting_pipeline.nodes

        assert actual_nodes[0]._inputs == ["PREFIX.A", "params:x"]
        assert actual_nodes[0]._outputs == "B"

    @pytest.mark.parametrize(
        "parameters", ["params:x", {"params:x"}, {"params:x": "params:x"}]
    )
    def test_parameters_left_intact_when_defined_as_(self, parameters):
        raw_pipeline = modular_pipeline(
            [node(triconcat, ["A", "params:x", "params:y"], "AA", name="node1")]
        )
        resulting_pipeline = pipeline(
            raw_pipeline,
            outputs={"AA": "B"},
            parameters=parameters,
            namespace="PREFIX",
        )
        actual_nodes = resulting_pipeline.nodes

        # x is left intact because it's defined in parameters but y is namespaced
        assert actual_nodes[0]._inputs == ["PREFIX.A", "params:x", "params:PREFIX.y"]
        assert actual_nodes[0]._outputs == "B"

    def test_parameters_updated_with_dict(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A", "params:x"], "AA", name="node1"),
                node(biconcat, ["AA", "params:y"], "B", name="node2"),
                node(biconcat, ["B", "params:x"], "BB", name="node3"),
            ]
        )
        resulting_pipeline = pipeline(
            raw_pipeline,
            outputs={"B": "B_new"},
            parameters={"x": "X"},
            namespace="ACTUAL",
        )
        actual_nodes = resulting_pipeline.nodes

        assert actual_nodes[0]._inputs == ["ACTUAL.A", "params:X"]
        assert actual_nodes[0]._outputs == "ACTUAL.AA"

        assert actual_nodes[1]._inputs == ["ACTUAL.AA", "params:ACTUAL.y"]
        assert actual_nodes[1]._outputs == "B_new"

        assert actual_nodes[2]._inputs == ["B_new", "params:X"]
        assert actual_nodes[2]._outputs == "ACTUAL.BB"

    def test_parameters_defined_with_params_prefix(self):
        raw_pipeline = modular_pipeline(
            [node(triconcat, ["A", "params:x", "params:y"], "AA", name="node1")]
        )
        resulting_pipeline = pipeline(
            raw_pipeline,
            outputs={"AA": "B"},
            parameters={"params:x"},
            namespace="PREFIX",
        )
        actual_nodes = resulting_pipeline.nodes

        # x is left intact because it's defined in parameters but y is namespaced
        assert actual_nodes[0]._inputs == ["PREFIX.A", "params:x", "params:PREFIX.y"]
        assert actual_nodes[0]._outputs == "B"

    def test_parameters_specified_under_inputs(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "parameters"], "BB", name="node2"),
            ]
        )

        pattern = r"Parameters should be specified in the 'parameters' argument"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, inputs={"params:alpha": "params:beta"})

        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, inputs={"parameters": "some_yaml_dataset"})

    def test_non_existent_parameters_mapped(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "CC"], "BB", name="node2"),
            ]
        )

        pattern = r"Failed to map datasets and/or parameters onto the nodes provided: params:beta"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, parameters={"beta": "gamma"})

        pattern = r"Failed to map datasets and/or parameters onto the nodes provided: parameters"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, parameters={"parameters": "some_yaml_dataset"})

    def test_bad_inputs_mapping(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "parameters"], "BB", name="node2"),
            ]
        )

        pattern = "Inputs must not be outputs from another node in the same pipeline"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, inputs={"AA": "CC"})

    def test_bad_outputs_mapping(self):
        raw_pipeline = modular_pipeline(
            [
                node(biconcat, ["A", "params:alpha"], "AA", name="node1"),
                node(biconcat, ["AA", "parameters"], "BB", name="node2"),
            ]
        )

        pattern = "All outputs must be generated by some node within the pipeline"
        with pytest.raises(ModularPipelineError, match=pattern):
            pipeline(raw_pipeline, outputs={"A": "C"})

    def test_pipeline_always_copies(self):
        original_pipeline = pipeline([node(constant_output, None, "A")])
        new_pipeline = pipeline(original_pipeline)
        assert new_pipeline.nodes == original_pipeline.nodes
        assert new_pipeline is not original_pipeline

    def test_pipeline_tags(self):
        tagged_pipeline = pipeline(
            [node(constant_output, None, "A"), node(constant_output, None, "B")],
            tags="tag",
        )

        assert all(n.tags == {"tag"} for n in tagged_pipeline.nodes)
