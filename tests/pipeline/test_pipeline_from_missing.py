from unittest import mock

import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import DataCatalog
from kedro.pipeline import node, pipeline
from kedro.runner import SequentialRunner


# Different dummy func based on the number of arguments
def constant_output():
    return "output"  # pragma: no cover


def identity(input1: str):
    return input1  # pragma: no cover


def biconcat(input1: str, input2: str):
    return input1 + input2  # pragma: no cover


@pytest.fixture
def hook_manager():
    return _create_hook_manager()


@pytest.fixture
def branched_pipeline():
    # #### Pipeline execution order ####
    # Inputs: A
    #
    # left_in: identity([A]) -> [B]
    # right_in: constant_output(None) -> [C]
    # combine: biconcat([B,C]) -> [D]
    # split: identity([D]) -> [E,F]
    # right_out: identity([F]) -> None
    # Outputs: E
    #
    #  A
    #  |
    # l-in  r-in
    #  |     |
    #  B     C
    #   \   /
    #  combine
    #     |
    #     D
    #     |
    #   split
    #   /   \
    #  E     F
    #        |
    #       r-out
    #
    # ##################################
    return pipeline(
        [
            node(identity, "A", "B", name="left_in"),
            node(constant_output, None, "C", name="right_in"),
            node(biconcat, ["B", "C"], "D", name="combine"),
            node(identity, "D", ["E", "F"], name="split"),
            node(identity, "F", None, name="right_out"),
        ]
    )


@pytest.fixture
def make_catalog(persistent_test_dataset):
    def _make_catalog(
        existent=None,
        non_existent=None,
        no_exists_method=None,
        raw_data=None,
    ):
        """Creates a catalog of existent and non-existent Datasets."""
        existent = [] if existent is None else existent
        non_existent = [] if non_existent is None else non_existent
        no_exists_method = [] if no_exists_method is None else no_exists_method

        catalog = DataCatalog(raw_data=raw_data)
        for source in existent:
            catalog[source] = persistent_test_dataset(None, None, lambda: True)
        for source in non_existent:
            catalog[source] = persistent_test_dataset(None, None, lambda: False)
        for source in no_exists_method:
            catalog[source] = persistent_test_dataset(None, None)
        return catalog

    return _make_catalog


def _pipelines_equal(pipe1, pipe2):
    return set(pipe1.nodes) == set(pipe2.nodes)


def _pipeline_contains(pipe, nodes):
    return set(nodes) == {n.name for n in pipe.nodes}


def _from_missing(pipeline, catalog, hook_manager):
    """Create a new pipeline based on missing outputs."""
    name = "kedro.runner.runner.AbstractRunner.run"
    with mock.patch(name) as run:
        SequentialRunner().run_only_missing(pipeline, catalog, hook_manager)
        _, args, _ = run.mock_calls[0]
    new_pipeline = args[0]
    return new_pipeline


class TestPipelineMissing:
    def test_all_missing(self, branched_pipeline, hook_manager, make_catalog):
        catalog = make_catalog(non_existent=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_none_missing(self, branched_pipeline, hook_manager, make_catalog):
        catalog = make_catalog(existent=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_none_missing_feeddict_only(
        self, branched_pipeline, hook_manager, make_catalog
    ):
        raw_data = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
        catalog = make_catalog(raw_data=raw_data)
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_first_missing(self, branched_pipeline, hook_manager, make_catalog):
        """combine from B and C is missing."""
        catalog = make_catalog(non_existent=["B", "C"], existent=["A", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_only_left_missing(self, branched_pipeline, hook_manager, make_catalog):
        catalog = make_catalog(non_existent=["B"], existent=["A", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "combine", "split", "right_out"]
        )

    def test_last_missing(self, branched_pipeline, hook_manager, make_catalog):
        """r-out from F is missing."""
        catalog = make_catalog(non_existent=["F"], existent=["A", "B", "C", "D", "E"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

    def test_missing_and_no_exists(
        self, branched_pipeline, caplog, hook_manager, make_catalog
    ):
        """If F doesn't have exists(), F is treated as missing."""
        catalog = make_catalog(
            existent=["A", "B", "C", "D", "E"], no_exists_method=["F"]
        )
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "'exists()' not implemented for 'PersistentTestDataset'"
            in log_record.getMessage()
        )

    def test_all_no_exists_method(
        self, branched_pipeline, caplog, hook_manager, make_catalog
    ):
        catalog = make_catalog(no_exists_method=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

        log_msgs = [record.getMessage() for record in caplog.records]
        expected_msg = (
            "'exists()' not implemented for 'PersistentTestDataset'. "
            "Assuming output does not exist."
        )
        assert expected_msg in log_msgs


class TestPipelineUnregistered:
    def test_propagate_up(self, branched_pipeline, hook_manager, make_catalog):
        """If a node needs to be rerun and requires unregistered (node-to-node)
        inputs, all necessary upstream nodes should be added.
        """
        catalog = make_catalog(existent=["A"], non_existent=["E"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "right_in", "combine", "split"]
        )

    def test_propagate_down_then_up(
        self, branched_pipeline, hook_manager, make_catalog
    ):
        """Unregistered (node-to-node) inputs for downstream nodes
        should be included, too.
        """
        catalog = make_catalog(existent=["A", "D", "E"], non_existent=["C"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_ignore_unnecessary_unreg(
        self, branched_pipeline, hook_manager, make_catalog
    ):
        """Unregistered (node-to-node) data sources should not trigger
        reruns, unless necessary to recreate registered data sources.
        """
        catalog = make_catalog(existent=["A", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_partial_propagation(self, branched_pipeline, hook_manager, make_catalog):
        """Unregistered (node-to-node) data sources should not trigger
        reruns, unless necessary to recreate registered data sources.
        """
        catalog = make_catalog(existent=["A", "D"], no_exists_method=["F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        print([n.name for n in new_pipeline.nodes])
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

    def test_partial_non_existent_propagation(
        self, branched_pipeline, hook_manager, make_catalog
    ):
        """A non existent dataset whose node has one unregistered input
        and one existent input should be recalculated correctly.
        """
        catalog = make_catalog(existent=["A", "C", "E", "F"], non_existent=["D"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "combine", "split", "right_out"]
        )

    def test_free_output(self, branched_pipeline, hook_manager, make_catalog):
        """Free outputs are the only unregistered data sources that
        should trigger runs.
        """
        catalog = make_catalog(existent=["A", "B", "C", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["combine", "split"])
