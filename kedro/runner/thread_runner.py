"""``ThreadRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort
using threads.
"""
from __future__ import annotations

import warnings
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from itertools import chain

from pluggy import PluginManager

from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.runner.runner import AbstractRunner, run_node


class ThreadRunner(AbstractRunner):
    """``ThreadRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in parallel groups formed by toposort
    using threads.
    """

    def __init__(self, max_workers: int = None, is_async: bool = False):
        """
        Instantiates the runner.

        Args:
            max_workers: Number of worker processes to spawn. If not set,
                calculated automatically based on the pipeline configuration
                and CPU core count.
            is_async: If True, set to False, because `ThreadRunner`
                doesn't support loading and saving the node inputs and
                outputs asynchronously with threads. Defaults to False.

        Raises:
            ValueError: bad parameters passed
        """
        if is_async:
            warnings.warn(
                "'ThreadRunner' doesn't support loading and saving the "
                "node inputs and outputs asynchronously with threads. "
                "Setting 'is_async' to False."
            )
        super().__init__(is_async=False)

        if max_workers is not None and max_workers <= 0:
            raise ValueError("max_workers should be positive")

        self._max_workers = max_workers

    def create_default_dataset(self, ds_name: str) -> MemoryDataset:  # type: ignore
        """Factory method for creating the default dataset for the runner.

        Args:
            ds_name: Name of the missing dataset.

        Returns:
            An instance of ``MemoryDataset`` to be used for all
            unregistered datasets.

        """
        return MemoryDataset()

    def _get_required_workers_count(self, pipeline: Pipeline):
        """
        Calculate the max number of processes required for the pipeline
        """
        # Number of nodes is a safe upper-bound estimate.
        # It's also safe to reduce it by the number of layers minus one,
        # because each layer means some nodes depend on other nodes
        # and they can not run in parallel.
        # It might be not a perfect solution, but good enough and simple.
        required_threads = len(pipeline.nodes) - len(pipeline.grouped_nodes) + 1

        return (
            min(required_threads, self._max_workers)
            if self._max_workers
            else required_threads
        )

    def _run(  # noqa: too-many-locals,useless-suppression
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager,
        session_id: str = None,
    ) -> None:
        """The abstract interface for running pipelines.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            Exception: in case of any downstream node failure.

        """
        nodes = pipeline.nodes
        load_counts = Counter(chain.from_iterable(n.inputs for n in nodes))
        node_dependencies = pipeline.node_dependencies
        todo_nodes = set(node_dependencies.keys())
        done_nodes: set[Node] = set()
        futures = set()
        done = None
        max_workers = self._get_required_workers_count(pipeline)

        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            while True:
                ready = {n for n in todo_nodes if node_dependencies[n] <= done_nodes}
                todo_nodes -= ready
                for node in ready:
                    futures.add(
                        pool.submit(
                            run_node,
                            node,
                            catalog,
                            hook_manager,
                            self._is_async,
                            session_id,
                        )
                    )
                if not futures:
                    assert not todo_nodes, (todo_nodes, done_nodes, ready, done)
                    break
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    try:
                        node = future.result()
                    except Exception:
                        self._suggest_resume_scenario(pipeline, done_nodes, catalog)
                        raise
                    done_nodes.add(node)
                    self._logger.info("Completed node: %s", node.name)
                    self._logger.info(
                        "Completed %d out of %d tasks", len(done_nodes), len(nodes)
                    )

                    # Decrement load counts, and release any datasets we
                    # have finished with.
                    for dataset in node.inputs:
                        load_counts[dataset] -= 1
                        if (
                            load_counts[dataset] < 1
                            and dataset not in pipeline.inputs()
                        ):
                            catalog.release(dataset)
                    for dataset in node.outputs:
                        if (
                            load_counts[dataset] < 1
                            and dataset not in pipeline.outputs()
                        ):
                            catalog.release(dataset)
