from __future__ import annotations

import re
from concurrent.futures.process import ProcessPoolExecutor
from typing import Any

import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import (
    AbstractDataset,
    DataCatalog,
    DatasetError,
    LambdaDataset,
    MemoryDataset,
)
from kedro.pipeline import node
from kedro.pipeline.modular_pipeline import pipeline as modular_pipeline
from kedro.runner import ParallelRunner
from kedro.runner.parallel_runner import (
    ParallelRunnerManager,
)
from kedro.runner.runner import _MAX_WINDOWS_WORKERS
from tests.runner.conftest import (
    exception_fn,
    identity,
    return_none,
    return_not_serialisable,
    sink,
    source,
)


class SingleProcessDataset(AbstractDataset):
    def __init__(self):
        self._SINGLE_PROCESS = True

    def _load(self):
        pass

    def _save(self):
        pass

    def _describe(self):
        pass


class TestValidParallelRunner:
    @pytest.mark.parametrize("is_async", [False, True])
    def test_parallel_run(self, is_async, fan_out_fan_in, catalog):
        catalog.add_feed_dict({"A": 42})
        result = ParallelRunner(is_async=is_async).run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)

    @pytest.mark.parametrize("is_async", [False, True])
    def test_parallel_run_with_plugin_manager(self, is_async, fan_out_fan_in, catalog):
        catalog.add_feed_dict({"A": 42})
        result = ParallelRunner(is_async=is_async).run(
            fan_out_fan_in, catalog, hook_manager=_create_hook_manager()
        )
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)

    @pytest.mark.parametrize("is_async", [False, True])
    def test_memory_dataset_input(self, is_async, fan_out_fan_in):
        pipeline = modular_pipeline([fan_out_fan_in])
        catalog = DataCatalog({"A": MemoryDataset("42")})
        result = ParallelRunner(is_async=is_async).run(pipeline, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == ("42", "42", "42")

    def test_log_not_using_async(self, fan_out_fan_in, catalog, caplog):
        catalog.add_feed_dict({"A": 42})
        ParallelRunner().run(fan_out_fan_in, catalog)
        assert "Using synchronous mode for loading and saving data." in caplog.text


class TestMaxWorkers:
    @pytest.mark.parametrize("is_async", [False, True])
    @pytest.mark.parametrize(
        "cpu_cores, user_specified_number, expected_number",
        [
            # The pipeline only needs 3 processes, no need for more
            (4, 6, 3),
            (4, None, 3),
            # We need 3 processes, but only 2 CPU cores available
            (2, None, 2),
            # Even though we have 1 CPU core, allow user to use more.
            (1, 2, 2),
        ],
    )
    def test_specified_max_workers_bellow_cpu_cores_count(
        self,
        is_async,
        mocker,
        fan_out_fan_in,
        catalog,
        cpu_cores,
        user_specified_number,
        expected_number,
    ):
        """
        The system has 2 cores, but we initialize the runner with max_workers=4.
        `fan_out_fan_in` pipeline needs 3 processes.
        A pool with 3 workers should be used.
        """
        mocker.patch("os.cpu_count", return_value=cpu_cores)

        executor_cls_mock = mocker.patch(
            "kedro.runner.parallel_runner.ProcessPoolExecutor",
            wraps=ProcessPoolExecutor,
        )

        catalog.add_feed_dict({"A": 42})
        result = ParallelRunner(
            max_workers=user_specified_number, is_async=is_async
        ).run(fan_out_fan_in, catalog)
        assert result == {"Z": (42, 42, 42)}

        executor_cls_mock.assert_called_once_with(max_workers=expected_number)

    def test_max_worker_windows(self, mocker):
        """The ProcessPoolExecutor on Python 3.7+
        has a quirk with the max worker number on Windows
        and requires it to be <=61
        """
        mocker.patch("os.cpu_count", return_value=100)
        mocker.patch("sys.platform", "win32")

        parallel_runner = ParallelRunner()
        assert parallel_runner._max_workers == _MAX_WINDOWS_WORKERS


@pytest.mark.parametrize("is_async", [False, True])
class TestInvalidParallelRunner:
    def test_task_node_validation(self, is_async, fan_out_fan_in, catalog):
        """ParallelRunner cannot serialise the lambda function."""
        catalog.add_feed_dict({"A": 42})
        pipeline = modular_pipeline([fan_out_fan_in, node(lambda x: x, "Z", "X")])
        with pytest.raises(AttributeError):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_task_dataset_validation(self, is_async, fan_out_fan_in, catalog):
        """ParallelRunner cannot serialise datasets marked with `_SINGLE_PROCESS`."""
        catalog.add("A", SingleProcessDataset())
        with pytest.raises(AttributeError):
            ParallelRunner(is_async=is_async).run(fan_out_fan_in, catalog)

    def test_task_exception(self, is_async, fan_out_fan_in, catalog):
        catalog.add_feed_dict(feed_dict={"A": 42})
        pipeline = modular_pipeline([fan_out_fan_in, node(exception_fn, "Z", "X")])
        with pytest.raises(Exception, match="test exception"):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_memory_dataset_output(self, is_async, fan_out_fan_in):
        """ParallelRunner does not support output to externally
        created MemoryDatasets.
        """
        pipeline = modular_pipeline([fan_out_fan_in])
        catalog = DataCatalog({"C": MemoryDataset()}, {"A": 42})
        with pytest.raises(AttributeError, match="['C']"):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_node_returning_none(self, is_async):
        pipeline = modular_pipeline(
            [node(identity, "A", "B"), node(return_none, "B", "C")]
        )
        catalog = DataCatalog({"A": MemoryDataset("42")})
        pattern = "Saving 'None' to a 'Dataset' is not allowed"
        with pytest.raises(DatasetError, match=pattern):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_dataset_not_serialisable(self, is_async, fan_out_fan_in):
        """Data set A cannot be serialisable because _load and _save are not
        defined in global scope.
        """

        def _load():
            return 0  # pragma: no cover

        def _save(arg):
            assert arg == 0  # pragma: no cover

        # Data set A cannot be serialised
        catalog = DataCatalog({"A": LambdaDataset(load=_load, save=_save)})

        pipeline = modular_pipeline([fan_out_fan_in])
        with pytest.raises(AttributeError, match="['A']"):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_memory_dataset_not_serialisable(self, is_async, catalog):
        """Memory dataset cannot be serialisable because of data it stores."""
        data = return_not_serialisable(None)
        pipeline = modular_pipeline([node(return_not_serialisable, "A", "B")])
        catalog.add_feed_dict(feed_dict={"A": 42})
        pattern = (
            rf"{data.__class__!s} cannot be serialised. ParallelRunner implicit "
            rf"memory datasets can only be used with serialisable data"
        )

        with pytest.raises(DatasetError, match=pattern):
            ParallelRunner(is_async=is_async).run(pipeline, catalog)

    def test_unable_to_schedule_all_nodes(
        self, mocker, is_async, fan_out_fan_in, catalog
    ):
        """Test the error raised when `futures` variable is empty,
        but `todo_nodes` is not (can barely happen in real life).
        """
        catalog.add_feed_dict({"A": 42})
        runner = ParallelRunner(is_async=is_async)

        real_node_deps = fan_out_fan_in.node_dependencies
        # construct deliberately unresolvable dependencies for all
        # pipeline nodes, so that none can be run
        fake_node_deps = {k: {"you_shall_not_pass"} for k in real_node_deps}
        # property mock requires patching a class, not an instance
        mocker.patch(
            "kedro.pipeline.Pipeline.node_dependencies",
            new_callable=mocker.PropertyMock,
            return_value=fake_node_deps,
        )

        pattern = "Unable to schedule new tasks although some nodes have not been run"
        with pytest.raises(RuntimeError, match=pattern):
            runner.run(fan_out_fan_in, catalog)


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


ParallelRunnerManager.register("LoggingDataset", LoggingDataset)


@pytest.fixture
def logging_dataset_catalog():
    log = []
    persistent_dataset = LoggingDataset(log, "in", "stuff")
    return DataCatalog(
        {
            "ds0_A": persistent_dataset,
            "ds0_B": persistent_dataset,
            "ds2_A": persistent_dataset,
            "ds2_B": persistent_dataset,
            "dsX": persistent_dataset,
            "dsY": persistent_dataset,
            "params:p": MemoryDataset(1),
        }
    )


@pytest.mark.parametrize("is_async", [False, True])
class TestParallelRunnerRelease:
    def test_dont_release_inputs_and_outputs(self, is_async):
        runner = ParallelRunner(is_async=is_async)
        log = runner._manager.list()

        pipeline = modular_pipeline(
            [node(identity, "in", "middle"), node(identity, "middle", "out")]
        )
        catalog = DataCatalog(
            {
                "in": runner._manager.LoggingDataset(log, "in", "stuff"),
                "middle": runner._manager.LoggingDataset(log, "middle"),
                "out": runner._manager.LoggingDataset(log, "out"),
            }
        )
        ParallelRunner().run(pipeline, catalog)

        # we don't want to see release in or out in here
        assert list(log) == [("load", "in"), ("load", "middle"), ("release", "middle")]

    def test_release_at_earliest_opportunity(self, is_async):
        runner = ParallelRunner(is_async=is_async)
        log = runner._manager.list()

        pipeline = modular_pipeline(
            [
                node(source, None, "first"),
                node(identity, "first", "second"),
                node(sink, "second", None),
            ]
        )
        catalog = DataCatalog(
            {
                "first": runner._manager.LoggingDataset(log, "first"),
                "second": runner._manager.LoggingDataset(log, "second"),
            }
        )
        runner.run(pipeline, catalog)

        # we want to see "release first" before "load second"
        assert list(log) == [
            ("load", "first"),
            ("release", "first"),
            ("load", "second"),
            ("release", "second"),
        ]

    def test_count_multiple_loads(self, is_async):
        runner = ParallelRunner(is_async=is_async)
        log = runner._manager.list()

        pipeline = modular_pipeline(
            [
                node(source, None, "dataset"),
                node(sink, "dataset", None, name="bob"),
                node(sink, "dataset", None, name="fred"),
            ]
        )
        catalog = DataCatalog(
            {"dataset": runner._manager.LoggingDataset(log, "dataset")}
        )
        runner.run(pipeline, catalog)

        # we want to the release after both the loads
        assert list(log) == [
            ("load", "dataset"),
            ("load", "dataset"),
            ("release", "dataset"),
        ]

    def test_release_transcoded(self, is_async):
        runner = ParallelRunner(is_async=is_async)
        log = runner._manager.list()

        pipeline = modular_pipeline(
            [node(source, None, "ds@save"), node(sink, "ds@load", None)]
        )
        catalog = DataCatalog(
            {
                "ds@save": LoggingDataset(log, "save"),
                "ds@load": LoggingDataset(log, "load"),
            }
        )

        ParallelRunner().run(pipeline, catalog)

        # we want to see both datasets being released
        assert list(log) == [("release", "save"), ("load", "load"), ("release", "load")]


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
        logging_dataset_catalog,
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
            ParallelRunner().run(
                two_branches_crossed_pipeline,
                logging_dataset_catalog,
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
        logging_dataset_catalog,
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
            test_pipeline -= modular_pipeline([nodes[name]])
            test_pipeline += modular_pipeline([nodes[name]._copy(func=exception_fn)])

        with pytest.raises(Exception, match="test exception"):
            ParallelRunner().run(
                test_pipeline,
                logging_dataset_catalog,
                hook_manager=_create_hook_manager(),
            )
        assert re.search(expected_pattern, caplog.text)
