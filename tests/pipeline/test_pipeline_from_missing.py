from unittest import mock

import pytest

from kedro.framework.hooks import _create_hook_manager
from kedro.io import DataCatalog, LambdaDataset
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


def _make_catalog(
    existent=None, non_existent=None, no_exists_method=None, feed_dict=None
):
    """Creates a catalog of existent and non-existent Datasets."""
    existent = [] if existent is None else existent
    non_existent = [] if non_existent is None else non_existent
    no_exists_method = [] if no_exists_method is None else no_exists_method

    catalog = DataCatalog(feed_dict=feed_dict)
    for source in existent:
        catalog.add(source, LambdaDataset(None, None, lambda: True))
    for source in non_existent:
        catalog.add(source, LambdaDataset(None, None, lambda: False))
    # Some LambdaDataset do not have exists() method
    for source in no_exists_method:
        catalog.add(source, LambdaDataset(None, None))
    return catalog


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
    def test_all_missing(self, branched_pipeline, hook_manager):
        catalog = _make_catalog(non_existent=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_none_missing(self, branched_pipeline, hook_manager):
        catalog = _make_catalog(existent=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_none_missing_feeddict_only(self, branched_pipeline, hook_manager):
        feed_dict = {"A": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
        catalog = _make_catalog(feed_dict=feed_dict)
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_first_missing(self, branched_pipeline, hook_manager):
        """combine from B and C is missing."""
        catalog = _make_catalog(non_existent=["B", "C"], existent=["A", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_only_left_missing(self, branched_pipeline, hook_manager):
        catalog = _make_catalog(non_existent=["B"], existent=["A", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "combine", "split", "right_out"]
        )

    def test_last_missing(self, branched_pipeline, hook_manager):
        """r-out from F is missing."""
        catalog = _make_catalog(non_existent=["F"], existent=["A", "B", "C", "D", "E"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

    def test_missing_and_no_exists(self, branched_pipeline, caplog, hook_manager):
        """If F doesn't have exists(), F is treated as missing."""
        catalog = _make_catalog(
            existent=["A", "B", "C", "D", "E"], no_exists_method=["F"]
        )
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

        log_record = caplog.records[0]
        assert log_record.levelname == "WARNING"
        assert (
            "'exists()' not implemented for 'LambdaDataset'" in log_record.getMessage()
        )

    def test_all_no_exists_method(self, branched_pipeline, caplog, hook_manager):
        catalog = _make_catalog(no_exists_method=["A", "B", "C", "D", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

        log_msgs = [record.getMessage() for record in caplog.records]
        expected_msg = (
            "'exists()' not implemented for 'LambdaDataset'. "
            "Assuming output does not exist."
        )
        assert expected_msg in log_msgs

    def test_catalog_and_feed_dict(self, branched_pipeline, hook_manager):
        """Mix of feed_dict and non-existent F."""
        catalog = _make_catalog(non_existent=["F"], existent=["D", "E"])
        catalog.add_feed_dict({"A": 1, "B": 2, "C": 3})
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])


class TestPipelineUnregistered:
    def test_propagate_up(self, branched_pipeline, hook_manager):
        """If a node needs to be rerun and requires unregistered (node-to-node)
        inputs, all necessary upstream nodes should be added.
        """
        catalog = _make_catalog(existent=["A"], non_existent=["E"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "right_in", "combine", "split"]
        )

    def test_propagate_down_then_up(self, branched_pipeline, hook_manager):
        """Unregistered (node-to-node) inputs for downstream nodes
        should be included, too.
        """
        catalog = _make_catalog(existent=["A", "D", "E"], non_existent=["C"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipelines_equal(branched_pipeline, new_pipeline)

    def test_ignore_unneccessary_unreg(self, branched_pipeline, hook_manager):
        """Unregistered (node-to-node) data sources should not trigger
        reruns, unless necessary to recreate registered data sources.
        """
        catalog = _make_catalog(existent=["A", "E", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, [])

    def test_partial_propagation(self, branched_pipeline, hook_manager):
        """Unregistered (node-to-node) data sources should not trigger
        reruns, unless necessary to recreate registered data sources.
        """
        catalog = _make_catalog(existent=["A", "D"], no_exists_method=["F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["split", "right_out"])

    def test_partial_non_existent_propagation(self, branched_pipeline, hook_manager):
        """A non existent dataset whose node has one unregistered input
        and one existent input should be recalculated correctly.
        """
        catalog = _make_catalog(existent=["A", "C", "E", "F"], non_existent=["D"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(
            new_pipeline, ["left_in", "combine", "split", "right_out"]
        )

    def test_free_output(self, branched_pipeline, hook_manager):
        """Free outputs are the only unregistered data sources that
        should trigger runs.
        """
        catalog = _make_catalog(existent=["A", "B", "C", "F"])
        new_pipeline = _from_missing(branched_pipeline, catalog, hook_manager)
        assert _pipeline_contains(new_pipeline, ["combine", "split"])
