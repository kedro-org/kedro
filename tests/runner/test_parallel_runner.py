# Copyright 2018-2019 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited (“QuantumBlack”) name and logo
# (either separately or in combination, “QuantumBlack Trademarks”) are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
#     or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=no-member

from multiprocessing import Manager
from multiprocessing.managers import BaseProxy
from typing import Any, Dict

import pytest

from kedro.io import (
    AbstractDataSet,
    DataCatalog,
    DataSetError,
    LambdaDataSet,
    MemoryDataSet,
)
from kedro.pipeline import Pipeline, node
from kedro.pipeline.decorators import log_time
from kedro.runner import ParallelRunner
from kedro.runner.parallel_runner import ParallelRunnerManager


def source():
    return "stuff"


def identity(arg):
    return arg


def sink(arg):  # pylint: disable=unused-argument
    pass


def fan_in(*args):
    return args


def exception_fn(arg):
    raise Exception("test exception")


def return_none(arg):
    arg = None
    return arg


@pytest.fixture
def catalog():
    return DataCatalog()


@pytest.fixture
def fan_out_fan_in():
    return Pipeline(
        [
            node(identity, "A", "B"),
            node(identity, "B", "C"),
            node(identity, "B", "D"),
            node(identity, "B", "E"),
            node(fan_in, ["C", "D", "E"], "Z"),
        ]
    )


