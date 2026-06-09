import importlib
import inspect
from collections.abc import Iterator

import numpy as np

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

node_module = importlib.import_module("kedro.pipeline.node")


def generate_one():
    yield from range(10)


def generate_tuple():
    for i in range(10):
        yield i, i * i


def generate_list():
    for i in range(10):
        yield [i, i * i]


def generate_dict():
    for i in range(10):
        yield {"idx": i, "square": i * i}


class TestRunGeneratorNode:
    def test_generator_node_one(self, mocker, catalog):
        fake_dataset = mocker.Mock()

        mocker.patch.object(catalog, "get", return_value=fake_dataset)

        n = node(generate_one, inputs=None, outputs="result")
        runner = SequentialRunner()
        runner.run(Pipeline([n]), catalog, _NullPluginManager())

        expected = [((i,),) for i in range(10)]
        assert fake_dataset.save.call_count == 10
        assert fake_dataset.save.call_args_list == expected

    def test_generator_node_tuple(self, mocker, catalog):
        left = mocker.Mock()
        right = mocker.Mock()

        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        n = node(generate_tuple, inputs=None, outputs=["left", "right"])
        runner = SequentialRunner()
        runner.run(Pipeline([n]), catalog, _NullPluginManager())

        expected_left = [((i,),) for i in range(10)]
        expected_right = [((i * i,),) for i in range(10)]
        assert left.save.call_count == 10
        assert left.save.call_args_list == expected_left
        assert right.save.call_count == 10
        assert right.save.call_args_list == expected_right

    def test_generator_node_list(self, mocker, catalog):
        left = mocker.Mock()
        right = mocker.Mock()

        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        n = node(generate_list, inputs=None, outputs=["left", "right"])
        runner = SequentialRunner()
        runner.run(Pipeline([n]), catalog, _NullPluginManager())

        expected_left = [((i,),) for i in range(10)]
        expected_right = [((i * i,),) for i in range(10)]

        assert left.save.call_count == 10
        assert left.save.call_args_list == expected_left
        assert right.save.call_count == 10
        assert right.save.call_args_list == expected_right

    def test_generator_node_dict(self, mocker, catalog):
        left = mocker.Mock()
        right = mocker.Mock()

        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        n = node(generate_dict, inputs=None, outputs={"idx": "left", "square": "right"})
        runner = SequentialRunner()
        runner.run(Pipeline([n]), catalog, _NullPluginManager())

        expected_left = [((i,),) for i in range(10)]
        expected_right = [((i * i,),) for i in range(10)]

        assert 10 == left.save.call_count
        assert left.save.call_args_list == expected_left
        assert 10 == right.save.call_count
        assert right.save.call_args_list == expected_right

    def test_generator_node_tuple_with_map_unzip_outputs(
        self, mocker, monkeypatch, catalog
    ):
        """Generator nodes should stream even if unzip returns non-generator iterators.

        This mirrors ``more_itertools`` 8.14.0-10.6.0, where ``unzip`` returned
        ``map`` objects for multi-output generator nodes. The runner must detect
        streaming from the node function itself rather than the concrete output
        iterator type returned by ``unzip``.
        """
        left = mocker.Mock()
        right = mocker.Mock()

        def unzip_returning_maps(iterable):
            rows = tuple(iterable)
            return tuple(
                map(lambda row, index=index: row[index], rows)
                for index in range(len(rows[0]))
            )

        monkeypatch.setattr(node_module, "unzip", unzip_returning_maps)
        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        n = node(generate_tuple, inputs=None, outputs=["left", "right"])
        SequentialRunner().run(Pipeline([n]), catalog, _NullPluginManager())

        expected_left = [((i,),) for i in range(10)]
        expected_right = [((i * i,),) for i in range(10)]
        assert left.save.call_count == 10
        assert left.save.call_args_list == expected_left
        assert right.save.call_count == 10
        assert right.save.call_args_list == expected_right


class _IterableNotGenerator:
    """Satisfies ``collections.abc.Iterator`` without being a Python generator.

    Stand-in for real-world objects that users routinely pass through Kedro
    nodes -- e.g. ``mne.Epochs`` and custom iterator-like domain objects --
    which implement ``__iter__``/``__next__`` but must be saved as a single
    opaque object rather than streamed chunk-by-chunk.
    """

    def __init__(self, label: str, size: int = 3):
        self.label = label
        self._size = size
        self._idx = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self._idx >= self._size:
            raise StopIteration
        self._idx += 1
        return f"{self.label}_chunk_{self._idx}"


