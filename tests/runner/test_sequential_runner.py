import re
from typing import Any, Dict

import pandas as pd
import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import AbstractDataSet, DataCatalog, DataSetError, LambdaDataSet
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner
from tests.runner.conftest import exception_fn, identity, sink, source


class TestValidSequentialRunner:
    def test_run_with_plugin_manager(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = SequentialRunner().run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)

    def test_run_without_plugin_manager(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
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

    def test_no_data_sets(self, is_async, branchless_pipeline):
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
        pattern = "Saving 'None' to a 'DataSet' is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            SequentialRunner(is_async=is_async).run(saving_none_pipeline, catalog)

    def test_result_saved_not_returned(self, is_async, saving_result_pipeline):
        """The pipeline runs ds->dsX but save does not save the output."""

        def _load():
            return 0

        def _save(arg):
            assert arg == 0

        catalog = DataCatalog(
            {
                "ds": LambdaDataSet(load=_load, save=_save),
                "dsX": LambdaDataSet(load=_load, save=_save),
            }
        )
        output = SequentialRunner(is_async=is_async).run(
            saving_result_pipeline, catalog
        )

        assert output == {}


@pytest.mark.parametrize("is_async", [False, True])
class TestSeqentialRunnerBranchedPipeline:
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


class LoggingDataSet(AbstractDataSet):
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

    def _describe(self) -> Dict[str, Any]:
        return {}


@pytest.mark.parametrize("is_async", [False, True])
class TestSequentialRunnerRelease:
    def test_dont_release_inputs_and_outputs(self, is_async):
        log = []
        pipeline = Pipeline(
            [node(identity, "in", "middle"), node(identity, "middle", "out")]
        )
        catalog = DataCatalog(
            {
                "in": LoggingDataSet(log, "in", "stuff"),
                "middle": LoggingDataSet(log, "middle"),
                "out": LoggingDataSet(log, "out"),
            }
        )
        SequentialRunner(is_async=is_async).run(pipeline, catalog)

        # we don't want to see release in or out in here
        assert log == [("load", "in"), ("load", "middle"), ("release", "middle")]

    def test_release_at_earliest_opportunity(self, is_async):
        log = []
        pipeline = Pipeline(
            [
                node(source, None, "first"),
                node(identity, "first", "second"),
                node(sink, "second", None),
            ]
        )
        catalog = DataCatalog(
            {
                "first": LoggingDataSet(log, "first"),
                "second": LoggingDataSet(log, "second"),
            }
        )
        SequentialRunner(is_async=is_async).run(pipeline, catalog)

        # we want to see "release first" before "load second"
        assert log == [
            ("load", "first"),
            ("release", "first"),
            ("load", "second"),
            ("release", "second"),
        ]

    def test_count_multiple_loads(self, is_async):
        log = []
        pipeline = Pipeline(
            [
                node(source, None, "dataset"),
                node(sink, "dataset", None, name="bob"),
                node(sink, "dataset", None, name="fred"),
            ]
        )
        catalog = DataCatalog({"dataset": LoggingDataSet(log, "dataset")})
        SequentialRunner(is_async=is_async).run(pipeline, catalog)

        # we want to the release after both the loads
        assert log == [("load", "dataset"), ("load", "dataset"), ("release", "dataset")]

    def test_release_transcoded(self, is_async):
        log = []
        pipeline = Pipeline(
            [node(source, None, "ds@save"), node(sink, "ds@load", None)]
        )
        catalog = DataCatalog(
            {
                "ds@save": LoggingDataSet(log, "save"),
                "ds@load": LoggingDataSet(log, "load"),
            }
        )

        SequentialRunner(is_async=is_async).run(pipeline, catalog)

        # we want to see both datasets being released
        assert log == [("release", "save"), ("load", "load"), ("release", "load")]

    @pytest.mark.parametrize(
        "pipeline",
        [
            Pipeline([node(identity, "ds1", "ds2", confirms="ds1")]),
            Pipeline(
                [
                    node(identity, "ds1", "ds2"),
                    node(identity, "ds2", None, confirms="ds1"),
                ]
            ),
        ],
    )
    def test_confirms(self, mocker, pipeline, is_async):
        fake_dataset_instance = mocker.Mock()
        catalog = DataCatalog(data_sets={"ds1": fake_dataset_instance})
        SequentialRunner(is_async=is_async).run(pipeline, catalog)
        fake_dataset_instance.confirm.assert_called_once_with()


@pytest.mark.parametrize(
    "failing_node_indexes,expected_pattern",
    [
        ([0], r"No nodes ran."),
        ([2], r"(node1_A,node1_B|node1_B,node1_A)"),
        ([3], r"(node3_A,node3_B|node3_B,node3_A)"),
        ([5], r"(node3_A,node3_B|node3_B,node3_A)"),
        ([3, 5], r"(node3_A,node3_B|node3_B,node3_A)"),
        ([2, 5], r"(node1_A,node1_B|node1_B,node1_A)"),
    ],
)
class TestSuggestResumeScenario:
    def test_suggest_resume_scenario(
        self,
        caplog,
        two_branches_crossed_pipeline,
        persistent_dataset_catalog,
        failing_node_indexes,
        expected_pattern,
    ):
        for idx in failing_node_indexes:
            failing_node = two_branches_crossed_pipeline.nodes[idx]
            two_branches_crossed_pipeline -= Pipeline([failing_node])
            two_branches_crossed_pipeline += Pipeline(
                [failing_node._copy(func=exception_fn)]
            )
        with pytest.raises(Exception):
            SequentialRunner().run(
                two_branches_crossed_pipeline,
                persistent_dataset_catalog,
                hook_manager=_create_hook_manager(),
            )
        assert re.search(expected_pattern, caplog.text)
