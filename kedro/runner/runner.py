"""``AbstractRunner`` is the base class for all ``Pipeline`` runner
implementations.
"""
from __future__ import annotations

import inspect
import itertools as it
import logging
from abc import ABC, abstractmethod
from collections import deque
from concurrent.futures import (
    ALL_COMPLETED,
    Future,
    ThreadPoolExecutor,
    as_completed,
    wait,
)
from typing import Any, Collection, Iterable, Iterator

from more_itertools import interleave
from pluggy import PluginManager

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.io import DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
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
            extra_dataset_patterns: Extra dataset factory patterns to be added to the DataCatalog
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
        catalog: DataCatalog,
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """Run the ``Pipeline`` using the datasets provided by ``catalog``
        and save results back to the same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be satisfied.

        Returns:
            Any node outputs that cannot be processed by the ``DataCatalog``.
            These are returned in a dictionary, where the keys are defined
            by the node outputs.

        """

        hook_or_null_manager = hook_manager or _NullPluginManager()
        catalog = catalog.shallow_copy()

        # Check which datasets used in the pipeline are in the catalog or match
        # a pattern in the catalog
        registered_ds = [ds for ds in pipeline.datasets() if ds in catalog]

        # Check if there are any input datasets that aren't in the catalog and
        # don't match a pattern in the catalog.
        unsatisfied = pipeline.inputs() - set(registered_ds)

        if unsatisfied:
            raise ValueError(
                f"Pipeline input(s) {unsatisfied} not found in the DataCatalog"
            )

        # Identify MemoryDataset in the catalog
        memory_datasets = {
            ds_name
            for ds_name, ds in catalog._datasets.items()
            if isinstance(ds, MemoryDataset)
        }

        # Check if there's any output datasets that aren't in the catalog and don't match a pattern
        # in the catalog and include MemoryDataset.
        free_outputs = pipeline.outputs() - (set(registered_ds) - memory_datasets)

        # Register the default dataset pattern with the catalog
        catalog = catalog.shallow_copy(
            extra_dataset_patterns=self._extra_dataset_patterns
        )

        if self._is_async:
            self._logger.info(
                "Asynchronous mode is enabled for loading and saving data"
            )
        self._run(pipeline, catalog, hook_or_null_manager, session_id)  # type: ignore[arg-type]

        self._logger.info("Pipeline execution completed successfully.")

        return {ds_name: catalog.load(ds_name) for ds_name in free_outputs}

    def run_only_missing(
        self, pipeline: Pipeline, catalog: DataCatalog, hook_manager: PluginManager
    ) -> dict[str, Any]:
        """Run only the missing outputs from the ``Pipeline`` using the
        datasets provided by ``catalog``, and save results back to the
        same objects.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
        Raises:
            ValueError: Raised when ``Pipeline`` inputs cannot be
                satisfied.

        Returns:
            Any node outputs that cannot be processed by the
            ``DataCatalog``. These are returned in a dictionary, where
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
    def _run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager,
        session_id: str | None = None,
    ) -> None:
        """The abstract interface for running pipelines, assuming that the
        inputs have already been checked and normalized by run().

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        """
        pass

    def _suggest_resume_scenario(
        self,
        pipeline: Pipeline,
        done_nodes: Iterable[Node],
        catalog: DataCatalog,
    ) -> None:
        """
        Suggest a command to the user to resume a run after it fails.
        The run should be started from the point closest to the failure
        for which persisted input exists.

        Args:
            pipeline: the ``Pipeline`` of the run.
            done_nodes: the ``Node``s that executed successfully.
            catalog: the ``DataCatalog`` of the run.

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


def _find_nodes_to_resume_from(
    pipeline: Pipeline, unfinished_nodes: Collection[Node], catalog: DataCatalog
) -> set[str]:
    """Given a collection of unfinished nodes in a pipeline using
    a certain catalog, find the node names to pass to pipeline.from_nodes()
    to cover all unfinished nodes, including any additional nodes
    that should be re-run if their outputs are not persisted.

    Args:
        pipeline: the ``Pipeline`` to find starting nodes for.
        unfinished_nodes: collection of ``Node``s that have not finished yet
        catalog: the ``DataCatalog`` of the run.

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
    pipeline: Pipeline, unfinished_nodes: Iterable[Node], catalog: DataCatalog
) -> set[Node]:
    """Breadth-first search approach to finding the complete set of
    ``Node``s which need to run to cover all unfinished nodes,
    including any additional nodes that should be re-run if their outputs
    are not persisted.

    Args:
        pipeline: the ``Pipeline`` to analyze.
        unfinished_nodes: the iterable of ``Node``s which have not finished yet.
        catalog: the ``DataCatalog`` of the run.

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


def _enumerate_non_persistent_inputs(node: Node, catalog: DataCatalog) -> set[str]:
    """Enumerate non-persistent input datasets of a ``Node``.

    Args:
        node: the ``Node`` to check the inputs of.
        catalog: the ``DataCatalog`` of the run.

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
    node_names = set(n.name for n in nodes)
    if len(node_names) == 0:
        return []
    sub_pipeline = pipeline.only_nodes(*node_names)
    initial_nodes = sub_pipeline.grouped_nodes[0]
    return initial_nodes


def run_node(
    node: Node,
    catalog: DataCatalog,
    hook_manager: PluginManager,
    is_async: bool = False,
    session_id: str | None = None,
) -> Node:
    """Run a single `Node` with inputs from and outputs to the `catalog`.

    Args:
        node: The ``Node`` to run.
        catalog: A ``DataCatalog`` containing the node's inputs and outputs.
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
    if is_async and inspect.isgeneratorfunction(node.func):
        raise ValueError(
            f"Async data loading and saving does not work with "
            f"nodes wrapping generator functions. Please make "
            f"sure you don't use `yield` anywhere "
            f"in node {str(node)}."
        )

    if is_async:
        node = _run_node_async(node, catalog, hook_manager, session_id)
    else:
        node = _run_node_sequential(node, catalog, hook_manager, session_id)

    for name in node.confirms:
        catalog.confirm(name)
    return node


