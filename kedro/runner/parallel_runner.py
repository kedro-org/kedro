"""``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort.
"""

from __future__ import annotations

from concurrent.futures import Executor, ProcessPoolExecutor
from multiprocessing.managers import BaseProxy, SyncManager
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import TYPE_CHECKING, Any

from kedro.io import (
    CatalogProtocol,
    DatasetNotFoundError,
    MemoryDataset,
    SharedMemoryDataset,
)
from kedro.runner.runner import AbstractRunner

if TYPE_CHECKING:
    from collections.abc import Iterable

    from pluggy import PluginManager

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
        extra_dataset_patterns: dict[str, dict[str, Any]] | None = None,
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
            extra_dataset_patterns: Extra dataset factory patterns to be added to the catalog
                during the run. This is used to set the default datasets to SharedMemoryDataset
                for `ParallelRunner`.

        Raises:
            ValueError: bad parameters passed
        """
        default_dataset_pattern = {"{default}": {"type": "SharedMemoryDataset"}}
        self._extra_dataset_patterns = extra_dataset_patterns or default_dataset_pattern
        super().__init__(
            is_async=is_async, extra_dataset_patterns=self._extra_dataset_patterns
        )
        self._manager = ParallelRunnerManager()
        self._manager.start()

        self._max_workers = self._validate_max_workers(max_workers)

    def __del__(self) -> None:
        if hasattr(self, "_manager") and self._manager:
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
    def _validate_catalog(cls, catalog: CatalogProtocol, pipeline: Pipeline) -> None:
        """Ensure that all datasets are serialisable and that we do not have
        any non proxied memory datasets being used as outputs as their content
        will not be synchronized across threads.
        """
        datasets = getattr(catalog, "_datasets", {})
        unserialisable = []
        for name, dataset in datasets.items(): # type: ignore
            if getattr(dataset, "_SINGLE_PROCESS", False):  # SKIP_IF_NO_SPARK
                unserialisable.append(name)
                continue
            try:
                ForkingPickler.dumps(dataset)
            except (AttributeError, PicklingError):
                unserialisable.append(name)

        if unserialisable:
            raise AttributeError(
                f"The following datasets cannot be used with multiprocessing: "
                f"{sorted(unserialisable)}\nIn order to utilize multiprocessing you "
                f"need to make sure all datasets are serialisable, i.e. datasets "
                f"should not make use of lambda functions, nested functions, closures "
                f"etc.\nIf you are using custom decorators ensure they are correctly "
                f"decorated using functools.wraps()."
            )

        memory_datasets = []
        for name, dataset in datasets.items():
            if (
                name in pipeline.all_outputs()
                and isinstance(dataset, MemoryDataset)
                and not isinstance(dataset, BaseProxy)
            ):
                memory_datasets.append(name)

        if memory_datasets:
            raise AttributeError(
                f"The following datasets are memory datasets: "
                f"{sorted(memory_datasets)}\n"
                f"ParallelRunner does not support output to externally created "
                f"MemoryDatasets"
            )

    def _set_manager_datasets(
        self, catalog: CatalogProtocol, pipeline: Pipeline
    ) -> None:
        for dataset_name in pipeline.datasets():
            try:
                if catalog.exists(dataset_name): 
                    dataset_obj = catalog._get_dataset(dataset_name) # type: ignore
                    if isinstance(dataset_obj, SharedMemoryDataset):
                        dataset_obj.set_manager(self._manager)
            except DatasetNotFoundError:
                self._logger.debug(f"Dataset '{dataset_name}' not found for _set_manager_datasets.")
            except Exception as e:
                self._logger.error(f"Error processing '{dataset_name}' in _set_manager_datasets: {e}")

        if hasattr(catalog, "_datasets"):
            for name, ds in getattr(catalog, "_datasets", {}).items():
                if isinstance(ds, SharedMemoryDataset):
                    try:
                        ds.set_manager(self._manager)
                    except Exception as e: # pragma: no cover
                        self._logger.error(f"Error setting manager for SharedMemoryDataset '{name}': {e}")

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
        return ProcessPoolExecutor(max_workers=max_workers)

    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
    ) -> None:
        """The method implementing parallel pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            AttributeError: When the provided pipeline is not suitable for
                parallel execution.
            RuntimeError: If the runner is unable to schedule the execution of
                all pipeline nodes.
            Exception: In case of any downstream node failure.

        """
        if not self._is_async:
            self._logger.info("Using synchronous mode for loading and saving data...")

        if hasattr(self, "_set_manager_datasets"):
            self._logger.debug("ParallelRunner: Calling _set_manager_datasets.")
            self._set_manager_datasets(catalog, pipeline)

        if hook_manager: 
            if hasattr(hook_manager.hook, "on_parallel_runner_start"):
                self._logger.info("ParallelRunner: Calling `on_parallel_runner_start` hook.")
                try:
                    hook_manager.hook.on_parallel_runner_start(manager=self._manager)
                except Exception as e: # pragma: no cover
                    self._logger.error(f"ParallelRunner: Error during `on_parallel_runner_start`: {e}", exc_info=True)
            else: # pragma: no cover
                 self._logger.warning("ParallelRunner: `on_parallel_runner_start` hook spec not found in hook_manager.")

        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=None,
            session_id=session_id,
        )

        if not pipeline.nodes: # pragma: no cover
            self._logger.info("ParallelRunner: Pipeline is empty, nothing to run (after super()._run call).")
