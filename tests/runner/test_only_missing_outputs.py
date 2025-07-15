from __future__ import annotations

import logging

import pytest

from kedro.io import (
    AbstractDataset,
    DataCatalog,
    MemoryDataset,
    SharedMemoryDataCatalog,
)
from kedro.pipeline import node, pipeline
from kedro.runner import ParallelRunner, SequentialRunner, ThreadRunner
from kedro.runner.runner import (
    _is_persistent_dataset_missing,
)
from tests.runner.conftest import identity


class DummyDataset(AbstractDataset):
    """A dummy dataset for tests."""

    def __init__(self, exists_result=False, initial_data=None):
        self._data = initial_data
        self._exists_result = exists_result

    def _save(self, data):
        self._data = data

    def _load(self):
        return self._data

    def _exists(self):
        return self._exists_result

    def _describe(self):
        return {}


def shared_data_func():
    return "shared_data"


def b_func(x):
    return f"b_{x}"


def c_func(x):
    return f"c_{x}"


def combine_func(b, c):
    return f"{b}+{c}"


def lambda_replacement(x, y):
    return x


def mixed_node_func(x):
    return (x, x + "_persistent")


def identity_with_default(x="default_value"):
    """Identity function that returns a default value if input is None"""
    return x if x is not None else "default_value"


def simple_logger_func(data_input):
    """A simple function for logging or side effects, for testing."""
    return None  # Explicitly return None for nodes with no dataset output


def another_logger_func(data_input):
    """Another simple function for logging or side effects."""
    return None


@pytest.fixture
def create_catalog(request):
    """Factory fixture to create appropriate catalog based on runner type"""

    def _create_catalog():
        runner_class = request.node.callspec.params.get("runner_class")
        if runner_class == ParallelRunner:
            return SharedMemoryDataCatalog()
        else:
            return DataCatalog()

    return _create_catalog


@pytest.fixture
def create_persistent_dataset(request):
    """Factory fixture to create appropriate persistent dataset based on runner type"""

    def _create_dataset(exists_result=False):
        return DummyDataset(exists_result=exists_result, initial_data="test_data")

    return _create_dataset


