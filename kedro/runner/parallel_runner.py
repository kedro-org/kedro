"""``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
be used to run the ``Pipeline`` in parallel groups formed by toposort.
"""
from __future__ import annotations

import multiprocessing
import os
import pickle
import sys
from collections import Counter
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from itertools import chain
from multiprocessing.managers import BaseProxy, SyncManager  # type: ignore
from multiprocessing.reduction import ForkingPickler
from pickle import PicklingError
from typing import Any, Iterable

from pluggy import PluginManager

from kedro.framework.hooks.manager import (
    _create_hook_manager,
    _register_hooks,
    _register_hooks_entry_points,
)
from kedro.framework.project import settings
from kedro.io import DataCatalog, DatasetError, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.runner.runner import AbstractRunner, run_node

# see https://github.com/python/cpython/blob/master/Lib/concurrent/futures/process.py#L114
_MAX_WINDOWS_WORKERS = 61


class _SharedMemoryDataset:
    """``_SharedMemoryDataset`` is a wrapper class for a shared MemoryDataset in SyncManager.
    It is not inherited from AbstractDataset class.
    """

    def __init__(self, manager: SyncManager):
        """Creates a new instance of ``_SharedMemoryDataset``,
        and creates shared memorydataset attribute.

        Args:
            manager: An instance of multiprocessing manager for shared objects.

        """
        self.shared_memory_dataset = manager.MemoryDataset()  # type: ignore

    def __getattr__(self, name):
        # This if condition prevents recursive call when deserialising
        if name == "__setstate__":
            raise AttributeError()
        return getattr(self.shared_memory_dataset, name)

    def save(self, data: Any):
        """Calls save method of a shared MemoryDataset in SyncManager."""
        try:
            self.shared_memory_dataset.save(data)
        except Exception as exc:
            # Checks if the error is due to serialisation or not
            try:
                pickle.dumps(data)
            except Exception as serialisation_exc:  # SKIP_IF_NO_SPARK
                raise DatasetError(
                    f"{str(data.__class__)} cannot be serialised. ParallelRunner "
                    "implicit memory datasets can only be used with serialisable data"
                ) from serialisation_exc
            raise exc


class ParallelRunnerManager(SyncManager):
    """``ParallelRunnerManager`` is used to create shared ``MemoryDataset``
    objects as default data sets in a pipeline.
    """


ParallelRunnerManager.register("MemoryDataset", MemoryDataset)  # noqa: no-member


def _bootstrap_subprocess(package_name: str, logging_config: dict[str, Any]):
    # noqa: import-outside-toplevel,cyclic-import
    from kedro.framework.project import configure_logging, configure_project

    configure_project(package_name)
    configure_logging(logging_config)


def _run_node_synchronization(  # noqa: too-many-arguments
    node: Node,
    catalog: DataCatalog,
    is_async: bool = False,
    session_id: str = None,
    package_name: str = None,
    logging_config: dict[str, Any] = None,
) -> Node:
    """Run a single `Node` with inputs from and outputs to the `catalog`.

    A ``PluginManager`` instance is created in each subprocess because the
    ``PluginManager`` can't be serialised.

    Args:
        node: The ``Node`` to run.
        catalog: A ``DataCatalog`` containing the node's inputs and outputs.
        is_async: If True, the node inputs and outputs are loaded and saved
            asynchronously with threads. Defaults to False.
        session_id: The session id of the pipeline run.
        package_name: The name of the project Python package.
        logging_config: A dictionary containing logging configuration.

    Returns:
        The node argument.

    """
    if multiprocessing.get_start_method() == "spawn" and package_name:
        _bootstrap_subprocess(package_name, logging_config)  # type: ignore

    hook_manager = _create_hook_manager()
    _register_hooks(hook_manager, settings.HOOKS)
    _register_hooks_entry_points(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)

    return run_node(node, catalog, hook_manager, is_async, session_id)


