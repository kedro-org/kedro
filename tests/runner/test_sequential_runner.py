from __future__ import annotations

import re
from typing import Any

import pandas as pd
import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import (
    AbstractDataset,
    DataCatalog,
    DatasetError,
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
        assert result["Z"].load() == (42, 42, 42)

    def test_run_without_plugin_manager(self, fan_out_fan_in, catalog):
        catalog["A"] = 42
        result = SequentialRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert result["Z"].load() == (42, 42, 42)

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
        assert outputs["ds3"].load() == 42

    def test_no_feed(self, is_async, memory_catalog, branchless_pipeline):
        outputs = SequentialRunner(is_async=is_async).run(
            branchless_pipeline, memory_catalog
        )
        assert "ds3" in outputs
        assert outputs["ds3"].load()["data"] == 42

    def test_node_returning_none(self, is_async, saving_none_pipeline, catalog):
        pattern = "Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            SequentialRunner(is_async=is_async).run(saving_none_pipeline, catalog)

    def test_saved_output_is_returned_by_runner(
        self, is_async, saving_result_pipeline, persistent_test_dataset
    ):
        def _load():
            return 0

        def _save(arg):
            assert arg == 0

        catalog = DataCatalog(
            {
                "ds": persistent_test_dataset(load=_load, save=_save),
                "dsX": persistent_test_dataset(load=_load, save=_save),
            }
        )
        output = SequentialRunner(is_async=is_async).run(
            saving_result_pipeline, catalog
        )

        assert "dsX" in output
        assert output["dsX"].load() == 0


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
        assert outputs["ds5"].load() == [1, 2, 3, 4, 5]
        assert isinstance(outputs["ds8"].load(), dict)
        # the pipeline runs ds1->ds4->ds8
        assert outputs["ds8"].load()["data"] == 42
        # the pipeline runs ds3
        assert isinstance(outputs["ds6"].load(), pd.DataFrame)

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
        assert isinstance(outputs["ds8"].load(), dict)
        assert outputs["ds8"].load()["data"] == 0
        assert isinstance(outputs["ds6"].load(), pd.DataFrame)

    def test_unsatisfied_inputs(self, is_async, unfinished_outputs_pipeline, catalog):
        """ds1, ds2 and ds3 were not specified."""
        with pytest.raises(DatasetError, match="has not been saved yet"):
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

    def test_is_persistent_and_missing(self, mocker):
        """Test _is_persistent_and_missing method logic"""
        runner = SequentialRunner()
        catalog = DataCatalog()

        # Test ephemeral dataset (MemoryDataset)
        mem_dataset = MemoryDataset()
        catalog._datasets = {"mem_output": mem_dataset}
        assert not runner._is_persistent_and_missing("mem_output", catalog)

        # Test persistent dataset that exists
        mock_dataset = mocker.Mock()
        mock_dataset._EPHEMERAL = False
        catalog._datasets = {"persist_output": mock_dataset}
        catalog.exists = mocker.Mock(return_value=True)
        assert not runner._is_persistent_and_missing("persist_output", catalog)

        # Test persistent dataset that doesn't exist
        catalog.exists = mocker.Mock(return_value=False)
        assert runner._is_persistent_and_missing("persist_output", catalog)

        # Test undefined dataset (not in catalog, no factory pattern)
        catalog._datasets = {}
        catalog.__contains__ = mocker.Mock(return_value=False)
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

    def test_is_output_missing_various_conditions(self, mocker):
        """Test _is_output_missing method with various conditions"""
        runner = SequentialRunner()

        # Test 1: Dataset in catalog and is ephemeral
        catalog = DataCatalog()
        ephemeral_dataset = MemoryDataset()
        catalog._datasets = {"ephemeral_out": ephemeral_dataset}
        assert runner._is_output_missing("ephemeral_out", catalog) is False

        # Test 2: Dataset in catalog, not ephemeral, exists
        catalog = DataCatalog()
        persistent_dataset = mocker.Mock()
        persistent_dataset._EPHEMERAL = False
        catalog._datasets = {"persistent_exists": persistent_dataset}
        catalog.exists = mocker.Mock(return_value=True)
        assert runner._is_output_missing("persistent_exists", catalog) is False

        # Test 3: Dataset in catalog, not ephemeral, doesn't exist
        catalog = DataCatalog()
        persistent_dataset = mocker.Mock()
        persistent_dataset._EPHEMERAL = False
        catalog._datasets = {"persistent_exists": persistent_dataset}
        catalog.exists = mocker.Mock(return_value=False)
        assert runner._is_output_missing("persistent_exists", catalog) is True

        # Test 4: Dataset in catalog, exists check raises exception
        catalog = DataCatalog()
        persistent_dataset = mocker.Mock()
        persistent_dataset._EPHEMERAL = False
        catalog._datasets = {"persistent_exists": persistent_dataset}
        catalog.exists = mocker.Mock(side_effect=Exception("Connection error"))
        assert runner._is_output_missing("persistent_exists", catalog) is True

        # Test 5: Dataset not in catalog._datasets but in catalog (factory pattern), exists
        # Use a mock catalog to properly control __contains__ behavior
        catalog = mocker.Mock()
        catalog._datasets = {}
        catalog.__contains__ = mocker.Mock(return_value=True)
        catalog.exists = mocker.Mock(return_value=True)
        assert runner._is_output_missing("factory_dataset", catalog) is False

        # Test 6: Dataset not in catalog._datasets but in catalog (factory pattern), doesn't exist
        catalog = mocker.Mock()
        catalog._datasets = {}
        catalog.__contains__ = mocker.Mock(return_value=True)
        catalog.exists = mocker.Mock(return_value=False)
        assert runner._is_output_missing("factory_dataset", catalog) is True

        # Test 7: Dataset not in catalog at all
        catalog = mocker.Mock()
        catalog._datasets = {}
        catalog.__contains__ = mocker.Mock(return_value=False)
        assert runner._is_output_missing("undefined_dataset", catalog) is True

        # Test 8: __contains__ check raises exception (lines 310-312)
        catalog = mocker.Mock()
        catalog._datasets = {}
        catalog.__contains__ = mocker.Mock(side_effect=Exception("Catalog error"))
        assert runner._is_output_missing("error_dataset", catalog) is True


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
    def test_run_includes_memory_datasets(
        self, pipeline_with_memory_datasets, persistent_test_dataset
    ):
        # Create a catalog with MemoryDataset entries and inputs for the pipeline
        catalog = DataCatalog(
            {
                "Input1": persistent_test_dataset(
                    load=lambda: "data1", save=lambda data: None
                ),
                "Input2": persistent_test_dataset(
                    load=lambda: "data2", save=lambda data: None
                ),
                "MemOutput1": MemoryDataset(),
                "MemOutput2": MemoryDataset(),
            }
        )

        # Add a regular dataset to the catalog
        catalog["RegularOutput"] = persistent_test_dataset(None, None, lambda: True)

        # Run the pipeline
        output = SequentialRunner().run(pipeline_with_memory_datasets, catalog)

        # Check that MemoryDataset outputs are included in the run results
        assert "MemOutput1" in output
        assert "MemOutput2" in output
        assert (
            "RegularOutput" not in output
        )  # This output is registered in DataCatalog and so should not be in free outputs
