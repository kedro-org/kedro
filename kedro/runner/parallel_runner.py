# FILE: kedro/runner/parallel_runner.py

from __future__ import annotations

import logging 
from concurrent.futures import Executor, ProcessPoolExecutor
from multiprocessing.managers import BaseProxy, SyncManager
from multiprocessing.reduction import ForkingPickler 
from pickle import PicklingError
from typing import TYPE_CHECKING, Any

from pluggy import PluginManager as PluggyPluginManager 

from kedro.framework.hooks.manager import _create_hook_manager, _NullPluginManager

from kedro.io import (
    CatalogProtocol,
    DatasetNotFoundError,
    MemoryDataset,
    SharedMemoryDataset,
)
from kedro.runner.runner import AbstractRunner 

if TYPE_CHECKING: # pragma: no cover
    from collections.abc import Iterable
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node


class ParallelRunnerManager(SyncManager):
    """``ParallelRunnerManager`` is used to create shared ``MemoryDataset``."""
ParallelRunnerManager.register("MemoryDataset", MemoryDataset)


class ParallelRunner(AbstractRunner):
    def __init__(
        self,
        max_workers: int | None = None,
        is_async: bool = False,
        extra_dataset_patterns: dict[str, dict[str, Any]] | None = None,
    ):
        default_dataset_pattern = {"{default}": {"type": "SharedMemoryDataset"}}
        self._extra_dataset_patterns = extra_dataset_patterns or default_dataset_pattern
        super().__init__(
            is_async=is_async, extra_dataset_patterns=self._extra_dataset_patterns
        )
        self._manager = ParallelRunnerManager()
        self._manager.start()
        self._max_workers = self._validate_max_workers(max_workers)
        self._subprocess_hook_manager: PluggyPluginManager | _NullPluginManager | None = None

    def __del__(self) -> None:
        if hasattr(self, "_manager") and self._manager:
            self._manager.shutdown()

    @classmethod
    def _validate_nodes(cls, nodes: Iterable[Node]) -> None:
        unserialisable = []
        for node in nodes:
            try: ForkingPickler.dumps(node)
            except (AttributeError, PicklingError): unserialisable.append(node)
        if unserialisable: raise AttributeError(f"Unserialisable nodes: {sorted(unserialisable)}")

    @classmethod
    def _validate_catalog(cls, catalog: CatalogProtocol, pipeline: Pipeline) -> None:
        datasets = getattr(catalog, "_datasets", {})
        unserialisable = []
        for name, dataset_obj in datasets.items():
            if getattr(dataset_obj, "_SINGLE_PROCESS", False): unserialisable.append(name); continue
            try: ForkingPickler.dumps(dataset_obj)
            except (AttributeError, PicklingError): unserialisable.append(name)
        if unserialisable: raise AttributeError(f"Unserialisable datasets: {sorted(unserialisable)}")
        
        memory_datasets = []
        for name, dataset_obj in datasets.items():
            if name in pipeline.all_outputs() and \
               isinstance(dataset_obj, MemoryDataset) and \
               not isinstance(dataset_obj, BaseProxy):
                memory_datasets.append(name)
        if memory_datasets: raise AttributeError(f"MemoryDatasets as outputs not supported: {sorted(memory_datasets)}")

    def _set_manager_datasets(self, catalog: CatalogProtocol, pipeline: Pipeline) -> None:
        for dataset_name in pipeline.datasets():
            try:
                if catalog.exists(dataset_name): 
                    dataset_obj = catalog._get_dataset(dataset_name) # type: ignore
                    if isinstance(dataset_obj, SharedMemoryDataset): dataset_obj.set_manager(self._manager)
            except DatasetNotFoundError: self._logger.debug(f"Dataset '{dataset_name}' not found for _set_manager_datasets.")
            except Exception as e: self._logger.error(f"Error for '{dataset_name}' in _set_manager_datasets: {e}")
        
        if hasattr(catalog, "_datasets"):
            for name, ds in getattr(catalog, "_datasets", {}).items():
                if isinstance(ds, SharedMemoryDataset):
                    try: ds.set_manager(self._manager)
                    except Exception as e: self._logger.error(f"Error setting manager for SharedMemoryDataset '{name}': {e}")

    def _get_required_workers_count(self, pipeline: Pipeline) -> int:
        return min(len(pipeline.nodes) - len(pipeline.grouped_nodes) + 1, self._max_workers)

    def _get_executor(self, max_workers: int) -> Executor:
        return ProcessPoolExecutor(max_workers=max_workers)

    def _prepare_subprocess_hook_manager(self, main_hook_manager: PluggyPluginManager) -> PluggyPluginManager | _NullPluginManager:
        if self._subprocess_hook_manager is not None:
            return self._subprocess_hook_manager

        picklable_hook_providers = []
        if hasattr(main_hook_manager.hook, "get_picklable_hook_implementations_for_subprocess"):
            results = main_hook_manager.hook.get_picklable_hook_implementations_for_subprocess()
            for provider_iterable in results:
                if provider_iterable:
                    picklable_hook_providers.extend(provider_iterable)
        
        if not picklable_hook_providers:
            self._logger.info("No picklable hook implementations provided by plugins for subprocesses. Using NullPluginManager.")
            self._subprocess_hook_manager = _NullPluginManager()
            return self._subprocess_hook_manager

        child_manager = _create_hook_manager(enable_tracing=False) 

        registered_count = 0
        for provider_instance in picklable_hook_providers:
            try:
                ForkingPickler.dumps(provider_instance) 
                if not child_manager.is_registered(provider_instance):
                    child_manager.register(provider_instance)
                    registered_count +=1
                    self._logger.debug(f"Registered picklable hook provider '{type(provider_instance).__name__}' for subprocess.")
            except PicklingError: # pragma: no cover
                self._logger.warning(f"Hook provider '{type(provider_instance).__name__}' NOT picklable, SKIPPED.")
            except Exception as e: # pragma: no cover
                 self._logger.error(f"Failed to register picklable hook provider '{type(provider_instance).__name__}': {e}")
        
        if registered_count > 0:
             self._logger.info(f"Successfully registered {registered_count} picklable hook(s) for subprocesses.")
             try:
                 ForkingPickler.dumps(child_manager) 
                 self._logger.info("Subprocess hook manager IS picklable after registration.")
             except Exception as e: # pragma: no cover
                 self._logger.error(
                     f"Subprocess hook manager IS NOT picklable after registration: {e}. "
                     "Falling back to NullPluginManager for subprocesses."
                 )
                 child_manager = _NullPluginManager()
        else:
            self._logger.info("No picklable hooks were ultimately registered. Using NullPluginManager for subprocesses.")
            child_manager = _NullPluginManager()
        
        self._subprocess_hook_manager = child_manager
        return self._subprocess_hook_manager

    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluggyPluginManager | None = None, 
        session_id: str | None = None,
    ) -> None:
        if not self._is_async:
            self._logger.info("Using synchronous mode for loading and saving data...")

        if hasattr(self, "_set_manager_datasets"):
            self._logger.debug("ParallelRunner: Calling _set_manager_datasets.")
            self._set_manager_datasets(catalog, pipeline)

        subprocess_hook_manager_to_use: PluggyPluginManager | _NullPluginManager
        if hook_manager: 
            if hasattr(hook_manager.hook, "on_parallel_runner_start"):
                self._logger.info("ParallelRunner: Calling `on_parallel_runner_start` hook.")
                try:
                    hook_manager.hook.on_parallel_runner_start(manager=self._manager, catalog=catalog)
                except Exception as e: # pragma: no cover
                    self._logger.error(f"ParallelRunner: Error during `on_parallel_runner_start`: {e}", exc_info=True)
            
            subprocess_hook_manager_to_use = self._prepare_subprocess_hook_manager(hook_manager)
        else: # pragma: no cover
            self._logger.info("ParallelRunner: No main hook manager provided; using NullPluginManager for subprocesses.")
            subprocess_hook_manager_to_use = _NullPluginManager()
        
        super()._run(
            pipeline=pipeline,
            catalog=catalog,
            hook_manager=subprocess_hook_manager_to_use, 
            session_id=session_id,
        )

        if not pipeline.nodes: # pragma: no cover
            self._logger.info("ParallelRunner: Pipeline is empty (after super()._run call).")
