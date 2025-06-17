from kedro.framework.hooks.manager import _NullPluginManager
from kedro.pipeline import Pipeline, node
from kedro.runner import SequentialRunner

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
            side_effect=lambda ds_name: left if ds_name == "left" else right,
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
            side_effect=lambda ds_name: left if ds_name == "left" else right,
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
            side_effect=lambda ds_name: left if ds_name == "left" else right,
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
