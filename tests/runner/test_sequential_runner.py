from __future__ import annotations

import re
from typing import Any

import pandas as pd
import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import AbstractDataset, DataCatalog, DatasetError, LambdaDataset
from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.runner import SequentialRunner
from tests.runner.conftest import exception_fn, identity, sink, source


class TestValidSequentialRunner:
    def test_run_with_plugin_manager(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict({"A": 42})
        result = SequentialRunner().run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)

    def test_run_without_plugin_manager(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict({"A": 42})
        result = SequentialRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)


@pytest.mark.parametrize("is_async", [False, True])
class TestSeqentialRunnerBranchlessPipeline:
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
        pandas_df_feed_dict,
    ):
        memory_catalog.add_feed_dict(pandas_df_feed_dict, replace=True)
        outputs = SequentialRunner(is_async=is_async).run(
            unfinished_outputs_pipeline, memory_catalog
        )
        assert set(outputs.keys()) == {"ds8", "ds5", "ds6"}
        # the pipeline runs ds2->ds5
        assert outputs["ds5"] == [1, 2, 3, 4, 5]
        assert isinstance(outputs["ds8"], dict)
        # the pipeline runs ds1->ds4->ds8
        assert outputs["ds8"]["data"] == 42
        # the pipline runs ds3
        assert isinstance(outputs["ds6"], pd.DataFrame)

    def test_conflict_feed_catalog(
        self,
        is_async,
        memory_catalog,
        unfinished_outputs_pipeline,
        conflicting_feed_dict,
    ):
        """ds1 and ds3 will be replaced with new inputs."""
        memory_catalog.add_feed_dict(conflicting_feed_dict, replace=True)
        outputs = SequentialRunner(is_async=is_async).run(
            unfinished_outputs_pipeline, memory_catalog
        )
        assert isinstance(outputs["ds8"], dict)
        assert outputs["ds8"]["data"] == 0
        assert isinstance(outputs["ds6"], pd.DataFrame)

    def test_unsatisfied_inputs(self, is_async, unfinished_outputs_pipeline, catalog):
        """ds1, ds2 and ds3 were not specified."""
        with pytest.raises(ValueError, match=r"not found in the DataCatalog"):
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
        test_pipeline = modular_pipeline(
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
        test_pipeline = modular_pipeline(
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
        test_pipeline = modular_pipeline(
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
        test_pipeline = modular_pipeline(
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
            modular_pipeline([node(identity, "ds1", "ds2", confirms="ds1")]),
            modular_pipeline(
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


@pytest.mark.parametrize(
    "failing_node_names,expected_pattern",
    [
        (["node1_A"], r"No nodes ran."),
        (["node2"], r"(node1_A,node1_B|node1_B,node1_A)"),
        (["node3_A"], r"(node3_A,node3_B|node3_B,node3_A)"),
        (["node4_A"], r"(node3_A,node3_B|node3_B,node3_A)"),
        (["node3_A", "node4_A"], r"(node3_A,node3_B|node3_B,node3_A)"),
        (["node2", "node4_A"], r"(node1_A,node1_B|node1_B,node1_A)"),
    ],
)
class TestSuggestResumeScenario:
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
            two_branches_crossed_pipeline -= modular_pipeline([nodes[name]])
            two_branches_crossed_pipeline += modular_pipeline(
                [nodes[name]._copy(func=exception_fn)]
            )
        with pytest.raises(Exception):
            SequentialRunner().run(
                two_branches_crossed_pipeline,
                persistent_dataset_catalog,
                hook_manager=_create_hook_manager(),
            )
        assert re.search(expected_pattern, caplog.text)