def _collect_inputs_from_hook(  # noqa: PLR0913
    node: Node,
    catalog: DataCatalog,
    inputs: dict[str, Any],
    is_async: bool,
    hook_manager: PluginManager,
    session_id: str | None = None,
) -> dict[str, Any]:
    inputs = inputs.copy()  # shallow copy to prevent in-place modification by the hook
    hook_response = hook_manager.hook.before_node_run(
        node=node,
        catalog=catalog,
        inputs=inputs,
        is_async=is_async,
        session_id=session_id,
    )

    additional_inputs = {}
    if (
        hook_response is not None
    ):  # all hooks on a _NullPluginManager will return None instead of a list
        for response in hook_response:
            if response is not None and not isinstance(response, dict):
                response_type = type(response).__name__
                raise TypeError(
                    f"'before_node_run' must return either None or a dictionary mapping "
                    f"dataset names to updated values, got '{response_type}' instead."
                )
            additional_inputs.update(response or {})

    return additional_inputs


def _call_node_run(  # noqa: PLR0913
    node: Node,
    catalog: DataCatalog,
    inputs: dict[str, Any],
    is_async: bool,
    hook_manager: PluginManager,
    session_id: str | None = None,
) -> dict[str, Any]:
    try:
        outputs = node.run(inputs)
    except Exception as exc:
        hook_manager.hook.on_node_error(
            error=exc,
            node=node,
            catalog=catalog,
            inputs=inputs,
            is_async=is_async,
            session_id=session_id,
        )
        raise exc
    hook_manager.hook.after_node_run(
        node=node,
        catalog=catalog,
        inputs=inputs,
        outputs=outputs,
        is_async=is_async,
        session_id=session_id,
    )
    return outputs


def _run_node_sequential(
    node: Node,
    catalog: DataCatalog,
    hook_manager: PluginManager,
    session_id: str | None = None,
) -> Node:
    inputs = {}

    for name in node.inputs:
        hook_manager.hook.before_dataset_loaded(dataset_name=name, node=node)
        inputs[name] = catalog.load(name)
        hook_manager.hook.after_dataset_loaded(
            dataset_name=name, data=inputs[name], node=node
        )

    is_async = False

    additional_inputs = _collect_inputs_from_hook(
        node, catalog, inputs, is_async, hook_manager, session_id=session_id
    )
    inputs.update(additional_inputs)

    outputs = _call_node_run(
        node, catalog, inputs, is_async, hook_manager, session_id=session_id
    )

    items: Iterable = outputs.items()
    # if all outputs are iterators, then the node is a generator node
    if all(isinstance(d, Iterator) for d in outputs.values()):
        # Python dictionaries are ordered, so we are sure
        # the keys and the chunk streams are in the same order
        # [a, b, c]
        keys = list(outputs.keys())
        # [Iterator[chunk_a], Iterator[chunk_b], Iterator[chunk_c]]
        streams = list(outputs.values())
        # zip an endless cycle of the keys
        # with an interleaved iterator of the streams
        # [(a, chunk_a), (b, chunk_b), ...] until all outputs complete
        items = zip(it.cycle(keys), interleave(*streams))

    for name, data in items:
        hook_manager.hook.before_dataset_saved(dataset_name=name, data=data, node=node)
        catalog.save(name, data)
        hook_manager.hook.after_dataset_saved(dataset_name=name, data=data, node=node)
    return node


def _run_node_async(
    node: Node,
    catalog: DataCatalog,
    hook_manager: PluginManager,
    session_id: str | None = None,
) -> Node:
    def _synchronous_dataset_load(dataset_name: str) -> Any:
        """Minimal wrapper to ensure Hooks are run synchronously
        within an asynchronous dataset load."""
        hook_manager.hook.before_dataset_loaded(dataset_name=dataset_name, node=node)
        return_ds = catalog.load(dataset_name)
        hook_manager.hook.after_dataset_loaded(
            dataset_name=dataset_name, data=return_ds, node=node
        )
        return return_ds

    with ThreadPoolExecutor() as pool:
        inputs: dict[str, Future] = {}

        for name in node.inputs:
            inputs[name] = pool.submit(_synchronous_dataset_load, name)

        wait(inputs.values(), return_when=ALL_COMPLETED)
        inputs = {key: value.result() for key, value in inputs.items()}
        is_async = True
        additional_inputs = _collect_inputs_from_hook(
            node, catalog, inputs, is_async, hook_manager, session_id=session_id
        )
        inputs.update(additional_inputs)

        outputs = _call_node_run(
            node, catalog, inputs, is_async, hook_manager, session_id=session_id
        )

        future_dataset_mapping = {}
        for name, data in outputs.items():
            hook_manager.hook.before_dataset_saved(
                dataset_name=name, data=data, node=node
            )
            future = pool.submit(catalog.save, name, data)
            future_dataset_mapping[future] = (name, data)

        for future in as_completed(future_dataset_mapping):
            exception = future.exception()
            if exception:
                raise exception
            name, data = future_dataset_mapping[future]
            hook_manager.hook.after_dataset_saved(
                dataset_name=name, data=data, node=node
            )
    return node
