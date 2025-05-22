"""``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort.
"""

from __future__ import annotations

import logging
from concurrent.futures import Executor, ProcessPoolExecutor
from multiprocessing.managers import BaseProxy, SyncManager
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import TYPE_CHECKING, Any

from pluggy import PluginManager

from kedro.framework.hooks.manager import _NullPluginManager, _create_hook_manager
from kedro.io import (
    CatalogProtocol,
    DatasetNotFoundError,
    MemoryDataset,
    SharedMemoryDataset,
)
from kedro.runner.runner import AbstractRunner

if TYPE_CHECKING:
    from collections.abc import Iterable

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
        self._subprocess_hook_manager: PluginManager | _NullPluginManager | None = None

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
        for name, dataset in datasets.items():
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
                    dataset = catalog._get_dataset(dataset_name)
                    if isinstance(dataset, SharedMemoryDataset):
                        dataset.set_manager(self._manager)
            except DatasetNotFoundError:
                self._logger.debug(
                    f"Dataset '{dataset_name}' not found for _set_manager_datasets."
                )
            except Exception as e:
                self._logger.error(
                    f"Error for '{dataset_name}' in _set_manager_datasets: {e}"
                )

        # Also process datasets already in the catalog
        if hasattr(catalog, "_datasets"):
            for name, dataset in getattr(catalog, "_datasets", {}).items():
                if isinstance(dataset, SharedMemoryDataset):
                    try:
                        dataset.set_manager(self._manager)
                    except Exception as e:
                        self._logger.error(
                            f"Error setting manager for SharedMemoryDataset '{name}': {e}"
                        )

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

    def _prepare_subprocess_hook_manager(
        self, main_hook_manager: PluginManager
    ) -> PluginManager | _NullPluginManager:
        """Prepare a hook manager for subprocesses by collecting picklable hook
        implementations from the main process hooks."""
        if self._subprocess_hook_manager is not None:
            return self._subprocess_hook_manager

        picklable_hook_providers = []
        if hasattr(main_hook_manager.hook, "get_picklable_hook_implementations_for_subprocess"):
            results = main_hook_manager.hook.get_picklable_hook_implementations_for_subprocess()
            for provider_iterable in results:
                if provider_iterable:
                    picklable_hook_providers.extend(provider_iterable)

        if not picklable_hook_providers:
            self._logger.info(
                "No picklable hook implementations provided by plugins for subprocesses. "
                "Using NullPluginManager."
            )
            self._subprocess_hook_manager = _NullPluginManager()
            return self._subprocess_hook_manager

        # Create a new hook manager for subprocesses without tracing
        # to ensure it can be pickled
        child_manager = _create_hook_manager(enable_tracing=False)

        registered_count = 0
        for provider_instance in picklable_hook_providers:
            try:
                ForkingPickler.dumps(provider_instance)
                if not child_manager.is_registered(provider_instance):
                    child_manager.register(provider_instance)
                    registered_count += 1
                    self._logger.debug(
                        f"Registered picklable hook provider "
                        f"'{type(provider_instance).__name__}' for subprocess."
                    )
            except PicklingError:
                self._logger.warning(
                    f"Hook provider '{type(provider_instance).__name__}' "
                    f"is not picklable, skipping."
                )
            except Exception as e:
                self._logger.error(
                    f"Failed to register picklable hook provider "
                    f"'{type(provider_instance).__name__}': {e}"
                )

        if registered_count > 0:
            self._logger.info(
                f"Successfully registered {registered_count} picklable hook(s) "
                f"for subprocesses."
            )
            # Verify the child manager is picklable
            try:
                ForkingPickler.dumps(child_manager)
            except Exception as e:
                self._logger.error(
                    f"Subprocess hook manager is not picklable after registration: {e}. "
                    f"Falling back to NullPluginManager for subprocesses."
                )
                child_manager = _NullPluginManager()
        else:
            self._logger.info(
                "No picklable hooks were registered. Using NullPluginManager for subprocesses."
            )
            child_manager = _NullPluginManager()

        self._subprocess_hook_manager = child_manager
        return self._subprocess_hook_manager

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
            self._logger.info(
                "Using synchronous mode for loading and saving data. Use the --async flag "
                "for potential performance gains. https://docs.kedro.org/en/stable/nodes_and_pipelines/run_a_pipeline.html#load-and-save-asynchronously"
            )

        self._set_manager_datasets(catalog, pipeline)

        subprocess_hook_manager_to_use: PluginManager | _NullPluginManager
        if hook_manager:
            # Call the new hook to allow plugins to prepare for parallel execution
            if hasattr(hook_manager.hook, "on_parallel_runner_start"):
                self._logger.info("Calling `on_parallel_runner_start` hook.")
                try:
                    hook_manager.hook.on_parallel_runner_start(
                        manager=self._manager, catalog=catalog
                    )
                except Exception as e:
                    self._logger.error(
                        f"Error during `on_parallel_runner_start`: {e}", exc_info=True
                    )

            subprocess_hook_manager_to_use = self._prepare_subprocess_hook_manager(
                hook_manager
            )
        else:
            self._logger.info(
                "No main hook manager provided; using NullPluginManager for subprocesses."
            )
            subprocess_hook_manager_to_use = _NullPluginManager()

        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=subprocess_hook_manager_to_use,
            session_id=session_id,
        )
