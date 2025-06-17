"""``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort.
"""

from __future__ import annotations

import os
from concurrent.futures import Executor, ProcessPoolExecutor
from multiprocessing import get_context
from multiprocessing.managers import SyncManager
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import TYPE_CHECKING

from kedro.io import (
    MemoryDataset,
)
from kedro.runner.runner import AbstractRunner

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pluggy import PluginManager

    from kedro.io import SharedMemoryCatalogProtocol
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node


class ParallelRunnerManager(SyncManager):
    """``ParallelRunnerManager`` is used to create shared ``MemoryDataset``
    objects as default datasets in a pipeline.
    """


ParallelRunnerManager.register("MemoryDataset", MemoryDataset)


class ParallelRunner(AbstractRunner):
    """``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in parallel groups formed by toposort.
    Please note that this `runner` implementation validates dataset using the
    ``_validate_catalog`` method, which checks if any of the datasets are
    single process only using the `_SINGLE_PROCESS` dataset attribute.
    """

    def __init__(
        self,
        max_workers: int | None = None,
        is_async: bool = False,
    ):
        """
        Instantiates the runner by creating a Manager.

        Args:
            max_workers: Number of worker processes to spawn. If not set,
                calculated automatically based on the pipeline configuration
                and CPU core count. On windows machines, the max_workers value
                cannot be larger than 61 and will be set to min(61, max_workers).
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
        Raises:
            ValueError: bad parameters passed
        """
        super().__init__(is_async=is_async)
        self._manager = ParallelRunnerManager()
        self._manager.start()

        self._max_workers = self._validate_max_workers(max_workers)

    def __del__(self) -> None:
        self._manager.shutdown()

    @classmethod
    def _validate_nodes(cls, nodes: Iterable[Node]) -> None:
        """Ensure all tasks are serialisable."""
        unserialisable = []
        for node in nodes:
            try:
                ForkingPickler.dumps(node)
            except (AttributeError, PicklingError):
                unserialisable.append(node)

        if unserialisable:
            raise AttributeError(
                f"The following nodes cannot be serialised: {sorted(unserialisable)}\n"
                f"In order to utilize multiprocessing you need to make sure all nodes "
                f"are serialisable, i.e. nodes should not include lambda "
                f"functions, nested functions, closures, etc.\nIf you "
                f"are using custom decorators ensure they are correctly decorated using "
                f"functools.wraps()."
            )

    @classmethod
    def _validate_catalog(cls, catalog: SharedMemoryCatalogProtocol) -> None:  # type: ignore[override]
        """Ensure that all datasets are serialisable and that we do not have
        any non proxied memory datasets being used as outputs as their content
        will not be synchronized across threads.
        """
        catalog.validate_catalog()

    def _set_manager_datasets(self, catalog: SharedMemoryCatalogProtocol) -> None:  # type: ignore[override]
        catalog.set_manager_datasets(self._manager)

    def _get_required_workers_count(self, pipeline: Pipeline) -> int:
        """
        Calculate the max number of processes required for the pipeline,
        limit to the number of CPU cores.
        """
        # Number of nodes is a safe upper-bound estimate.
        # It's also safe to reduce it by the number of layers minus one,
        # because each layer means some nodes depend on other nodes
        # and they can not run in parallel.
        # It might be not a perfect solution, but good enough and simple.
        required_processes = len(pipeline.nodes) - len(pipeline.grouped_nodes) + 1

        return min(required_processes, self._max_workers)

    def _get_executor(self, max_workers: int) -> Executor:
        context = os.environ.get("KEDRO_MP_CONTEXT")
        if context and context not in {"fork", "spawn"}:
            context = None
        ctx = get_context(context)
        return ProcessPoolExecutor(max_workers=max_workers, mp_context=ctx)

    def _run(
        self,
        pipeline: Pipeline,
        catalog: SharedMemoryCatalogProtocol,  # type: ignore[override]
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
    ) -> None:
        """The method implementing parallel pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``SharedMemoryCatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            run_id: The id of the run.

        Raises:
            AttributeError: When the provided pipeline is not suitable for
                parallel execution.
            RuntimeError: If the runner is unable to schedule the execution of
                all pipeline nodes.
            Exception: In case of any downstream node failure.

        """
        if not self._is_async:
            self._logger.info(
                "Using synchronous mode for loading and saving data. Use the --async flag "
                "for potential performance gains. https://docs.kedro.org/en/stable/nodes_and_pipelines/run_a_pipeline.html#load-and-save-asynchronously"
            )

        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            run_id=run_id,
        )