class ParallelRunner(AbstractRunner):
    """``ParallelRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in parallel groups formed by toposort.
    Please note that this `runner` implementation validates dataset using the
    ``_validate_catalog`` method, which checks if any of the datasets are
    single process only using the `_SINGLE_PROCESS` dataset attribute.
    """

    def __init__(self, max_workers: int = None, is_async: bool = False):
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
        self._manager.start()  # noqa: consider-using-with

        # This code comes from the concurrent.futures library
        # https://github.com/python/cpython/blob/master/Lib/concurrent/futures/process.py#L588
        if max_workers is None:
            # NOTE: `os.cpu_count` might return None in some weird cases.
            # https://github.com/python/cpython/blob/3.7/Modules/posixmodule.c#L11431
            max_workers = os.cpu_count() or 1
            if sys.platform == "win32":
                max_workers = min(_MAX_WINDOWS_WORKERS, max_workers)

        self._max_workers = max_workers

    def __del__(self):
        self._manager.shutdown()

    def create_default_dataset(  # type: ignore
        self, ds_name: str
    ) -> _SharedMemoryDataset:
        """Factory method for creating the default dataset for the runner.

        Args:
            ds_name: Name of the missing dataset.

        Returns:
            An instance of ``_SharedMemoryDataset`` to be used for all
            unregistered datasets.

        """
        return _SharedMemoryDataset(self._manager)

    @classmethod
    def _validate_nodes(cls, nodes: Iterable[Node]):
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
    def _validate_catalog(cls, catalog: DataCatalog, pipeline: Pipeline):
        """Ensure that all data sets are serialisable and that we do not have
        any non proxied memory data sets being used as outputs as their content
        will not be synchronized across threads.
        """

        datasets = catalog._datasets  # noqa: protected-access

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
                f"The following data sets cannot be used with multiprocessing: "
                f"{sorted(unserialisable)}\nIn order to utilize multiprocessing you "
                f"need to make sure all data sets are serialisable, i.e. data sets "
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
                f"The following data sets are memory data sets: "
                f"{sorted(memory_datasets)}\n"
                f"ParallelRunner does not support output to externally created "
                f"MemoryDatasets"
            )

    def _get_required_workers_count(self, pipeline: Pipeline):
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
            AttributeError: When the provided pipeline is not suitable for
                parallel execution.
            RuntimeError: If the runner is unable to schedule the execution of
                all pipeline nodes.
            Exception: In case of any downstream node failure.

        """
        # noqa: import-outside-toplevel,cyclic-import

        nodes = pipeline.nodes
        self._validate_catalog(catalog, pipeline)
        self._validate_nodes(nodes)

        load_counts = Counter(chain.from_iterable(n.inputs for n in nodes))
        node_dependencies = pipeline.node_dependencies
        todo_nodes = set(node_dependencies.keys())
        done_nodes: set[Node] = set()
        futures = set()
        done = None
        max_workers = self._get_required_workers_count(pipeline)

        from kedro.framework.project import LOGGING, PACKAGE_NAME

        with ProcessPoolExecutor(max_workers=max_workers) as pool:
            while True:
                ready = {n for n in todo_nodes if node_dependencies[n] <= done_nodes}
                todo_nodes -= ready
                for node in ready:
                    futures.add(
                        pool.submit(
                            _run_node_synchronization,
                            node,
                            catalog,
                            self._is_async,
                            session_id,
                            package_name=PACKAGE_NAME,
                            logging_config=LOGGING,  # type: ignore
                        )
                    )
                if not futures:
                    if todo_nodes:
                        debug_data = {
                            "todo_nodes": todo_nodes,
                            "done_nodes": done_nodes,
                            "ready_nodes": ready,
                            "done_futures": done,
                        }
                        debug_data_str = "\n".join(
                            f"{k} = {v}" for k, v in debug_data.items()
                        )
                        raise RuntimeError(
                            f"Unable to schedule new tasks although some nodes "
                            f"have not been run:\n{debug_data_str}"
                        )
                    break  # pragma: no cover
                done, futures = wait(futures, return_when=FIRST_COMPLETED)
                for future in done:
                    node = future.result()
                    done_nodes.add(node)

                    # Decrement load counts, and release any datasets we
                    # have finished with. This is particularly important
                    # for the shared, default datasets we created above.
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
