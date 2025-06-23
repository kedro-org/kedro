"""``ThreadRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort
using threads.
"""

from __future__ import annotations

import warnings
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

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
        extra_dataset_patterns: dict[str, dict[str, Any]] | None = None,
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
            extra_dataset_patterns: Extra dataset factory patterns to be added to the catalog
                during the run. This is used to set the default datasets to MemoryDataset
                for `ThreadRunner`.

        Raises:
            ValueError: bad parameters passed
        """
        if is_async:
            warnings.warn(
                "'ThreadRunner' doesn't support loading and saving the "
                "node inputs and outputs asynchronously with threads. "
                "Setting 'is_async' to False."
            )
        default_dataset_pattern = {"{default}": {"type": "MemoryDataset"}}
        self._extra_dataset_patterns = extra_dataset_patterns or default_dataset_pattern
        super().__init__(
            is_async=False, extra_dataset_patterns=self._extra_dataset_patterns
        )

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
        session_id: str | None = None,
    ) -> None:
        """The method implementing threaded pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            Exception: in case of any downstream node failure.

        """
        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=hook_manager,
            session_id=session_id,
        )
