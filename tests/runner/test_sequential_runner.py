from __future__ import annotations

import logging
import re
from typing import Any

import pandas as pd
import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import (
    AbstractDataset,
    DataCatalog,
    DatasetError,
    LambdaDataset,
    MemoryDataset,
)
from kedro.pipeline import node, pipeline
from kedro.runner import SequentialRunner
from tests.runner.conftest import exception_fn, identity, sink, source


class TestValidSequentialRunner:
    def test_run_with_plugin_manager(self, fan_out_fan_in, catalog):
        catalog["A"] = 42
        result = SequentialRunner().run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)

    def test_run_without_plugin_manager(self, fan_out_fan_in, catalog):
        catalog["A"] = 42
        result = SequentialRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)

    def test_log_not_using_async(self, fan_out_fan_in, catalog, caplog):
        catalog["A"] = 42
        SequentialRunner().run(fan_out_fan_in, catalog)
        assert "Using synchronous mode for loading and saving data." in caplog.text

    def test_run_twice_giving_same_result(self, fan_out_fan_in, catalog):
        catalog["A"] = 42
        patterns_before_run = catalog.config_resolver.list_patterns()
        result_first_run = SequentialRunner().run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )
        # Check runtime patterns removed after run, so catalog is not mutated
        assert patterns_before_run == catalog.config_resolver.list_patterns()

        result_second_run = SequentialRunner().run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )

        assert result_first_run == result_second_run


@pytest.mark.parametrize("is_async", [False, True])
class TestSequentialRunnerBranchlessPipeline:
    def test_no_input_seq(self, is_async, branchless_no_input_pipeline, catalog):
        outputs = SequentialRunner(is_async=is_async).run(
            branchless_no_input_pipeline, catalog
        )
        assert "E" in outputs
        assert len(outputs) == 1

    def test_no_datasets(self, is_async, branchless_pipeline):
        catalog = DataCatalog({}, {"ds1": 42})
        outputs = SequentialRunner(is_async=is_async).run(branchless_pipeline, catalog)
        assert "ds3" in outputs
        assert outputs["ds3"] == 42

    def test_no_feed(self, is_async, memory_catalog, branchless_pipeline):
        outputs = SequentialRunner(is_async=is_async).run(
            branchless_pipeline, memory_catalog
        )
        assert "ds3" in outputs
        assert outputs["ds3"]["data"] == 42

    def test_node_returning_none(self, is_async, saving_none_pipeline, catalog):
        pattern = "Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            SequentialRunner(is_async=is_async).run(saving_none_pipeline, catalog)

    def test_result_saved_not_returned(self, is_async, saving_result_pipeline):
        """The pipeline runs ds->dsX but save does not save the output."""

        def _load():
            return 0

        def _save(arg):
            assert arg == 0

        catalog = DataCatalog(
            {
                "ds": LambdaDataset(load=_load, save=_save),
                "dsX": LambdaDataset(load=_load, save=_save),
            }
        )
        output = SequentialRunner(is_async=is_async).run(
            saving_result_pipeline, catalog
        )

        assert output == {}


@pytest.mark.parametrize("is_async", [False, True])
class TestSequentialRunnerBranchedPipeline:
    def test_input_seq(
        self,
        is_async,
        memory_catalog,
        unfinished_outputs_pipeline,
        pandas_df_raw_data,
    ):
        for df_name, df_value in pandas_df_raw_data.items():
            memory_catalog[df_name] = df_value
        outputs = SequentialRunner(is_async=is_async).run(
            unfinished_outputs_pipeline, memory_catalog
        )
        assert set(outputs.keys()) == {"ds8", "ds5", "ds6"}
        # the pipeline runs ds2->ds5
        assert outputs["ds5"] == [1, 2, 3, 4, 5]
        assert isinstance(outputs["ds8"], dict)
        # the pipeline runs ds1->ds4->ds8
        assert outputs["ds8"]["data"] == 42
        # the pipeline runs ds3
        assert isinstance(outputs["ds6"], pd.DataFrame)

    def test_conflict_feed_catalog(
        self,
        is_async,
        memory_catalog,
        unfinished_outputs_pipeline,
        conflicting_raw_data,
    ):
        """ds1 and ds3 will be replaced with new inputs."""

        for ds_name, ds_value in conflicting_raw_data.items():
            memory_catalog[ds_name] = ds_value

        outputs = SequentialRunner(is_async=is_async).run(
            unfinished_outputs_pipeline, memory_catalog
        )
        assert isinstance(outputs["ds8"], dict)
        assert outputs["ds8"]["data"] == 0
        assert isinstance(outputs["ds6"], pd.DataFrame)

    def test_unsatisfied_inputs(self, is_async, unfinished_outputs_pipeline, catalog):
        """ds1, ds2 and ds3 were not specified."""
        with pytest.raises(
            ValueError, match=rf"not found in the {catalog.__class__.__name__}"
        ):
            SequentialRunner(is_async=is_async).run(
                unfinished_outputs_pipeline, catalog
            )


