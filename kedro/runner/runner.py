"""``AbstractRunner`` is the base class for all ``Pipeline`` runner
implementations.
"""

from __future__ import annotations

import inspect
import logging
import os
import sys
import warnings
from abc import ABC, abstractmethod
from collections import Counter, deque
from concurrent.futures import (
    FIRST_COMPLETED,
    Executor,
    Future,
    ProcessPoolExecutor,
    wait,
)
from itertools import chain
from time import perf_counter
from typing import TYPE_CHECKING, Any

from pluggy import PluginManager

from kedro import KedroDeprecationWarning
from kedro.framework.hooks.manager import _NullPluginManager
from kedro.io import CatalogProtocol, MemoryDataset, SharedMemoryDataset
from kedro.pipeline import Pipeline
from kedro.runner.task import Task

# see https://github.com/python/cpython/blob/master/Lib/concurrent/futures/process.py#L114
_MAX_WINDOWS_WORKERS = 61

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from pluggy import PluginManager

    from kedro.pipeline.node import Node


class AbstractRunner(ABC):
    """``AbstractRunner`` is the base class for all ``Pipeline`` runner
    implementations.
    """

    def __init__(
        self,
        is_async: bool = False,
        extra_dataset_patterns: dict[str, dict[str, Any]] | None = None,
    ):
        """Instantiates the runner class.

        Args:
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
            extra_dataset_patterns: Extra dataset factory patterns to be added to the catalog
                during the run. This is used to set the default datasets on the Runner instances.

        """
        self._is_async = is_async
        self._extra_dataset_patterns = extra_dataset_patterns

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(self.__module__)

    def run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the ``Pipeline`` using the datasets provided by ``catalog``
        and save results back to the same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be satisfied.

        Returns:
            Any node outputs that cannot be processed by the catalog.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.

        """
        # Check which datasets used in the pipeline are in the catalog or match
        # a pattern in the catalog, not including extra dataset patterns
        # Run a warm-up to materialize all datasets in the catalog before run
        warmed_up_ds = []
        for ds in pipeline.datasets():
            if ds in catalog:
                warmed_up_ds.append(ds)
                _ = catalog._get_dataset(ds)

        # Check if there are any input datasets that aren't in the catalog and
        # don't match a pattern in the catalog.
        unsatisfied = pipeline.inputs() - set(warmed_up_ds)

        if unsatisfied:
            raise ValueError(
                f"Pipeline input(s) {unsatisfied} not found in the {catalog.__class__.__name__}"
            )

        # Register the default dataset pattern with the catalog
        # TODO: replace with catalog.config_resolver.add_runtime_patterns() when removing old catalog
        catalog = catalog.shallow_copy(
            extra_dataset_patterns=self._extra_dataset_patterns
        )

        hook_or_null_manager = hook_manager or _NullPluginManager()

        # Check which datasets used in the pipeline are in the catalog or match
        # a pattern in the catalog, including added extra_dataset_patterns
        registered_ds = [ds for ds in pipeline.datasets() if ds in catalog]

        if self._is_async:
            self._logger.info(
                "Asynchronous mode is enabled for loading and saving data"
            )

        start_time = perf_counter()
        self._run(pipeline, catalog, hook_or_null_manager, session_id)  # type: ignore[arg-type]
        end_time = perf_counter()
        run_duration = end_time - start_time

        self._logger.info(
            f"Pipeline execution completed successfully in {run_duration:.1f} sec."
        )

        # Identify MemoryDataset in the catalog
        memory_datasets = {
            ds_name
            for ds_name, ds in catalog._datasets.items()
            if isinstance(ds, MemoryDataset) or isinstance(ds, SharedMemoryDataset)
        }

        # Check if there's any output datasets that aren't in the catalog and don't match a pattern
        # in the catalog and include MemoryDataset.
        free_outputs = pipeline.outputs() - (set(registered_ds) - memory_datasets)

        run_output = {ds_name: catalog.load(ds_name) for ds_name in free_outputs}

        # Remove runtime patterns after run, so they do not affect further runs
        if self._extra_dataset_patterns:
            catalog.config_resolver.remove_runtime_patterns(
                self._extra_dataset_patterns
            )

        return run_output

    def run_only_missing(
        self, pipeline: Pipeline, catalog: CatalogProtocol, hook_manager: PluginManager
    ) -> dict[str, Any]:
        """Run only the missing outputs from the ``Pipeline`` using the
        datasets provided by ``catalog``, and save results back to the
        same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be
                satisfied.

        Returns:
            Any node outputs that cannot be processed by the
            catalog. These are returned in a dictionary, where
            the keys are defined by the node outputs.

        """
        free_outputs = pipeline.outputs() - set(catalog.list())
        missing = {ds for ds in catalog.list() if not catalog.exists(ds)}
        to_build = free_outputs | missing
        to_rerun = pipeline.only_nodes_with_outputs(*to_build) + pipeline.from_inputs(
            *to_build
        )

        # We also need any missing datasets that are required to run the
        # `to_rerun` pipeline, including any chains of missing datasets.
        unregistered_ds = pipeline.datasets() - set(catalog.list())
        output_to_unregistered = pipeline.only_nodes_with_outputs(*unregistered_ds)
        input_from_unregistered = to_rerun.inputs() & unregistered_ds
        to_rerun += output_to_unregistered.to_outputs(*input_from_unregistered)

        return self.run(to_rerun, catalog, hook_manager)

    @abstractmethod  # pragma: no cover
    def _get_executor(self, max_workers: int) -> Executor | None:
        """Abstract method to provide the correct executor (e.g., ThreadPoolExecutor, ProcessPoolExecutor or None if running sequentially)."""
        pass

    @abstractmethod  # pragma: no cover
    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol,
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
    ) -> None:
        """The abstract interface for running pipelines, assuming that the
         inputs have already been checked and normalized by run().
         This contains the Common pipeline execution logic using an executor.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.
        """

        nodes = pipeline.nodes

        self._validate_catalog(catalog, pipeline)
        self._validate_nodes(nodes)
        self._set_manager_datasets(catalog, pipeline)

        load_counts = Counter(chain.from_iterable(n.inputs for n in pipeline.nodes))
        node_dependencies = pipeline.node_dependencies
        todo_nodes = set(node_dependencies.keys())
        done_nodes: set[Node] = set()
        futures = set()
        done = None
        max_workers = self._get_required_workers_count(pipeline)

        pool = self._get_executor(max_workers)
        if pool is None:
            for exec_index, node in enumerate(nodes):
                try:
                    Task(
                        node=node,
                        catalog=catalog,
                        hook_manager=hook_manager,
                        is_async=self._is_async,
                        session_id=session_id,
                    ).execute()
                    done_nodes.add(node)
                except Exception:
                    self._suggest_resume_scenario(pipeline, done_nodes, catalog)
                    raise
                self._logger.info("Completed node: %s", node.name)
                self._logger.info(
                    "Completed %d out of %d tasks", len(done_nodes), len(nodes)
                )
                self._release_datasets(node, catalog, load_counts, pipeline)

            return  # Exit early since everything runs sequentially

        with pool as executor:
            while True:
                ready = {n for n in todo_nodes if node_dependencies[n] <= done_nodes}
                todo_nodes -= ready
                for node in ready:
                    task = Task(
                        node=node,
                        catalog=catalog,
                        hook_manager=hook_manager,
                        is_async=self._is_async,
                        session_id=session_id,
                    )
                    if isinstance(executor, ProcessPoolExecutor):
                        task.parallel = True
                    futures.add(executor.submit(task))
                if not futures:
                    if todo_nodes:
                        self._raise_runtime_error(todo_nodes, done_nodes, ready, done)
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
                    self._release_datasets(node, catalog, load_counts, pipeline)

    @staticmethod
    def _raise_runtime_error(
        todo_nodes: set[Node],
        done_nodes: set[Node],
        ready: set[Node],
        done: set[Future[Node]] | None,
    ) -> None:
        debug_data = {
            "todo_nodes": todo_nodes,
            "done_nodes": done_nodes,
            "ready_nodes": ready,
            "done_futures": done,
        }
        debug_data_str = "\n".join(f"{k} = {v}" for k, v in debug_data.items())
        raise RuntimeError(
            f"Unable to schedule new tasks although some nodes "
            f"have not been run:\n{debug_data_str}"
        )

    def _suggest_resume_scenario(
        self,
        pipeline: Pipeline,
        done_nodes: Iterable[Node],
        catalog: CatalogProtocol,
    ) -> None:
        """
        Suggest a command to the user to resume a run after it fails.
        The run should be started from the point closest to the failure
        for which persisted input exists.

        Args:
            pipeline: the ``Pipeline`` of the run.
            done_nodes: the ``Node``s that executed successfully.
            catalog: an implemented instance of ``CatalogProtocol`` of the run.

        """
        remaining_nodes = set(pipeline.nodes) - set(done_nodes)

        postfix = ""
        if done_nodes:
            start_node_names = _find_nodes_to_resume_from(
                pipeline=pipeline,
                unfinished_nodes=remaining_nodes,
                catalog=catalog,
            )
            start_nodes_str = ",".join(sorted(start_node_names))
            postfix += f'  --from-nodes "{start_nodes_str}"'

        if not postfix:
            self._logger.warning(
                "No nodes ran. Repeat the previous command to attempt a new run."
            )
        else:
            self._logger.warning(
                f"There are {len(remaining_nodes)} nodes that have not run.\n"
                "You can resume the pipeline run from the nearest nodes with "
                "persisted inputs by adding the following "
                f"argument to your previous command:\n{postfix}"
            )

    @staticmethod
    def _release_datasets(
        node: Node, catalog: CatalogProtocol, load_counts: dict, pipeline: Pipeline
    ) -> None:
        """Decrement dataset load counts and release any datasets we've finished with"""
        for dataset in node.inputs:
            load_counts[dataset] -= 1
            if load_counts[dataset] < 1 and dataset not in pipeline.inputs():
                catalog.release(dataset)
        for dataset in node.outputs:
            if load_counts[dataset] < 1 and dataset not in pipeline.outputs():
                catalog.release(dataset)

    def _validate_catalog(self, catalog: CatalogProtocol, pipeline: Pipeline) -> None:
        # Add catalog validation logic here if needed
        pass

    def _validate_nodes(self, node: Iterable[Node]) -> None:
        # Add node validation logic here if needed
        pass

    def _set_manager_datasets(
        self, catalog: CatalogProtocol, pipeline: Pipeline
    ) -> None:
        # Set up any necessary manager datasets here
        pass

    def _get_required_workers_count(self, pipeline: Pipeline) -> int:
        return 1

    @classmethod
    def _validate_max_workers(cls, max_workers: int | None) -> int:
        """
        Validates and returns the number of workers. Sets to os.cpu_count() or 1 if max_workers is None,
        and limits max_workers to 61 on Windows.

        Args:
            max_workers: Desired number of workers. If None, defaults to os.cpu_count() or 1.

        Returns:
            A valid number of workers to use.

        Raises:
            ValueError: If max_workers is set and is not positive.
        """
        if max_workers is None:
            max_workers = os.cpu_count() or 1
            if sys.platform == "win32":
                max_workers = min(_MAX_WINDOWS_WORKERS, max_workers)
        elif max_workers <= 0:
            raise ValueError("max_workers should be positive")

        return max_workers


