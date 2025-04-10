import pytest

from kedro.io import (
    KedroDataCatalog,
    LambdaDataset,
)
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.runner.runner import (
    _find_all_nodes_for_resumed_pipeline,
    _find_nodes_to_resume_from,
)


@pytest.mark.parametrize(
    "pipeline_name,remaining_node_names,expected_result",
    [
        ("pipeline_asymmetric", {"node2", "node3", "node4"}, {"node1", "node2"}),
        ("pipeline_asymmetric", {"node3", "node4"}, {"node1", "node2"}),
        ("pipeline_asymmetric", {"node4"}, {"node1", "node2"}),
        ("pipeline_asymmetric", set(), set()),
        ("empty_pipeline", set(), set()),
        ("pipeline_triangular", {"node3"}, {"node1"}),
        (
            "two_branches_crossed_pipeline",
            {
                "node1_A",
                "node1_B",
                "node2",
                "node3_A",
                "node3_B",
                "node4_A",
                "node4_B",
            },
            {"node1_A", "node1_B"},
        ),
        (
            "two_branches_crossed_pipeline",
            {"node2", "node3_A", "node3_B", "node4_A", "node4_B"},
            {"node1_A", "node1_B"},
        ),
        (
            "two_branches_crossed_pipeline",
            ["node3_A", "node3_B", "node4_A", "node4_B"],
            {"node3_A", "node3_B"},
        ),
        (
            "two_branches_crossed_pipeline",
            ["node4_A", "node4_B"],
            {"node3_A", "node3_B"},
        ),
        ("two_branches_crossed_pipeline", ["node4_A"], {"node3_A"}),
        ("two_branches_crossed_pipeline", ["node3_A", "node4_A"], {"node3_A"}),
    ],
)
class TestResumeLogicBehaviour:
    def test_simple_pipeline(
        self,
        pipeline_name,
        persistent_dataset_catalog,
        remaining_node_names,
        expected_result,
        request,
    ):
        """
        Test suggestion for simple pipelines with a mix of persistent
        and memory datasets.
        """
        test_pipeline = request.getfixturevalue(pipeline_name)

        remaining_nodes = test_pipeline.only_nodes(*remaining_node_names).nodes
        result_node_names = _find_nodes_to_resume_from(
            test_pipeline, remaining_nodes, persistent_dataset_catalog
        )
        assert expected_result == result_node_names

    def test_all_datasets_persistent(
        self,
        pipeline_name,
        persistent_dataset_catalog,
        remaining_node_names,
        expected_result,
        request,
    ):
        """
        Test suggestion for pipelines where all datasets are persisted:
        In that case, exactly the set of remaining nodes should be re-run.
        """
        test_pipeline = request.getfixturevalue(pipeline_name)

        catalog = KedroDataCatalog(
            dict.fromkeys(
                test_pipeline.datasets(),
                LambdaDataset(load=lambda: 42, save=lambda data: None),
            )
        )

        remaining_nodes = set(test_pipeline.only_nodes(*remaining_node_names).nodes)
        result_node_names = _find_nodes_to_resume_from(
            test_pipeline,
            remaining_nodes,
            catalog,
        )
        final_pipeline_nodes = set(test_pipeline.from_nodes(*result_node_names).nodes)
        assert final_pipeline_nodes == remaining_nodes

    @pytest.mark.parametrize("extra_input", ["params:p", "dsY"])
    def test_added_shared_input(
        self,
        pipeline_name,
        persistent_dataset_catalog,
        remaining_node_names,
        expected_result,
        extra_input,
        request,
    ):
        """
        Test suggestion for pipelines where a single persistent dataset or
        parameter is shared across all nodes. These do not change and
        therefore should not affect resume suggestion.
        """
        test_pipeline = request.getfixturevalue(pipeline_name)

        # Add parameter shared across all nodes
        test_pipeline = modular_pipeline(
            [n._copy(inputs=[*n.inputs, extra_input]) for n in test_pipeline.nodes]
        )

        remaining_nodes = test_pipeline.only_nodes(*remaining_node_names).nodes
        result_node_names = _find_nodes_to_resume_from(
            test_pipeline, remaining_nodes, persistent_dataset_catalog
        )
        assert expected_result == result_node_names

    def test_suggestion_consistency(
        self,
        pipeline_name,
        persistent_dataset_catalog,
        remaining_node_names,
        expected_result,
        request,
    ):
        """
        Test that suggestions are internally consistent; pipeline generated
        from resume nodes should exactly contain set of all required nodes.
        """
        test_pipeline = request.getfixturevalue(pipeline_name)

        remaining_nodes = test_pipeline.only_nodes(*remaining_node_names).nodes
        required_nodes = _find_all_nodes_for_resumed_pipeline(
            test_pipeline, remaining_nodes, persistent_dataset_catalog
        )
        resume_node_names = _find_nodes_to_resume_from(
            test_pipeline, remaining_nodes, persistent_dataset_catalog
        )

        assert {n.name for n in required_nodes} == {
            n.name for n in test_pipeline.from_nodes(*resume_node_names).nodes
        }