class LoggingDataset(AbstractDataset):
    def __init__(self, log, name, value=None):
        self.log = log
        self.name = name
        self.value = value

    def _load(self) -> Any:
        self.log.append(("load", self.name))
        return self.value

    def _save(self, data: Any) -> None:
        self.value = data

    def _release(self) -> None:
        self.log.append(("release", self.name))
        self.value = None

    def _describe(self) -> dict[str, Any]:
        return {}


@pytest.mark.parametrize("is_async", [False, True])
class TestSequentialRunnerRelease:
    def test_dont_release_inputs_and_outputs(self, is_async):
        log = []
        test_pipeline = pipeline(
            [node(identity, "in", "middle"), node(identity, "middle", "out")]
        )
        catalog = DataCatalog(
            {
                "in": LoggingDataset(log, "in", "stuff"),
                "middle": LoggingDataset(log, "middle"),
                "out": LoggingDataset(log, "out"),
            }
        )
        SequentialRunner(is_async=is_async).run(test_pipeline, catalog)

        # we don't want to see release in or out in here
        assert log == [("load", "in"), ("load", "middle"), ("release", "middle")]

    def test_release_at_earliest_opportunity(self, is_async):
        log = []
        test_pipeline = pipeline(
            [
                node(source, None, "first"),
                node(identity, "first", "second"),
                node(sink, "second", None),
            ]
        )
        catalog = DataCatalog(
            {
                "first": LoggingDataset(log, "first"),
                "second": LoggingDataset(log, "second"),
            }
        )
        SequentialRunner(is_async=is_async).run(test_pipeline, catalog)

        # we want to see "release first" before "load second"
        assert log == [
            ("load", "first"),
            ("release", "first"),
            ("load", "second"),
            ("release", "second"),
        ]

    def test_count_multiple_loads(self, is_async):
        log = []
        test_pipeline = pipeline(
            [
                node(source, None, "dataset"),
                node(sink, "dataset", None, name="bob"),
                node(sink, "dataset", None, name="fred"),
            ]
        )
        catalog = DataCatalog({"dataset": LoggingDataset(log, "dataset")})
        SequentialRunner(is_async=is_async).run(test_pipeline, catalog)

        # we want to the release after both the loads
        assert log == [("load", "dataset"), ("load", "dataset"), ("release", "dataset")]

    def test_release_transcoded(self, is_async):
        log = []
        test_pipeline = pipeline(
            [node(source, None, "ds@save"), node(sink, "ds@load", None)]
        )
        catalog = DataCatalog(
            {
                "ds@save": LoggingDataset(log, "save"),
                "ds@load": LoggingDataset(log, "load"),
            }
        )

        SequentialRunner(is_async=is_async).run(test_pipeline, catalog)

        # we want to see both datasets being released
        assert log == [("release", "save"), ("load", "load"), ("release", "load")]

    @pytest.mark.parametrize(
        "test_pipeline",
        [
            pipeline([node(identity, "ds1", "ds2", confirms="ds1")]),
            pipeline(
                [
                    node(identity, "ds1", "ds2"),
                    node(identity, "ds2", None, confirms="ds1"),
                ]
            ),
        ],
    )
    def test_confirms(self, mocker, test_pipeline, is_async):
        fake_dataset_instance = mocker.Mock()
        catalog = DataCatalog(datasets={"ds1": fake_dataset_instance})
        SequentialRunner(is_async=is_async).run(test_pipeline, catalog)
        fake_dataset_instance.confirm.assert_called_once_with()


