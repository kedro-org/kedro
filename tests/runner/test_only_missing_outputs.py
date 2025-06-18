from __future__ import annotations

import pytest

from kedro.io import (
    DataCatalog,
    LambdaDataset,
    MemoryDataset,
)
from kedro.pipeline import node, pipeline
from kedro.runner import SequentialRunner
from tests.runner.conftest import identity


class TestOnlyMissingOutputs:
    def test_only_missing_outputs_all_outputs_missing(self, mocker, caplog):
        """Test only_missing_outputs when all outputs are missing"""
        catalog = DataCatalog()

        # Create a simple test pipeline with a PERSISTENT output
        test_pipeline = pipeline([node(identity, "input", "output")])
        catalog["input"] = MemoryDataset("test_data")
        # Make output a persistent dataset that doesn't exist
        catalog["output"] = LambdaDataset(load=lambda: None, save=lambda x: None)
        catalog.exists = mocker.Mock(return_value=False)

        runner = SequentialRunner()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should call the filter method
        spy_filter.assert_called_once()
        assert "Running all 1 nodes (no outputs to skip)" in caplog.text

    def test_only_missing_outputs_some_outputs_exist(self, mocker, caplog):
        """Test only_missing_outputs when final output exists (all nodes skipped)"""
        catalog = DataCatalog()

        # Create pipeline: A -> B -> C
        test_pipeline = pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

        # Mock exists to say C exists (so all persistent outputs exist)
        def mock_exists(dataset_name):
            return dataset_name == "C"

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["A"] = MemoryDataset("data_a")
        catalog["B"] = MemoryDataset("data_b")
        # Make C a persistent dataset so it's considered in the filtering logic
        catalog["C"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should call the filter method
        spy_filter.assert_called_once()
        # Since C exists and is the only persistent final output, all nodes should be skipped
        assert "Skipping all 2 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_some_outputs_missing(self, mocker, caplog):
        """Test only_missing_outputs when final output is missing (nodes run)"""
        catalog = DataCatalog()

        # Create pipeline: A -> B -> C
        test_pipeline = pipeline(
            [
                node(identity, "A", "B", name="node1"),
                node(identity, "B", "C", name="node2"),
            ]
        )

        # Mock exists to say C doesn't exist (so persistent outputs are missing)
        def mock_exists(dataset_name):
            return False

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["A"] = MemoryDataset("data_a")
        catalog["B"] = MemoryDataset("data_b")
        # Make C a persistent dataset so it's considered in the filtering logic
        catalog["C"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should call the filter method
        spy_filter.assert_called_once()
        # Since C is missing, all nodes needed to produce C should run
        assert "Running all 2 nodes (no outputs to skip)" in caplog.text

    def test_only_missing_outputs_false_does_not_filter(self, mocker):
        """Test that only_missing_outputs=False does not filter the pipeline"""
        catalog = DataCatalog()
        test_pipeline = pipeline([node(identity, "input", "output")])
        catalog["input"] = MemoryDataset("test_data")

        runner = SequentialRunner()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")

        runner.run(test_pipeline, catalog, only_missing_outputs=False)

        # Should not call the filter method when only_missing_outputs=False
        spy_filter.assert_not_called()

    def test_only_missing_outputs_complex_topology(self, mocker, caplog):
        """Test complex pipeline topology with multiple branches and shared nodes"""
        catalog = DataCatalog()

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

        # Mock exists: only persistentA exists
        def mock_exists(dataset_name):
            return dataset_name == "persistentA"

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["input1"] = MemoryDataset("data1")
        catalog["input2"] = MemoryDataset("data2")
        for mem_ds in ["memA", "memC", "memE"]:
            catalog[mem_ds] = MemoryDataset()
        for persistent_ds in ["persistentA", "persistentC", "persistentE"]:
            catalog[persistent_ds] = LambdaDataset(
                load=lambda: None, save=lambda x: None
            )

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should skip nodeA, nodeB but run nodeC, nodeD, nodeE, nodeF
        log_text = caplog.text
        assert (
            "Skipping 2 nodes with existing persistent outputs: nodeA, nodeB"
            in log_text
        )
        assert "Running 4 out of 6 nodes (skipped 2 nodes)" in log_text

    def test_only_missing_outputs_wasteful_node_optimization(self, mocker, caplog):
        """Test that wasteful nodes are automatically excluded by pipeline.to_outputs()"""
        catalog = DataCatalog()

        # Pipeline structure:
        # input -> nodeA -> memA -> nodeB -> persistentB (exists)
        # input -> nodeC -> memC (only consumed by nodeB)
        test_pipeline = pipeline(
            [
                node(identity, "input", "memA", name="nodeA"),
                node(lambda x, y: x, ["memA", "memC"], "persistentB", name="nodeB"),
                node(identity, "input", "memC", name="nodeC"),
            ]
        )

        # Mock exists: persistentB exists
        catalog.exists = mocker.Mock(return_value=True)
        catalog["input"] = MemoryDataset("input_data")
        catalog["memA"] = MemoryDataset()
        catalog["memC"] = MemoryDataset()
        catalog["persistentB"] = LambdaDataset(
            load=lambda: "dataB", save=lambda x: None
        )

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # All nodes should be skipped including nodeC (wasteful node)
        assert "Skipping all 3 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_with_dataset_factory(self, mocker, caplog):
        """Test that dataset factory patterns are handled correctly"""
        from kedro.io.catalog_config_resolver import CatalogConfigResolver

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

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should run the node since the persistent output doesn't exist
        assert "Running all 1 nodes" in caplog.text

    def test_only_missing_outputs_catalog_contains_exception(self, mocker):
        """Test that exceptions in catalog.__contains__ are NOT caught"""

        # Create a DataCatalog subclass that raises an exception in __contains__
        class ExceptionCatalog(DataCatalog):
            def __contains__(self, dataset_name):
                if dataset_name == "output":
                    raise KeyError("Simulated catalog error")
                return super().__contains__(dataset_name)

        catalog = ExceptionCatalog()
        catalog["input"] = MemoryDataset("test_data")

        # Create a simple pipeline
        test_pipeline = pipeline([node(identity, "input", "output", name="node1")])

        runner = SequentialRunner()

        # Should raise the exception, not handle it
        with pytest.raises(KeyError, match="Simulated catalog error"):
            runner.run(test_pipeline, catalog, only_missing_outputs=True)

    def test_only_missing_outputs_diamond_dependency(self, mocker, caplog):
        """Test handling of diamond dependencies with shared upstream nodes"""
        catalog = DataCatalog()

        # Create a diamond dependency:
        # shared_node -> shared_output
        # nodeB: shared_output -> B
        # nodeC: shared_output -> C
        # nodeD: B, C -> D (missing)
        test_pipeline = pipeline(
            [
                node(lambda: "shared_data", None, "shared_output", name="shared_node"),
                node(lambda x: f"b_{x}", "shared_output", "B", name="nodeB"),
                node(lambda x: f"c_{x}", "shared_output", "C", name="nodeC"),
                node(lambda b, c: f"{b}+{c}", ["B", "C"], "D", name="nodeD"),
            ]
        )

        # Mock exists: only D doesn't exist
        def mock_exists(dataset_name):
            return dataset_name != "D"

        catalog.exists = mocker.Mock(side_effect=mock_exists)

        # Set up all datasets
        catalog["shared_output"] = MemoryDataset()
        catalog["B"] = MemoryDataset()
        catalog["C"] = MemoryDataset()
        catalog["D"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # All 4 nodes should run since D is missing
        assert "Running all 4 nodes" in caplog.text

    def test_is_persistent_and_missing_ephemeral_dataset(self, mocker):
        """Test that ephemeral datasets (MemoryDataset) are not considered persistent."""
        runner = SequentialRunner()
        catalog = DataCatalog()

        # Use public API instead of _datasets
        catalog["mem_output"] = MemoryDataset()

        assert not runner._is_persistent_and_missing("mem_output", catalog)

    def test_is_persistent_and_missing_persistent_exists(self, mocker):
        """Test that persistent datasets that exist are not considered missing."""
        runner = SequentialRunner()
        catalog = DataCatalog()

        # Use public API instead of _datasets
        catalog["persist_output"] = LambdaDataset(
            load=lambda: "data", save=lambda x: None
        )
        catalog.exists = mocker.Mock(return_value=True)

        assert not runner._is_persistent_and_missing("persist_output", catalog)

    def test_is_persistent_and_missing_persistent_not_exists(self, mocker):
        """Test that persistent datasets that don't exist are considered missing."""
        runner = SequentialRunner()
        catalog = DataCatalog()

        # Use public API instead of _datasets
        catalog["persist_output"] = LambdaDataset(
            load=lambda: None, save=lambda x: None
        )
        catalog.exists = mocker.Mock(return_value=False)

        assert runner._is_persistent_and_missing("persist_output", catalog)

    def test_is_persistent_and_missing_undefined_dataset(self, mocker):
        """Test that undefined datasets (not in catalog, no factory) are not considered persistent."""
        runner = SequentialRunner()
        catalog = DataCatalog()

        # Just test that it's not in catalog - no need to mock _datasets
        assert not runner._is_persistent_and_missing("undefined_output", catalog)

    def test_only_missing_outputs_factory_pattern_ephemeral(self, mocker, caplog):
        """Test factory pattern that creates ephemeral datasets"""
        catalog = DataCatalog()

        # Create a pipeline where output is not defined (will become MemoryDataset)
        test_pipeline = pipeline([node(identity, "input", "output_test", name="node1")])
        catalog["input"] = MemoryDataset("test_data")

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should skip everything since undefined outputs become MemoryDatasets (ephemeral)
        assert "Skipping all 1 nodes (all persistent outputs exist)" in caplog.text

    def test_only_missing_outputs_partial_persistent_outputs(self, mocker, caplog):
        """Test node with mix of persistent and ephemeral outputs"""
        catalog = DataCatalog()

        # Node produces both ephemeral and persistent outputs
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
        catalog["persistent_out"] = LambdaDataset(
            load=lambda: None, save=lambda x: None
        )

        # Mock exists for persistent dataset
        catalog.exists = mocker.Mock(return_value=False)

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should run because persistent output is missing
        assert "Running all 1 nodes" in caplog.text
