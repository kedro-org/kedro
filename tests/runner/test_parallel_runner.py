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

from multiprocessing.managers import BaseProxy

import pytest

from kedro.io import DataCatalog, DataSetError, LambdaDataSet, MemoryDataSet
from kedro.pipeline import Pipeline, node
from kedro.pipeline.decorators import log_time
from kedro.runner import ParallelRunner


def identity(input1: str):
    return input1  # pragma: no cover


def fan_in(*args):
    return args


def exception_fn(arg):
    raise Exception("test exception")


def null(arg):
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
        pipeline = Pipeline([node(identity, "A", "B"), node(null, "B", "C")])
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