class TestOnlyMissingOutputs:
    def test_only_missing_outputs_all_outputs_missing(self, mocker, caplog):
        """Test only_missing_outputs when all outputs are missing"""
        catalog = DataCatalog()
        # Mock catalog to say all outputs are missing
        catalog.exists = mocker.Mock(return_value=False)

        # Create a simple test pipeline
        test_pipeline = pipeline([node(identity, "input", "output")])
        catalog["input"] = MemoryDataset("test_data")

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

    def test_only_missing_outputs_avoids_wasteful_nodes(self, mocker, caplog):
        """Test that nodes producing only wasteful outputs are skipped"""
        # Set caplog to capture DEBUG level logs
        caplog.set_level(logging.DEBUG)

        catalog = DataCatalog()

        # Create pipeline with wasteful branch:
        # input -> nodeA -> memA -> nodeB -> persistentA (exists)
        # input -> nodeC -> memC -> nodeD -> persistentC (missing)
        test_pipeline = pipeline(
            [
                node(identity, "input", "memA", name="nodeA"),
                node(identity, "memA", "persistentA", name="nodeB"),
                node(identity, "input", "memC", name="nodeC"),
                node(identity, "memC", "persistentC", name="nodeD"),
            ]
        )

        # Mock exists: persistentA exists, persistentC missing
        def mock_exists(dataset_name):
            return dataset_name == "persistentA"

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["input"] = MemoryDataset("input_data")
        catalog["memA"] = MemoryDataset()
        catalog["memC"] = MemoryDataset()
        catalog["persistentA"] = LambdaDataset(
            load=lambda: "dataA", save=lambda x: None
        )
        catalog["persistentC"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        spy_filter = mocker.spy(runner, "_filter_pipeline_for_missing_outputs")
        spy_wasteful = mocker.spy(runner, "_remove_wasteful_nodes")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should call both filter methods
        spy_filter.assert_called_once()
        spy_wasteful.assert_called_once()

        # Should skip nodeA and nodeB (wasteful branch) but run nodeC and nodeD
        assert (
            "Skipping 2 nodes with existing persistent outputs: nodeA, nodeB"
            in caplog.text
        )
        assert "Running 2 out of 4 nodes (skipped 2 nodes)" in caplog.text

        # Check that the debug log for removing wasteful nodes was hit
        assert (
            "Removing node 'nodeA' as it only produces outputs consumed by skipped nodes"
            in caplog.text
        )

    def test_only_missing_outputs_multi_output_node_warning(self, mocker, caplog):
        """Test warning for nodes that produce both needed and wasteful outputs"""

        def multi_output_func(x):
            return x, x  # Produces two identical outputs

        catalog = DataCatalog()

        # Create pipeline where one node produces multiple outputs:
        # input -> multiNode -> (memA, memB)
        # memA -> nodeA -> persistentA (exists)
        # memB -> nodeB -> persistentB (missing)
        test_pipeline = pipeline(
            [
                node(multi_output_func, "input", ["memA", "memB"], name="multiNode"),
                node(identity, "memA", "persistentA", name="nodeA"),
                node(identity, "memB", "persistentB", name="nodeB"),
            ]
        )

        # Mock exists: persistentA exists, persistentB missing
        def mock_exists(dataset_name):
            return dataset_name == "persistentA"

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["input"] = MemoryDataset("input_data")
        catalog["memA"] = MemoryDataset()
        catalog["memB"] = MemoryDataset()
        catalog["persistentA"] = LambdaDataset(
            load=lambda: "dataA", save=lambda x: None
        )
        catalog["persistentB"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should warn about the wasteful output but still run the node
        assert "Node 'multiNode' produces outputs ['memA']" in caplog.text
        assert "consumed by skipped nodes" in caplog.text
        assert "must run to produce other needed outputs" in caplog.text

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

    def test_only_missing_outputs_no_wasteful_optimization_needed(self, mocker, caplog):
        """Test case where initial filtering is already optimal"""
        # Set caplog to capture DEBUG level logs
        caplog.set_level(logging.DEBUG)

        catalog = DataCatalog()

        # Simple linear pipeline - no waste possible
        # input -> nodeA -> mem -> nodeB -> persistent (missing)
        test_pipeline = pipeline(
            [
                node(identity, "input", "mem", name="nodeA"),
                node(identity, "mem", "persistent", name="nodeB"),
            ]
        )

        def mock_exists(dataset_name):
            return False  # persistent is missing

        catalog.exists = mocker.Mock(side_effect=mock_exists)
        catalog["input"] = MemoryDataset("input_data")
        catalog["mem"] = MemoryDataset()
        catalog["persistent"] = LambdaDataset(load=lambda: None, save=lambda x: None)

        runner = SequentialRunner()
        spy_wasteful = mocker.spy(runner, "_remove_wasteful_nodes")

        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Should call wasteful removal but no nodes should be removed
        spy_wasteful.assert_called_once()
        assert "Running all 2 nodes (no outputs to skip)" in caplog.text

    def test_only_missing_outputs_debug_logging(self, mocker, caplog):
        """Test that debug logging for removing wasteful nodes is properly logged"""
        # Set caplog to capture DEBUG level logs
        caplog.set_level(logging.DEBUG, logger="kedro.runner")

        catalog = DataCatalog()

        # Create a simple pipeline where one node will be removed
        # nodeA -> memA -> nodeB -> persistentB (exists)
        # This should result in both nodes being skipped
        test_pipeline = pipeline(
            [
                node(identity, "input", "memA", name="nodeA"),
                node(identity, "memA", "persistentB", name="nodeB"),
            ]
        )

        # Mock exists: persistentB exists
        catalog.exists = mocker.Mock(return_value=True)
        catalog["input"] = MemoryDataset("input_data")
        catalog["memA"] = MemoryDataset()
        catalog["persistentB"] = LambdaDataset(
            load=lambda: "dataB", save=lambda x: None
        )

        runner = SequentialRunner()
        runner.run(test_pipeline, catalog, only_missing_outputs=True)

        # Check that the debug log for removing wasteful nodes was hit
        debug_logs = [
            record.message for record in caplog.records if record.levelname == "DEBUG"
        ]
        assert any(
            "Removing node 'nodeA' as it only produces outputs consumed by skipped nodes"
            in log
            for log in debug_logs
        )


class TestSuggestResumeScenario:
    @pytest.mark.parametrize(
        "failing_node_names,expected_pattern",
        [
            (["node1_A", "node1_B"], r"No nodes ran."),
            (["node2"], r"(node1_A,node1_B|node1_B,node1_A)"),
            (["node3_A"], r"(node3_A,node3_B|node3_B,node3_A|node3_A)"),
            (["node4_A"], r"(node3_A,node3_B|node3_B,node3_A|node3_A)"),
            (["node3_A", "node4_A"], r"(node3_A,node3_B|node3_B,node3_A|node3_A)"),
            (["node2", "node4_A"], r"(node1_A,node1_B|node1_B,node1_A)"),
        ],
    )
    def test_suggest_resume_scenario(
        self,
        caplog,
        two_branches_crossed_pipeline,
        persistent_dataset_catalog,
        failing_node_names,
        expected_pattern,
    ):
        nodes = {n.name: n for n in two_branches_crossed_pipeline.nodes}
        for name in failing_node_names:
            two_branches_crossed_pipeline -= pipeline([nodes[name]])
            two_branches_crossed_pipeline += pipeline(
                [nodes[name]._copy(func=exception_fn)]
            )
        with pytest.raises(Exception):
            SequentialRunner().run(
                two_branches_crossed_pipeline,
                persistent_dataset_catalog,
                hook_manager=_create_hook_manager(),
            )
        assert re.search(expected_pattern, caplog.text)

    @pytest.mark.parametrize(
        "failing_node_names,expected_pattern",
        [
            (["node1_A", "node1_B"], r"No nodes ran."),
            (["node2"], r'"node1_A,node1_B"'),
            (["node3_A"], r"(node3_A,node3_B|node3_A)"),
            (["node4_A"], r"(node3_A,node3_B|node3_A)"),
            (["node3_A", "node4_A"], r"(node3_A,node3_B|node3_A)"),
            (["node2", "node4_A"], r'"node1_A,node1_B"'),
        ],
    )
    def test_stricter_suggest_resume_scenario(
        self,
        caplog,
        two_branches_crossed_pipeline_variable_inputs,
        persistent_dataset_catalog,
        failing_node_names,
        expected_pattern,
    ):
        """
        Stricter version of previous test.
        Covers pipelines where inputs are shared across nodes.
        """
        test_pipeline = two_branches_crossed_pipeline_variable_inputs

        nodes = {n.name: n for n in test_pipeline.nodes}
        for name in failing_node_names:
            test_pipeline -= pipeline([nodes[name]])
            test_pipeline += pipeline([nodes[name]._copy(func=exception_fn)])

        with pytest.raises(Exception, match="test exception"):
            SequentialRunner().run(
                test_pipeline,
                persistent_dataset_catalog,
                hook_manager=_create_hook_manager(),
            )
        assert re.search(expected_pattern, caplog.text)


class TestMemoryDatasetBehaviour:
    def test_run_includes_memory_datasets(self, pipeline_with_memory_datasets):
        # Create a catalog with MemoryDataset entries and inputs for the pipeline
        catalog = DataCatalog(
            {
                "Input1": LambdaDataset(load=lambda: "data1", save=lambda data: None),
                "Input2": LambdaDataset(load=lambda: "data2", save=lambda data: None),
                "MemOutput1": MemoryDataset(),
                "MemOutput2": MemoryDataset(),
            }
        )

        # Add a regular dataset to the catalog
        catalog["RegularOutput"] = LambdaDataset(None, None, lambda: True)

        # Run the pipeline
        output = SequentialRunner().run(pipeline_with_memory_datasets, catalog)

        # Check that MemoryDataset outputs are included in the run results
        assert "MemOutput1" in output
        assert "MemOutput2" in output
        assert (
            "RegularOutput" not in output
        )  # This output is registered in DataCatalog and so should not be in free outputs