@pytest.mark.parametrize(
    "runner_class", [SequentialRunner, ParallelRunner, ThreadRunner]
)
class TestOnlyMissingOutputs:
    def test_only_missing_outputs_all_outputs_missing(
        self, runner_class, create_catalog, create_persistent_dataset, mocker, caplog
    ):
        """Test only_missing_outputs when all outputs are missing"""
        catalog = create_catalog()

        # Create a simple test pipeline with a PERSISTENT output
        test_pipeline = pipeline([node(identity, "input", "output")])
        catalog["input"] = MemoryDataset("test_data")
        # Make output a persistent dataset that doesn't exist
        catalog["output"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        spy_filter.assert_called_once()
        assert "Running 1 out of 1 nodes" in caplog.text

    def test_only_missing_outputs_some_outputs_exist(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test only_missing_outputs when final output exists (all nodes skipped)"""
        catalog = create_catalog()

        # Create pipeline: A -> B -> C
        test_pipeline = pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

        catalog["A"] = MemoryDataset("data_a")
        catalog["B"] = MemoryDataset("data_b")
        # Make C a persistent dataset that exists
        catalog["C"] = create_persistent_dataset(exists_result=True)

        runner = runner_class()

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Since C exists and is the only persistent final output, all nodes should be skipped
        assert "Skipping all 2 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_some_outputs_missing(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test only_missing_outputs when final output is missing (nodes run)"""
        catalog = create_catalog()

        # Create pipeline: A -> B -> C
        test_pipeline = pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

        catalog["A"] = MemoryDataset("data_a")
        catalog["B"] = MemoryDataset("data_b")  # Ephemeral intermediate
        # Make C a persistent dataset that doesn't exist
        catalog["C"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Since C is missing and B is ephemeral, all nodes needed to produce C should run
        assert "Running 2 out of 2 nodes" in caplog.text

    def test_only_missing_outputs_granular_skipping(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test granular skipping: skip upstream nodes whose persistent outputs exist"""
        catalog = create_catalog()

        # Create pipeline: A -> B -> C
        # Where B is persistent and exists, C is persistent and missing
        test_pipeline = pipeline(
            [
                node(identity_with_default, "A", "B", name="node1"),
                node(identity_with_default, "B", "C", name="node2"),
            ]
        )

        catalog["A"] = MemoryDataset("data_a")
        # Make B a persistent dataset that exists
        catalog["B"] = create_persistent_dataset(exists_result=True)
        # Make C a persistent dataset that doesn't exist
        catalog["C"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        assert "Skipping 1 nodes with existing outputs: node1" in caplog.text
        assert "Running 1 out of 2 nodes" in caplog.text

    def test_only_missing_outputs_complex_granular_skipping(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test complex pipeline with mix of existing and missing persistent outputs"""
        catalog = create_catalog()

        # Pipeline:
        # input -> nodeA -> persistentA (exists)
        # persistentA -> nodeB -> persistentB (missing)
        # input -> nodeC -> persistentC (exists)
        # persistentC -> nodeD -> persistentD (missing)
        test_pipeline = pipeline(
            [
                node(identity_with_default, "input", "persistentA", name="nodeA"),
                node(identity_with_default, "persistentA", "persistentB", name="nodeB"),
                node(identity_with_default, "input", "persistentC", name="nodeC"),
                node(identity_with_default, "persistentC", "persistentD", name="nodeD"),
            ]
        )

        catalog["input"] = MemoryDataset("data")
        catalog["persistentA"] = create_persistent_dataset(exists_result=True)
        catalog["persistentB"] = create_persistent_dataset(exists_result=False)
        catalog["persistentC"] = create_persistent_dataset(exists_result=True)
        catalog["persistentD"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should skip nodeA and nodeC (their outputs exist)
        # Should run nodeB and nodeD (their outputs are missing)
        log_text = caplog.text
        assert "Skipping 2 nodes with existing outputs: nodeA, nodeC" in log_text
        assert "Running 2 out of 4 nodes" in log_text

    def test_only_missing_outputs_false_does_not_filter(
        self, runner_class, create_catalog, mocker
    ):
        """Test that only_missing_outputs=False does not filter the pipeline"""
        catalog = create_catalog()
        test_pipeline = pipeline([node(identity, "input", "output")])
        catalog["input"] = MemoryDataset("test_data")

        runner = runner_class()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=False)

        # Should not call the filter method when only_missing_outputs=False
        spy_filter.assert_not_called()

    def test_only_missing_outputs_complex_topology(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test complex pipeline topology with multiple branches and shared nodes"""
        catalog = create_catalog()

        # Complex topology:
        # input1 -> nodeA -> memA -> nodeB -> persistentA (exists)
        # input1 -> nodeC -> memC -> nodeD -> persistentC (missing)
        # input2 -> nodeE -> memE -> nodeF -> persistentE (missing)
        test_pipeline = pipeline(
            [
                node(identity, "input1", "memA", name="nodeA"),
                node(identity, "memA", "persistentA", name="nodeB"),
                node(identity, "input1", "memC", name="nodeC"),
                node(identity, "memC", "persistentC", name="nodeD"),
                node(identity, "input2", "memE", name="nodeE"),
                node(identity, "memE", "persistentE", name="nodeF"),
            ]
        )

        catalog["input1"] = MemoryDataset("data1")
        catalog["input2"] = MemoryDataset("data2")
        for mem_ds in ["memA", "memC", "memE"]:
            catalog[mem_ds] = MemoryDataset()

        # Set up persistent datasets with different exists results
        catalog["persistentA"] = create_persistent_dataset(exists_result=True)
        catalog["persistentC"] = create_persistent_dataset(exists_result=False)
        catalog["persistentE"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should skip nodeA, nodeB but run nodeC, nodeD, nodeE, nodeF
        log_text = caplog.text
        assert "Skipping 2 nodes with existing outputs: nodeA, nodeB" in log_text
        assert "Running 4 out of 6 nodes" in log_text

    def test_only_missing_outputs_wasteful_node_optimization(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test that wasteful nodes are automatically excluded"""
        catalog = create_catalog()

        # Pipeline structure:
        # input -> nodeA -> memA -> nodeB -> persistentB (exists)
        # input -> nodeC -> memC (only consumed by nodeB)
        # Use regular function instead of lambda for ParallelRunner
        if runner_class == ParallelRunner:
            combine_node = node(
                lambda_replacement, ["memA", "memC"], "persistentB", name="nodeB"
            )
        else:
            combine_node = node(
                lambda x, y: x, ["memA", "memC"], "persistentB", name="nodeB"
            )

        test_pipeline = pipeline(
            [
                node(identity, "input", "memA", name="nodeA"),
                combine_node,
                node(identity, "input", "memC", name="nodeC"),
            ]
        )

        catalog["input"] = MemoryDataset("input_data")
        catalog["memA"] = MemoryDataset()
        catalog["memC"] = MemoryDataset()
        catalog["persistentB"] = create_persistent_dataset(exists_result=True)

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # All nodes should be skipped including nodeC
        assert "Skipping all 3 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_with_dataset_factory(
        self, runner_class, create_catalog, mocker, caplog
    ):
        """Test that dataset factory patterns are handled correctly"""
        from kedro.io.catalog_config_resolver import CatalogConfigResolver

        runner_class_param = runner_class
        if runner_class_param == ParallelRunner:
            # For ParallelRunner, we need to use SharedMemoryDataCatalog
            pytest.skip(
                "ParallelRunner doesn't support config_resolver in the same way"
            )

        # Set up a factory pattern that creates persistent datasets
        catalog_config = {
            "output_{param}": {
                "type": "pickle.PickleDataset",
                "filepath": "data/{param}.pkl",
            }
        }
        config_resolver = CatalogConfigResolver(catalog_config)
        catalog = DataCatalog(config_resolver=config_resolver)
        catalog["input"] = MemoryDataset("test_data")

        # Mock exists to return False (dataset doesn't exist)
        catalog.exists = mocker.Mock(return_value=False)

        # Create a pipeline with dataset factory pattern
        test_pipeline = pipeline(
            [
                node(identity, "input", "output_test", name="node1"),
            ]
        )

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should run the node since the persistent output doesn't exist
        assert "Running 1 out of 1 nodes" in caplog.text

    def test_only_missing_outputs_catalog_contains_exception(
        self, runner_class, create_catalog
    ):
        """Test that exceptions in catalog.__contains__ are NOT caught"""
        if runner_class == ParallelRunner:

            class ExceptionCatalog(SharedMemoryDataCatalog):
                def __contains__(self, dataset_name):
                    if dataset_name == "output":
                        raise KeyError("Simulated catalog error")
                    return super().__contains__(dataset_name)
        else:

            class ExceptionCatalog(DataCatalog):
                def __contains__(self, dataset_name):
                    if dataset_name == "output":
                        raise KeyError("Simulated catalog error")
                    return super().__contains__(dataset_name)

        catalog = ExceptionCatalog()
        catalog["input"] = MemoryDataset("test_data")

        # Create a simple pipeline
        test_pipeline = pipeline([node(identity, "input", "output", name="node1")])

        runner = runner_class()

        # Should raise the exception
        with pytest.raises(KeyError, match="Simulated catalog error"):
            runner.run(test_pipeline, catalog, only_missing_outputs=True)

    def test_only_missing_outputs_diamond_dependency(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test handling of diamond dependencies with shared upstream nodes"""
        catalog = create_catalog()

        if runner_class == ParallelRunner:
            test_pipeline = pipeline(
                [
                    node(shared_data_func, None, "shared_output", name="shared_node"),
                    node(b_func, "shared_output", "B", name="nodeB"),
                    node(c_func, "shared_output", "C", name="nodeC"),
                    node(combine_func, ["B", "C"], "D", name="nodeD"),
                ]
            )
        else:
            test_pipeline = pipeline(
                [
                    node(
                        lambda: "shared_data", None, "shared_output", name="shared_node"
                    ),
                    node(lambda x: f"b_{x}", "shared_output", "B", name="nodeB"),
                    node(lambda x: f"c_{x}", "shared_output", "C", name="nodeC"),
                    node(lambda b, c: f"{b}+{c}", ["B", "C"], "D", name="nodeD"),
                ]
            )

        # Set up all datasets
        catalog["shared_output"] = MemoryDataset()
        catalog["B"] = MemoryDataset()
        catalog["C"] = MemoryDataset()
        catalog["D"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # All 4 nodes should run since D is missing and all intermediates are ephemeral
        assert "Running 4 out of 4 nodes" in caplog.text

    def test_is_dataset_missing_ephemeral_dataset(self, runner_class, create_catalog):
        """Test that ephemeral datasets (MemoryDataset) are not considered missing."""
        catalog = create_catalog()

        # Use public API instead of _datasets
        catalog["mem_output"] = MemoryDataset()

        assert not _is_persistent_dataset_missing("mem_output", catalog)

    def test_is_dataset_missing_persistent_exists(
        self, runner_class, create_catalog, create_persistent_dataset
    ):
        """Test that persistent datasets that exist are not considered missing."""
        catalog = create_catalog()

        # Use public API instead of _datasets
        catalog["persist_output"] = create_persistent_dataset(exists_result=True)

        assert not _is_persistent_dataset_missing("persist_output", catalog)

    def test_is_dataset_missing_persistent_not_exists(
        self, runner_class, create_catalog, create_persistent_dataset
    ):
        """Test that persistent datasets that don't exist are considered missing."""
        catalog = create_catalog()

        # Use public API instead of _datasets
        catalog["persist_output"] = create_persistent_dataset(exists_result=False)

        assert _is_persistent_dataset_missing("persist_output", catalog)

    def test_is_persistent_and_missing_undefined_dataset(
        self, runner_class, create_catalog
    ):
        """Test that undefined datasets (not in catalog) are not considered missing."""
        catalog = create_catalog()

        assert not _is_persistent_dataset_missing("undefined_output", catalog)

    def test_only_missing_outputs_factory_pattern_ephemeral(
        self, runner_class, create_catalog, caplog
    ):
        """Test factory pattern that creates ephemeral datasets"""
        catalog = create_catalog()

        # Create a pipeline where output is not defined (will become MemoryDataset)
        test_pipeline = pipeline([node(identity, "input", "output_test", name="node1")])
        catalog["input"] = MemoryDataset("test_data")

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should skip everything since undefined outputs become MemoryDatasets (ephemeral)
        assert "Skipping all 1 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_partial_persistent_outputs(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test node with mix of persistent and ephemeral outputs"""
        catalog = create_catalog()

        # Node creates both ephemeral and persistent outputs
        if runner_class == ParallelRunner:
            test_pipeline = pipeline(
                [
                    node(
                        mixed_node_func,
                        "input",
                        ["ephemeral_out", "persistent_out"],
                        name="mixed_node",
                    ),
                ]
            )
        else:
            test_pipeline = pipeline(
                [
                    node(
                        lambda x: (x, x + "_persistent"),
                        "input",
                        ["ephemeral_out", "persistent_out"],
                        name="mixed_node",
                    ),
                ]
            )

        # Setup catalog
        catalog["input"] = MemoryDataset("data")
        catalog["ephemeral_out"] = MemoryDataset()
        catalog["persistent_out"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should run because persistent output is missing
        assert "Running 1 out of 1 nodes" in caplog.text

    def test_only_missing_outputs_node_with_no_outputs(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test that nodes with no outputs always run"""
        catalog = create_catalog()

        # Create a pipeline with a node that has no outputs (e.g., a logging node)
        test_pipeline = pipeline(
            [
                node(identity, "input", "intermediate", name="node1"),
                node(simple_logger_func, "intermediate", None, name="node_no_output"),
                node(identity, "intermediate", "final", name="node3"),
            ]
        )

        catalog["input"] = MemoryDataset("test_data")
        catalog["intermediate"] = create_persistent_dataset(exists_result=True)
        catalog["final"] = create_persistent_dataset(exists_result=True)

        runner = runner_class()

        logger_name = runner._logger.name
        caplog.set_level(logging.DEBUG, logger=logger_name)

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should run node_no_output even though all other outputs exist
        assert "Node 'node_no_output' must run: has no outputs" in caplog.text
        assert "Skipping 2 nodes with existing outputs: node1, node3" in caplog.text
        assert "Running 1 out of 3 nodes" in caplog.text

    def test_only_missing_outputs_ephemeral_intermediate_needed_by_child(
        self, runner_class, create_catalog, create_persistent_dataset, mocker, caplog
    ):
        """Test when an output is not in catalog but needed by a downstream node"""
        catalog = create_catalog()

        # Create a pipeline where 'ephemeral_data' is not defined in catalog
        test_pipeline = pipeline(
            [
                node(identity, "input", "ephemeral_data", name="child"),
                node(identity, "ephemeral_data", "persistent_output", name="parent"),
            ]
        )

        catalog["input"] = MemoryDataset("test_data")
        catalog["persistent_output"] = create_persistent_dataset(exists_result=False)

        runner = runner_class()

        import kedro.runner.runner

        is_ephemeral_or_missing = mocker.spy(
            kedro.runner.runner, "_is_dataset_ephemeral_or_missing"
        )

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        assert "Running 2 out of 2 nodes" in caplog.text

        # Verify the method was called for the ephemeral output
        is_ephemeral_or_missing.assert_any_call("ephemeral_data", catalog)

    def test_only_missing_outputs_complex_with_no_output_nodes(
        self, runner_class, create_catalog, create_persistent_dataset, caplog
    ):
        """Test complex pipeline with nodes that have no outputs mixed with regular nodes"""
        catalog = create_catalog()

        # Pipeline with multiple branches including nodes with no outputs
        test_pipeline = pipeline(
            [
                node(identity, "input", "data1", name="node1"),
                node(simple_logger_func, "data1", None, name="logger1"),
                node(identity, "data1", "data2", name="node2"),
                node(another_logger_func, "data2", None, name="logger2"),
                node(identity, "data2", "final_output", name="node3"),
            ]
        )

        catalog["input"] = MemoryDataset("test_data")
        catalog["data1"] = create_persistent_dataset(exists_result=True)
        catalog["data2"] = create_persistent_dataset(exists_result=True)
        catalog["final_output"] = create_persistent_dataset(exists_result=True)

        runner = runner_class()

        logger_name = runner._logger.name
        caplog.set_level(logging.DEBUG, logger=logger_name)

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Only the logger nodes should run since all persistent outputs exist
        assert "Node 'logger1' must run: has no outputs" in caplog.text
        assert "Node 'logger2' must run: has no outputs" in caplog.text
        assert (
            "Skipping 3 nodes with existing outputs: node1, node2, node3" in caplog.text
        )
        assert "Running 2 out of 5 nodes" in caplog.text
