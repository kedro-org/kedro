# Copyright 2021 QuantumBlack Visual Analytics Limited
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
"""``SequentialExecutor`` is an ``AbstractExecutor`` implementation. It
can be used to run the provided nodes in a sequential manner.
"""

from typing import Iterable

from kedro.io import AbstractDataSet, DataCatalog, MemoryDataSet
from kedro.pipeline.node import Node
from kedro.symphony.executor.executor import AbstractExecutor, run_node


class SequentialExecutor(AbstractExecutor):
    """``SequentialExecutor`` is an ``AbstractExecutor`` implementation.
    It can be used to run the provided nodes in a sequential manner.
    """

    def __init__(self, nodes: Iterable[Node], is_async: bool = False):
        """Instantiates the executor class.

        Args:
            nodes: The iterable of nodes to run.
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.

        """
        super().__init__(nodes, is_async=is_async)

    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set

        Returns:
            An instance of an implementation of AbstractDataSet to be used
            for all unregistered data sets.

        """
        return MemoryDataSet()

    def _run(
        self, nodes: Iterable[Node], catalog: DataCatalog, run_id: str = None
    ) -> None:
        """The method implementing sequential node running.

        Args:
            pipeline: The nodes to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            run_id: The id of the run.

        Raises:
            Exception: in case of any downstream node failure.
        """
        for exec_index, node in enumerate(nodes):
            run_node(node, catalog, self._is_async, run_id)

            self._logger.debug(
                "Completed %d out of %d tasks", exec_index + 1, len(nodes)
            )
