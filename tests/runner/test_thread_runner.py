# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=no-member
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict

import pytest

from kedro.io import AbstractDataSet, DataCatalog, DataSetError, MemoryDataSet
from kedro.pipeline import Pipeline, node
from kedro.pipeline.decorators import log_time
from kedro.runner import ThreadRunner


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


class TestValidThreadRunner:
    def test_create_default_data_set(self):
        data_set = ThreadRunner().create_default_data_set("")
        assert isinstance(data_set, MemoryDataSet)

    def test_thread_run(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ThreadRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert result["Z"] == (42, 42, 42)

    def test_memory_data_set_input(self, fan_out_fan_in):
        catalog = DataCatalog({"A": MemoryDataSet("42")})
        result = ThreadRunner().run(fan_out_fan_in, catalog)
        assert "Z" in result
        assert result["Z"] == ("42", "42", "42")


class TestMaxWorkers:
    @pytest.mark.parametrize(
        "user_specified_number, expected_number",
        [
            # The pipeline only needs 3 threads, no need for more
            (6, 3),
            (None, 3),
        ],
    )
    def test_specified_max_workers(
        self, mocker, fan_out_fan_in, catalog, user_specified_number, expected_number,
    ):  # pylint: disable=too-many-arguments
        """
        We initialize the runner with max_workers=4.
        `fan_out_fan_in` pipeline needs 3 threads.
        A pool with 3 workers should be used.
        """
        executor_cls_mock = mocker.patch(
            "kedro.runner.thread_runner.ThreadPoolExecutor", wraps=ThreadPoolExecutor,
        )

        catalog.add_feed_dict(dict(A=42))
        result = ThreadRunner(max_workers=user_specified_number).run(
            fan_out_fan_in, catalog
        )
        assert result == {"Z": (42, 42, 42)}

        executor_cls_mock.assert_called_once_with(max_workers=expected_number)

    def test_init_with_negative_process_count(self):
        pattern = "max_workers should be positive"
        with pytest.raises(ValueError, match=pattern):
            ThreadRunner(max_workers=-1)


class TestInvalidThreadRunner:
    def test_task_exception(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(feed_dict=dict(A=42))
        pipeline = Pipeline([fan_out_fan_in, node(exception_fn, "Z", "X")])
        with pytest.raises(Exception, match="test exception"):
            ThreadRunner().run(pipeline, catalog)

    def test_node_returning_none(self):
        pipeline = Pipeline([node(identity, "A", "B"), node(return_none, "B", "C")])
        catalog = DataCatalog({"A": MemoryDataSet("42")})
        pattern = "Saving `None` to a `DataSet` is not allowed"
        with pytest.raises(DataSetError, match=pattern):
            ThreadRunner().run(pipeline, catalog)


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


class TestThreadRunnerDecorator:
    def test_decorate_pipeline(self, fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ThreadRunner().run(fan_out_fan_in.decorate(log_time), catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)

    def test_decorated_nodes(self, decorated_fan_out_fan_in, catalog):
        catalog.add_feed_dict(dict(A=42))
        result = ThreadRunner().run(decorated_fan_out_fan_in, catalog)
        assert "Z" in result
        assert len(result["Z"]) == 3
        assert result["Z"] == (42, 42, 42)


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


class TestThreadRunnerRelease:
    def test_dont_release_inputs_and_outputs(self):
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
        ThreadRunner().run(pipeline, catalog)

        # we don't want to see release in or out in here
        assert list(log) == [("load", "in"), ("load", "middle"), ("release", "middle")]

    def test_release_at_earliest_opportunity(self):
        runner = ThreadRunner()
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
        runner.run(pipeline, catalog)

        # we want to see "release first" before "load second"
        assert list(log) == [
            ("load", "first"),
            ("release", "first"),
            ("load", "second"),
            ("release", "second"),
        ]

    def test_count_multiple_loads(self):
        runner = ThreadRunner()
        log = []

        pipeline = Pipeline(
            [
                node(source, None, "dataset"),
                node(sink, "dataset", None, name="bob"),
                node(sink, "dataset", None, name="fred"),
            ]
        )
        catalog = DataCatalog({"dataset": LoggingDataSet(log, "dataset")})
        runner.run(pipeline, catalog)

        # we want to the release after both the loads
        assert list(log) == [
            ("load", "dataset"),
            ("load", "dataset"),
            ("release", "dataset"),
        ]

    def test_release_transcoded(self):
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

        ThreadRunner().run(pipeline, catalog)

        # we want to see both datasets being released
        assert list(log) == [("release", "save"), ("load", "load"), ("release", "load")]