class TestValidParallelRunner:
    def test_create_default_data_set(self):
        # data_set is a proxy to a dataset in another process.
        data_set = ParallelRunner().create_default_data_set("")
        assert isinstance(data_set, BaseProxy)

    def test_parallel_run(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ParallelRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)

    def test_memory_data_set_input(self, fan_out_fan_in):
        pipeline = Pipeline([fan_out_fan_in])
        catalog = DataCatalog({"A": MemoryDataSet("42")})
        result = ParallelRunner().run(pipeline, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == ("42", "42", "42")


class TestInvalidParallelRunner:
    def test_task_validation(self, fan_out_fan_in, catalog):
        """ParallelRunner cannot serialize the lambda function."""
        catalog.add_feed_dict(dict(A=42))
        pipeline = Pipeline([fan_out_fan_in, node(lambda x: x, "Z", "X")])
        with pytest.raises(AttributeError):
            ParallelRunner().run(pipeline, catalog)

    def test_task_exception(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(feed_dict=dict(A=42))
        pipeline = Pipeline([fan_out_fan_in, node(exception_fn, "Z", "X")])
        with pytest.raises(Exception, match="test exception"):
            ParallelRunner().run(pipeline, catalog)

    def test_memory_data_set_output(self, fan_out_fan_in):
        """ParallelRunner does not support output to externally
        created MemoryDataSets.
        """
        pipeline = Pipeline([fan_out_fan_in])
        catalog = DataCatalog({"C": MemoryDataSet()}, dict(A=42))
        with pytest.raises(AttributeError, match="['C']"):
            ParallelRunner().run(pipeline, catalog)

    def test_node_returning_none(self):
        pipeline = Pipeline([node(identity, "A", "B"), node(return_none, "B", "C")])
        catalog = DataCatalog({"A": MemoryDataSet("42")})
        pattern = "Saving `None` to a `DataSet` is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            ParallelRunner().run(pipeline, catalog)

    def test_data_set_not_serializable(self, fan_out_fan_in):
        """Data set A cannot be serializable because _load and _save are not
        defined in global scope.
        """

        def _load():
            return 0  # pragma: no cover

        def _save(arg):
            assert arg == 0  # pragma: no cover

        # Data set A cannot be serialized
        catalog = DataCatalog({"A": LambdaDataSet(load=_load, save=_save)})

        pipeline = Pipeline([fan_out_fan_in])
        with pytest.raises(AttributeError, match="['A']"):
            ParallelRunner().run(pipeline, catalog)


@log_time
def decorated_identity(*args, **kwargs):
    return identity(*args, **kwargs)


@pytest.fixture
def decorated_fan_out_fan_in():
    return Pipeline(
        [
            node(decorated_identity, "A", "B"),
            node(decorated_identity, "B", "C"),
            node(decorated_identity, "B", "D"),
            node(decorated_identity, "B", "E"),
            node(fan_in, ["C", "D", "E"], "Z"),
        ]
    )


class TestParallelRunnerDecorator:
    def test_decorate_pipeline(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ParallelRunner().run(fan_out_fan_in.decorate(log_time), catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)

    def test_decorated_nodes(self, decorated_fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ParallelRunner().run(decorated_fan_out_fan_in, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)


class LoggingDataSet(AbstractDataSet):
    def __init__(self, log, name, value=None):
        self.log = log
        self.name = name
        self.value = value

    def _load(self) -> Any:
        self.log["log"] += [("load", self.name)]
        return self.value

    def _save(self, data: Any) -> None:
        self.value = data

    def _release(self) -> None:
        self.log["log"] += [("release", self.name)]
        self.value = None

    def _describe(self) -> Dict[str, Any]:
        return {}


ParallelRunnerManager.register("LoggingDataSet", LoggingDataSet)


class TestParallelRunnerRelease:
    def test_dont_release_inputs_and_outputs(self):
        manager = ParallelRunnerManager()
        manager.start()
        log = Manager().dict(log=[])

        pipeline = Pipeline(
            [node(identity, "in", "middle"), node(identity, "middle", "out")]
        )
        catalog = DataCatalog(
            {
                "in": manager.LoggingDataSet(log, "in", "stuff"),
                "middle": manager.LoggingDataSet(log, "middle"),
                "out": manager.LoggingDataSet(log, "out"),
            }
        )
        ParallelRunner().run(pipeline, catalog)

        # we don't want to see release in or out in here
        assert log["log"] == [("load", "in"), ("load", "middle"), ("release", "middle")]

    def test_release_at_earliest_opportunity(self):
        manager = ParallelRunnerManager()
        manager.start()
        log = Manager().dict(log=[])

        pipeline = Pipeline(
            [
                node(source, None, "first"),
                node(identity, "first", "second"),
                node(sink, "second", None),
            ]
        )
        catalog = DataCatalog(
            {
                "first": manager.LoggingDataSet(log, "first"),
                "second": manager.LoggingDataSet(log, "second"),
            }
        )
        ParallelRunner().run(pipeline, catalog)

        # we want to see "release first" before "load second"
        assert log["log"] == [
            ("load", "first"),
            ("release", "first"),
            ("load", "second"),
            ("release", "second"),
        ]

    def test_count_multiple_loads(self):
        manager = ParallelRunnerManager()
        manager.start()
        log = Manager().dict(log=[])

        pipeline = Pipeline(
            [
                node(source, None, "dataset"),
                node(sink, "dataset", None, name="bob"),
                node(sink, "dataset", None, name="fred"),
            ]
        )
        catalog = DataCatalog({"dataset": manager.LoggingDataSet(log, "dataset")})
        ParallelRunner().run(pipeline, catalog)

        # we want to the release after both the loads
        assert log["log"] == [
            ("load", "dataset"),
            ("load", "dataset"),
            ("release", "dataset"),
        ]

    def test_release_transcoded(self):
        manager = ParallelRunnerManager()
        manager.start()
        log = Manager().dict(log=[])

        pipeline = Pipeline(
            [node(source, None, "ds@save"), node(sink, "ds@load", None)]
        )
        catalog = DataCatalog(
            {
                "ds@save": LoggingDataSet(log, "save"),
                "ds@load": LoggingDataSet(log, "load"),
            }
        )

        ParallelRunner().run(pipeline, catalog)

        # we want to see both datasets being released
        assert log["log"] == [
            ("release", "save"),
            ("load", "load"),
            ("release", "load"),
        ]
