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
"""``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort.
"""

from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from multiprocessing.managers import BaseManager, BaseProxy
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import Iterable

from kedro.io import AbstractDataSet, DataCatalog, MemoryDataSet
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.runner.runner import AbstractRunner, run_node


class ParallelRunnerManager(BaseManager):
    """``ParallelRunnerManager`` is used to create shared ``MemoryDataSet``
    objects as default data sets in a pipeline.
    """

    pass


ParallelRunnerManager.register("MemoryDataSet", MemoryDataSet)


class ParallelRunner(AbstractRunner):
    """``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in parallel groups formed by toposort.
    """

    def __init__(self):
        """Instantiates the runner by creating a Manager.
        """
        self._manager = ParallelRunnerManager()
        self._manager.start()

    def create_default_data_set(self, ds_name: str, max_loads: int) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set
            max_loads: Maximum number of times ``load`` method of the
                default data set is allowed to be invoked. Any number of
                calls is allowed if the argument is not set.

        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        # pylint: disable=no-member
        return self._manager.MemoryDataSet(max_loads=max_loads)

    @classmethod
    def _validate_nodes(cls, nodes: Iterable[Node]):
        """Ensure all tasks are serializable."""
        unserializable = []
        for node in nodes:
            try:
                ForkingPickler.dumps(node)
            except (AttributeError, PicklingError):
                unserializable.append(node)

        if unserializable:
            raise AttributeError(
                "The following nodes cannot be serialized: {}\nIn order to "
                "utilize multiprocessing you need to make sure all nodes are "
                "serializable, i.e. nodes should not include lambda "
                "functions, nested functions, closures, etc.\nIf you "
                "are using custom decorators ensure they are correctly using "
                "functools.wraps().".format(unserializable)
            )

    @classmethod
    def _validate_catalog(cls, catalog: DataCatalog, pipeline: Pipeline):
        """Ensure that all data sets are serializable and that we do not have
        any non proxied memory data sets being used as outputs as their content
        will not be synchronized across threads.
        """

        data_sets = catalog._data_sets  # pylint: disable=protected-access

        unserializable = []
        for name, data_set in data_sets.items():
            try:
                ForkingPickler.dumps(data_set)
            except (AttributeError, PicklingError):
                unserializable.append(name)

        if unserializable:
            raise AttributeError(
                "The following data_sets cannot be serialized: {}\nIn order "
                "to utilize multiprocessing you need to make sure all data "
                "sets are serializable, i.e. data sets should not make use of "
                "lambda functions, nested functions, closures etc.\nIf you "
                "are using custom decorators ensure they are correctly using "
                "functools.wraps().".format(unserializable)
            )

        memory_data_sets = []
        for name, data_set in data_sets.items():
            if (
                name in pipeline.all_outputs()
                and isinstance(data_set, MemoryDataSet)
                and not isinstance(data_set, BaseProxy)
            ):
                memory_data_sets.append(name)

        if memory_data_sets:
            raise AttributeError(
                "The following data sets are memory data sets: {}\n"
                "ParallelRunner does not support output to externally created "
                "MemoryDataSets".format(memory_data_sets)
            )

    def _run(self, pipeline: Pipeline, catalog: DataCatalog) -> None:
        """The abstract interface for running pipelines.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.

        Raises:
            AttributeError: when the provided pipeline is not suitable for
                parallel execution.

        """

        self._validate_catalog(catalog, pipeline)
        self._validate_nodes(pipeline.nodes)

        done_inputs = pipeline.inputs()
        todo_nodes = set(pipeline.nodes)
        futures = set()
        with ProcessPoolExecutor() as pool:
            while True:
                ready = {n for n in todo_nodes if set(n.inputs) <= done_inputs}
                todo_nodes -= ready
                for node in ready:
                    futures.add(pool.submit(run_node, node, catalog))
                if not futures:
                    assert not todo_nodes
                    break
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    done_inputs.update(future.result().outputs)
