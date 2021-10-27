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
"""``AbstractExecutor`` is the base class for all ``Pipeline`` executor
implementations.
"""

from abc import ABC
from typing import Iterable

from kedro.io import DataCatalog
from kedro.pipeline.node import Node


class AbstractExecutor(ABC):
    """``AbstractExecutor`` is the base class for all ``Pipeline``
    executor implementations.
    """

    def __init__(self, nodes: Iterable[Node], is_async: bool = False):
        """Instantiates the executor class.

        Args:
            nodes: The iterable of nodes to execute.
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
        """
        self._nodes = nodes
        self._is_async = is_async

    def run_node(
        node: Node, catalog: DataCatalog, is_async: bool = False, run_id: str = None
    ) -> Node:
        """Run a single `Node` with inputs from and outputs to the `catalog`.

        Args:
            node: The ``Node`` to run.
            catalog: A ``DataCatalog`` containing the node's inputs and outputs.
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
            run_id: The id of the pipeline run

        Returns:
            The node argument.

        """
        if is_async:
            node = _run_node_async(node, catalog, run_id)
        else:
            node = _run_node_sequential(node, catalog, run_id)

        for name in node.confirms:
            catalog.confirm(name)
        return node

    @abc.abstractmethod
    def _run_node_sequential(node: Node, catalog: DataCatalog, run_id: str = None) -> Node:
        pass

    @abc.abstractmethod
    def _run_node_async(node: Node, catalog: DataCatalog, run_id: str = None) -> Node:
        pass