class TestNonGeneratorIterables:
    """Regression tests for kedro-org/kedro#5412.

    The sequential runner used to treat any output that satisfied the
    ``Iterator`` ABC as a streaming generator-node output and iterate over it
    before saving, corrupting custom business objects. These tests pin the
    contract that only generator-function node outputs are streamed; every other
    iterable is passed to ``catalog.save`` unchanged.
    """

    def test_fake_iterable_is_iterator_but_not_generator(self):
        """Sanity check: our fixture reproduces the class of object
        (iterable + non-generator) that triggered the original bug."""
        obj = _IterableNotGenerator("x")
        assert isinstance(obj, Iterator)
        assert not inspect.isgenerator(obj)

    def test_single_iterable_output_is_passed_through(self, mocker, catalog):
        fake_dataset = mocker.Mock()
        mocker.patch.object(catalog, "get", return_value=fake_dataset)

        obj = _IterableNotGenerator("only")

        def produce_one():
            return obj

        n = node(produce_one, inputs=None, outputs="result")
        SequentialRunner().run(Pipeline([n]), catalog, _NullPluginManager())

        assert fake_dataset.save.call_count == 1
        (saved,), _ = fake_dataset.save.call_args
        assert saved is obj, "Runner must not iterate a non-generator output"

    def test_multiple_iterable_outputs_are_passed_through(self, mocker, catalog):
        """The original #5412 repro: two outputs, both iterable-but-not-
        generator, returned from a single node. Previously the runner's
        ``all(isinstance(d, Iterator) ...)`` check fired and ``interleave``
        pulled yielded chunks into ``catalog.save`` instead of the objects."""
        left = mocker.Mock()
        right = mocker.Mock()
        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        left_obj = _IterableNotGenerator("left")
        right_obj = _IterableNotGenerator("right")

        def produce_two():
            return left_obj, right_obj

        n = node(produce_two, inputs=None, outputs=["left", "right"])
        SequentialRunner().run(Pipeline([n]), catalog, _NullPluginManager())

        assert left.save.call_count == 1
        (saved_left,), _ = left.save.call_args
        assert saved_left is left_obj

        assert right.save.call_count == 1
        (saved_right,), _ = right.save.call_args
        assert saved_right is right_obj

    def test_dict_mapped_iterable_outputs_are_passed_through(self, mocker, catalog):
        """Explicit ``outputs={"a": "left", "b": "right"}`` mapping must also
        short-circuit the streaming path -- this is the exact configuration
        the #5412 reporter used to try to bypass tuple unpacking."""
        left = mocker.Mock()
        right = mocker.Mock()
        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        a_obj = _IterableNotGenerator("a")
        b_obj = _IterableNotGenerator("b")

        def produce_dict():
            return {"a": a_obj, "b": b_obj}

        n = node(produce_dict, inputs=None, outputs={"a": "left", "b": "right"})
        SequentialRunner().run(Pipeline([n]), catalog, _NullPluginManager())

        (saved_left,), _ = left.save.call_args
        (saved_right,), _ = right.save.call_args
        assert saved_left is a_obj
        assert saved_right is b_obj

    def test_numpy_array_outputs_are_passed_through(self, mocker, catalog):
        left = mocker.Mock()
        right = mocker.Mock()
        mocker.patch.object(
            catalog,
            "get",
            side_effect=lambda ds_name, **kwargs: left if ds_name == "left" else right,
        )

        left_array = np.array([1, 2, 3])
        right_array = np.array([4, 5, 6])

        def produce_arrays():
            return left_array, right_array

        n = node(produce_arrays, inputs=None, outputs=["left", "right"])
        SequentialRunner().run(Pipeline([n]), catalog, _NullPluginManager())

        assert left.save.call_count == 1
        (saved_left,), _ = left.save.call_args
        assert saved_left is left_array

        assert right.save.call_count == 1
        (saved_right,), _ = right.save.call_args
        assert saved_right is right_array
