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
"""``AbstractRunner`` is the base class for all ``Pipeline`` runner
implementations.
"""

import logging
from abc import ABC, abstractmethod
from concurrent.futures import ALL_COMPLETED, ThreadPoolExecutor, as_completed, wait
from typing import Any, Dict, Iterable

from kedro.framework.hooks import get_hook_manager
from kedro.io import AbstractDataSet, DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node


class AbstractRunner(ABC):
    """``AbstractRunner`` is the base class for all ``Pipeline`` runner
    implementations.
    """

    def __init__(self, is_async: bool = False):
        """Instantiates the runner classs.

            Args:
                is_async: If True, the node inputs and outputs are loaded and saved
                    asynchronously with threads. Defaults to False.

        """
        self._is_async = is_async

    @property
    def _logger(self):
        return logging.getLogger(self.__module__)

    def run(
        self, pipeline: Pipeline, catalog: DataCatalog, run_id: str = None
    ) -> Dict[str, Any]:
        """Run the ``Pipeline`` using the ``DataSet``s provided by ``catalog``
        and save results back to the same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            run_id: The id of the run.

        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be satisfied.

        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.

        """

        catalog = catalog.shallow_copy()

        unsatisfied = pipeline.inputs() - set(catalog.list())
        if unsatisfied:
            raise ValueError(
                "Pipeline input(s) {} not found in the "
                "DataCatalog".format(unsatisfied)
            )

        free_outputs = pipeline.outputs() - set(catalog.list())
        unregistered_ds = pipeline.data_sets() - set(catalog.list())
        for ds_name in unregistered_ds:
            catalog.add(ds_name, self.create_default_data_set(ds_name))

        if self._is_async:
            self._logger.info(
                "Asynchronous mode is enabled for loading and saving data"
            )
        self._run(pipeline, catalog, run_id)

        self._logger.info("Pipeline execution completed successfully.")

        return {ds_name: catalog.load(ds_name) for ds_name in free_outputs}

    def run_only_missing(
        self, pipeline: Pipeline, catalog: DataCatalog
    ) -> Dict[str, Any]:
        """Run only the missing outputs from the ``Pipeline`` using the
        ``DataSet``s provided by ``catalog`` and save results back to the same
        objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be satisfied.

        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.

        """
        free_outputs = pipeline.outputs() - set(catalog.list())
        missing = {ds for ds in catalog.list() if not catalog.exists(ds)}
        to_build = free_outputs | missing
        to_rerun = pipeline.only_nodes_with_outputs(*to_build) + pipeline.from_inputs(
            *to_build
        )

        # we also need any memory data sets that feed into that
        # including chains of memory data sets
        memory_sets = pipeline.data_sets() - set(catalog.list())
        output_to_memory = pipeline.only_nodes_with_outputs(*memory_sets)
        input_from_memory = to_rerun.inputs() & memory_sets
        to_rerun += output_to_memory.to_outputs(*input_from_memory)

        return self.run(to_rerun, catalog)

    @abstractmethod  # pragma: no cover
    def _run(
        self, pipeline: Pipeline, catalog: DataCatalog, run_id: str = None
    ) -> None:
        """The abstract interface for running pipelines, assuming that the
        inputs have already been checked and normalized by run().

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            run_id: The id of the run.

        """
        pass

    @abstractmethod  # pragma: no cover
    def create_default_data_set(self, ds_name: str) -> AbstractDataSet:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set

        Returns:
            An instance of an implementation of AbstractDataSet to be
            used for all unregistered data sets.

        """
        pass

    def _suggest_resume_scenario(
        self, pipeline: Pipeline, done_nodes: Iterable[Node]
    ) -> None:
        remaining_nodes = set(pipeline.nodes) - set(done_nodes)

        postfix = ""
        if done_nodes:
            node_names = (n.name for n in remaining_nodes)
            resume_p = pipeline.only_nodes(*node_names)

            start_p = resume_p.only_nodes_with_inputs(*resume_p.inputs())
            start_node_names = (n.name for n in start_p.nodes)
            postfix += '  --from-nodes "{}"'.format(",".join(start_node_names))

        self._logger.warning(
            "There are %d nodes that have not run.\n"
            "You can resume the pipeline run by adding the following "
            "argument to your previous command:\n%s",
            len(remaining_nodes),
            postfix,
        )


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


def _run_node_sequential(node: Node, catalog: DataCatalog, run_id: str = None) -> Node:
    inputs = {name: catalog.load(name) for name in node.inputs}
    hook_manager = get_hook_manager()
    is_async = False
    hook_manager.hook.before_node_run(  # pylint: disable=no-member
        node=node, catalog=catalog, inputs=inputs, is_async=is_async, run_id=run_id
    )
    try:
        outputs = node.run(inputs)
    except Exception as exc:
        hook_manager.hook.on_node_error(  # pylint: disable=no-member
            error=exc,
            node=node,
            catalog=catalog,
            inputs=inputs,
            is_async=is_async,
            run_id=run_id,
        )
        raise exc
    hook_manager.hook.after_node_run(  # pylint: disable=no-member
        node=node,
        catalog=catalog,
        inputs=inputs,
        outputs=outputs,
        is_async=is_async,
        run_id=run_id,
    )

    for name, data in outputs.items():
        catalog.save(name, data)
    return node


def _run_node_async(node: Node, catalog: DataCatalog, run_id: str = None) -> Node:
    with ThreadPoolExecutor() as pool:
        inputs = {
            name: pool.submit(catalog.load, name) for name in node.inputs
        }  # Python dict is thread-safe
        wait(inputs.values(), return_when=ALL_COMPLETED)
        inputs = {key: value.result() for key, value in inputs.items()}
        hook_manager = get_hook_manager()
        is_async = True
        hook_manager.hook.before_node_run(  # pylint: disable=no-member
            node=node, catalog=catalog, inputs=inputs, is_async=is_async, run_id=run_id
        )
        try:
            outputs = node.run(inputs)
        except Exception as exc:
            hook_manager.hook.on_node_error(  # pylint: disable=no-member
                error=exc,
                node=node,
                catalog=catalog,
                inputs=inputs,
                is_async=is_async,
                run_id=run_id,
            )
            raise exc
        hook_manager.hook.after_node_run(  # pylint: disable=no-member
            node=node,
            catalog=catalog,
            inputs=inputs,
            outputs=outputs,
            is_async=is_async,
            run_id=run_id,
        )

        save_futures = set()

        for name, data in outputs.items():
            save_futures.add(pool.submit(catalog.save, name, data))

        for future in as_completed(save_futures):
            exception = future.exception()
            if exception:
                raise exception
    return node
