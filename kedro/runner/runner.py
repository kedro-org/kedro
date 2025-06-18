"""``AbstractRunner`` is the base class for all ``Pipeline`` runner
implementations.
"""

from __future__ import annotations

import logging
import os
import sys
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

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.pipeline import Pipeline
from kedro.runner.task import Task

# see https://github.com/python/cpython/blob/master/Lib/concurrent/futures/process.py#L114
_MAX_WINDOWS_WORKERS = 61

if TYPE_CHECKING:
    from collections.abc import Collection, Iterable

    from pluggy import PluginManager

    from kedro.io import CatalogProtocol, SharedMemoryCatalogProtocol
    from kedro.pipeline.node import Node


class AbstractRunner(ABC):
    """``AbstractRunner`` is the base class for all ``Pipeline`` runner
    implementations.
    """

    def __init__(
        self,
        is_async: bool = False,
    ):
        """Instantiates the runner class.

        Args:
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.
        """
        self._is_async = is_async

    @property
    def _logger(self) -> logging.Logger:
        return logging.getLogger(self.__module__)

    def run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
        only_missing_outputs: bool = False,
    ) -> dict[str, Any]:
        """Run the ``Pipeline`` using the datasets provided by ``catalog``
        and save results back to the same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            run_id: The id of the run.
            only_missing_outputs: Run only nodes with missing outputs.

        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be satisfied.

        Returns:
            Dictionary with pipeline outputs, where keys are dataset names
            and values are dataset object.
        """
        # Apply missing outputs filtering if requested
        if only_missing_outputs:
            pipeline = self._filter_pipeline_for_missing_outputs(pipeline, catalog)

        # Run a warm-up to materialize all datasets in the catalog before run
        for ds in pipeline.datasets():
            _ = catalog.get(ds, fallback_to_runtime_pattern=True)

        hook_or_null_manager = hook_manager or _NullPluginManager()

        if self._is_async:
            self._logger.info(
                "Asynchronous mode is enabled for loading and saving data."
            )

        start_time = perf_counter()
        self._run(pipeline, catalog, hook_or_null_manager, run_id)  # type: ignore[arg-type]
        end_time = perf_counter()
        run_duration = end_time - start_time

        self._logger.info(
            f"Pipeline execution completed successfully in {run_duration:.1f} sec."
        )

        # Now we return all pipeline outputs, but we do not load datasets data
        run_output = {ds_name: catalog[ds_name] for ds_name in pipeline.outputs()}

        return run_output

    def _filter_pipeline_for_missing_outputs(
        self, pipeline: Pipeline, catalog: CatalogProtocol | SharedMemoryCatalogProtocol
    ) -> Pipeline:
        """Filter pipeline to only include nodes needed to produce missing persistent outputs."""
        original_node_count = len(pipeline.nodes)

        # First identify which persistent outputs are missing
        missing_persistent_outputs = set()

        for node in pipeline.nodes:
            for output in node.outputs:
                # Check if it's a persistent dataset that's missing
                if self._is_persistent_and_missing(output, catalog):
                    missing_persistent_outputs.add(output)

        # If no persistent outputs are missing, skip everything
        if not missing_persistent_outputs:
            self._logger.info(
                f"Skipping all {original_node_count} nodes (all persistent outputs exist)"
            )
            return Pipeline([])

        # Use Kedro's built-in method to get only nodes needed for missing outputs
        # This automatically handles dependencies and excludes wasteful nodes
        required_pipeline = pipeline.to_outputs(*missing_persistent_outputs)

        # Log the results
        skipped_count = original_node_count - len(required_pipeline.nodes)
        if skipped_count > 0:
            skipped_names = {n.name for n in pipeline.nodes} - {
                n.name for n in required_pipeline.nodes
            }
            self._logger.info(
                f"Skipping {skipped_count} nodes with existing persistent outputs: "
                f"{', '.join(sorted(skipped_names))}"
            )
            self._logger.info(
                f"Running {len(required_pipeline.nodes)} out of {original_node_count} nodes "
                f"(skipped {skipped_count} nodes)"
            )
        else:
            self._logger.info(
                f"Running all {original_node_count} nodes (no outputs to skip)"
            )

        return required_pipeline

    def _is_persistent_and_missing(
        self, output: str, catalog: CatalogProtocol | SharedMemoryCatalogProtocol
    ) -> bool:
        """Check if an output is a persistent dataset that doesn't exist.

        Args:
            output: The output dataset name.
            catalog: The data catalogue to check.

        Returns:
            True if the output is persistent and missing.
        """
        # First check if it's explicitly in the catalog
        dataset = catalog._datasets.get(output)

        if dataset is not None:
            # It's explicitly in the catalog
            is_ephemeral = getattr(dataset, "_EPHEMERAL", False)
            if is_ephemeral:
                return False

            # It's persistent - check existence
            return not catalog.exists(output)

        if output not in catalog:
            # Not in catalog and no factory - will be MemoryDataset (ephemeral)
            return False

        # Matches a factory pattern - check if it would be ephemeral
        ds = catalog.get(output)
        is_ephemeral = ds is not None and hasattr(ds, "_EPHEMERAL") and ds._EPHEMERAL

        # Return based on ephemeral status and existence
        return False if is_ephemeral else not catalog.exists(output)

    @abstractmethod  # pragma: no cover
    def _get_executor(self, max_workers: int) -> Executor | None:
        """Abstract method to provide the correct executor (e.g., ThreadPoolExecutor, ProcessPoolExecutor or None if running sequentially)."""
        pass

    @abstractmethod  # pragma: no cover
    def _run(
        self,
        pipeline: Pipeline,
        catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
        hook_manager: PluginManager | None = None,
        run_id: str | None = None,
    ) -> None:
        """The abstract interface for running pipelines, assuming that the
         inputs have already been checked and normalized by run().
         This contains the Common pipeline execution logic using an executor.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            run_id: The id of the run.
        """

        nodes = pipeline.nodes

        self._validate_catalog(catalog)
        self._validate_nodes(nodes)
        self._set_manager_datasets(catalog)

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
                        run_id=run_id,
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
                        run_id=run_id,
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
        catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
    ) -> None:
        """
        Suggest a command to the user to resume a run after it fails.
        The run should be started from the point closest to the failure
        for which persisted input exists.

        Args:
            pipeline: the ``Pipeline`` of the run.
            done_nodes: the ``Node``s that executed successfully.
            catalog: an implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` of the run.

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
        node: Node,
        catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
        load_counts: dict,
        pipeline: Pipeline,
    ) -> None:
        """Decrement dataset load counts and release any datasets we've finished with"""
        for dataset in node.inputs:
            load_counts[dataset] -= 1
            if load_counts[dataset] < 1 and dataset not in pipeline.inputs():
                catalog.release(dataset)
        for dataset in node.outputs:
            if load_counts[dataset] < 1 and dataset not in pipeline.outputs():
                catalog.release(dataset)

    def _validate_catalog(
        self, catalog: CatalogProtocol | SharedMemoryCatalogProtocol
    ) -> None:
        # Add catalog validation logic here if needed
        pass

    def _validate_nodes(self, node: Iterable[Node]) -> None:
        # Add node validation logic here if needed
        pass

    def _set_manager_datasets(
        self, catalog: CatalogProtocol | SharedMemoryCatalogProtocol
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
    pipeline: Pipeline,
    unfinished_nodes: Collection[Node],
    catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
) -> set[str]:
    """Given a collection of unfinished nodes in a pipeline using
    a certain catalog, find the node names to pass to pipeline.from_nodes()
    to cover all unfinished nodes, including any additional nodes
    that should be re-run if their outputs are not persisted.

    Args:
        pipeline: the ``Pipeline`` to find starting nodes for.
        unfinished_nodes: collection of ``Node``s that have not finished yet
        catalog: an implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` of the run.

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
    pipeline: Pipeline,
    unfinished_nodes: Iterable[Node],
    catalog: CatalogProtocol | SharedMemoryCatalogProtocol,
) -> set[Node]:
    """Breadth-first search approach to finding the complete set of
    ``Node``s which need to run to cover all unfinished nodes,
    including any additional nodes that should be re-run if their outputs
    are not persisted.

    Args:
        pipeline: the ``Pipeline`` to analyze.
        unfinished_nodes: the iterable of ``Node``s which have not finished yet.
        catalog: an implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` of the run.

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


def _enumerate_non_persistent_inputs(
    node: Node, catalog: CatalogProtocol | SharedMemoryCatalogProtocol
) -> set[str]:
    """Enumerate non-persistent input datasets of a ``Node``.

    Args:
        node: the ``Node`` to check the inputs of.
        catalog: an implemented instance of ``CatalogProtocol`` or ``SharedMemoryCatalogProtocol`` of the run.

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