def _find_nodes_to_resume_from(
    pipeline: Pipeline, unfinished_nodes: Collection[Node], catalog: CatalogProtocol
) -> set[str]:
    """Given a collection of unfinished nodes in a pipeline using
    a certain catalog, find the node names to pass to pipeline.from_nodes()
    to cover all unfinished nodes, including any additional nodes
    that should be re-run if their outputs are not persisted.

    Args:
        pipeline: the ``Pipeline`` to find starting nodes for.
        unfinished_nodes: collection of ``Node``s that have not finished yet
        catalog: an implemented instance of ``CatalogProtocol`` of the run.

    Returns:
        Set of node names to pass to pipeline.from_nodes() to continue
        the run.

    """
    nodes_to_be_run = _find_all_nodes_for_resumed_pipeline(
        pipeline, unfinished_nodes, catalog
    )

    # Find which of the remaining nodes would need to run first (in topo sort)
    persistent_ancestors = _find_initial_node_group(pipeline, nodes_to_be_run)

    return {n.name for n in persistent_ancestors}


def _find_all_nodes_for_resumed_pipeline(
    pipeline: Pipeline, unfinished_nodes: Iterable[Node], catalog: CatalogProtocol
) -> set[Node]:
    """Breadth-first search approach to finding the complete set of
    ``Node``s which need to run to cover all unfinished nodes,
    including any additional nodes that should be re-run if their outputs
    are not persisted.

    Args:
        pipeline: the ``Pipeline`` to analyze.
        unfinished_nodes: the iterable of ``Node``s which have not finished yet.
        catalog: an implemented instance of ``CatalogProtocol`` of the run.

    Returns:
        A set containing all input unfinished ``Node``s and all remaining
        ``Node``s that need to run in case their outputs are not persisted.

    """
    nodes_to_run = set(unfinished_nodes)
    initial_nodes = _nodes_with_external_inputs(unfinished_nodes)

    queue, visited = deque(initial_nodes), set(initial_nodes)
    while queue:
        current_node = queue.popleft()
        nodes_to_run.add(current_node)
        # Look for parent nodes which produce non-persistent inputs (if those exist)
        non_persistent_inputs = _enumerate_non_persistent_inputs(current_node, catalog)
        for node in _enumerate_nodes_with_outputs(pipeline, non_persistent_inputs):
            if node in visited:
                continue
            visited.add(node)
            queue.append(node)

    # Make sure no downstream tasks are skipped
    nodes_to_run = set(pipeline.from_nodes(*(n.name for n in nodes_to_run)).nodes)

    return nodes_to_run


