"""``ThreadRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort
using threads.
"""

from __future__ import annotations

import warnings
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import TYPE_CHECKING

from kedro.runner.runner import AbstractRunner

if TYPE_CHECKING:
    from pluggy import PluginManager

    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline


class ThreadRunner(AbstractRunner):
    """``ThreadRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in parallel groups formed by toposort
    using threads.
    """

    def __init__(
        self,
        max_workers: int | None = None,
        is_async: bool = False,
    ):
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

        self._max_workers = self._validate_max_workers(max_workers)

    def _get_required_workers_count(self, pipeline: Pipeline) -> int:
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

    def _get_executor(self, max_workers: int) -> Executor:
        return ThreadPoolExecutor(max_workers=max_workers)

    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
    ) -> None:
        """The method implementing threaded pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            run_id: The id of the run.

        Raises:
            Exception: in case of any downstream node failure.

        """
        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=hook_manager,
            run_id=run_id,
        )
