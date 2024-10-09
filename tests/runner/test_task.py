import pytest

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.pipeline import node
from kedro.runner import Task


def generate_one():
    yield from range(10)


class TestTask:
    def test_generator_fail_async(self, mocker, catalog):
        fake_dataset = mocker.Mock()
        catalog.add("result", fake_dataset)
        n = node(generate_one, inputs=None, outputs="result")

        with pytest.raises(Exception, match="nodes wrapping generator functions"):
            task = Task(n, catalog, _NullPluginManager(), is_async=True)
            task.execute()