def _nodes_with_external_inputs(nodes_of_interest: Iterable[Node]) -> set[Node]:
    """For given ``Node``s , find their subset which depends on
    external inputs of the ``Pipeline`` they constitute. External inputs
    are pipeline inputs not produced by other ``Node``s in the ``Pipeline``.

    Args:
        nodes_of_interest: the ``Node``s to analyze.

    Returns:
        A set of ``Node``s that depend on external inputs
        of nodes of interest.

    """
    p_nodes_of_interest = Pipeline(nodes_of_interest)
    p_nodes_with_external_inputs = p_nodes_of_interest.only_nodes_with_inputs(
        *p_nodes_of_interest.inputs()
    )
    return set(p_nodes_with_external_inputs.nodes)


def _enumerate_non_persistent_inputs(node: Node, catalog: CatalogProtocol) -> set[str]:
    """Enumerate non-persistent input datasets of a ``Node``.

    Args:
        node: the ``Node`` to check the inputs of.
        catalog: an implemented instance of ``CatalogProtocol`` of the run.

    Returns:
        Set of names of non-persistent inputs of given ``Node``.

    """
    # We use _datasets because they pertain parameter name format
    catalog_datasets = catalog._datasets
    non_persistent_inputs: set[str] = set()
    for node_input in node.inputs:
        if node_input.startswith("params:"):
            continue

        if (
            node_input not in catalog_datasets
            or catalog_datasets[node_input]._EPHEMERAL
        ):
            non_persistent_inputs.add(node_input)

    return non_persistent_inputs


def _enumerate_nodes_with_outputs(
    pipeline: Pipeline, outputs: Collection[str]
) -> list[Node]:
    """For given outputs, returns a list containing nodes that
    generate them in the given ``Pipeline``.

    Args:
        pipeline: the ``Pipeline`` to search for nodes in.
        outputs: the dataset names to find source nodes for.

    Returns:
        A list of all ``Node``s that are producing ``outputs``.

    """
    parent_pipeline = pipeline.only_nodes_with_outputs(*outputs)
    return parent_pipeline.nodes


def _find_initial_node_group(pipeline: Pipeline, nodes: Iterable[Node]) -> list[Node]:
    """Given a collection of ``Node``s in a ``Pipeline``,
    find the initial group of ``Node``s to be run (in topological order).

    This can be used to define a sub-pipeline with the smallest possible
    set of nodes to pass to --from-nodes.

    Args:
        pipeline: the ``Pipeline`` to search for initial ``Node``s in.
        nodes: the ``Node``s to find initial group for.

    Returns:
        A list of initial ``Node``s to run given inputs (in topological order).

    """
    node_names = {n.name for n in nodes}
    if len(node_names) == 0:
        return []
    sub_pipeline = pipeline.only_nodes(*node_names)
    initial_nodes = sub_pipeline.grouped_nodes[0]
    return initial_nodes


def run_node(
    node: Node,
    catalog: CatalogProtocol,
    hook_manager: PluginManager,
    is_async: bool = False,
    session_id: str | None = None,
) -> Node:
    """Run a single `Node` with inputs from and outputs to the `catalog`.

    Args:
        node: The ``Node`` to run.
        catalog: An implemented instance of ``CatalogProtocol`` containing the node's inputs and outputs.
        hook_manager: The ``PluginManager`` to activate hooks.
        is_async: If True, the node inputs and outputs are loaded and saved
            asynchronously with threads. Defaults to False.
        session_id: The session id of the pipeline run.

    Raises:
        ValueError: Raised if is_async is set to True for nodes wrapping
            generator functions.

    Returns:
        The node argument.

    """
    warnings.warn(
        "`run_node()` has been deprecated and will be removed in Kedro 1.0.0.",
        KedroDeprecationWarning,
    )

    if is_async and inspect.isgeneratorfunction(node.func):
        raise ValueError(
            f"Async data loading and saving does not work with "
            f"nodes wrapping generator functions. Please make "
            f"sure you don't use `yield` anywhere "
            f"in node {node!s}."
        )

    task = Task(
        node=node,
        catalog=catalog,
        hook_manager=hook_manager,
        is_async=is_async,
        session_id=session_id,
    )
    node = task.execute()
    return node
