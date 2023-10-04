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
from typing import Any, Iterable, Iterator

from more_itertools import interleave
from pluggy import PluginManager

from kedro.framework.hooks.manager import _NullPluginManager
from kedro.io import AbstractDataset, DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node


class AbstractRunner(ABC):
    """``AbstractRunner`` is the base class for all ``Pipeline`` runner
    implementations.
    """

    def __init__(self, is_async: bool = False):
        """Instantiates the runner class.

        Args:
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.

        """
        self._is_async = is_async

    @property
    def _logger(self):
        return logging.getLogger(self.__module__)

    def run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager = None,
        session_id: str = None,
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

        hook_manager = hook_manager or _NullPluginManager()
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

        # Check if there's any output datasets that aren't in the catalog and don't match a pattern
        # in the catalog.
        free_outputs = pipeline.outputs() - set(registered_ds)
        unregistered_ds = pipeline.datasets() - set(registered_ds)

        # Create a default dataset for unregistered datasets
        for ds_name in unregistered_ds:
            catalog.add(ds_name, self.create_default_dataset(ds_name))

        if self._is_async:
            self._logger.info(
                "Asynchronous mode is enabled for loading and saving data"
            )
        self._run(pipeline, catalog, hook_manager, session_id)

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
        session_id: str = None,
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

    @abstractmethod  # pragma: no cover
    def create_default_dataset(self, ds_name: str) -> AbstractDataset:
        """Factory method for creating the default dataset for the runner.

        Args:
            ds_name: Name of the missing dataset.

        Returns:
            An instance of an implementation of ``AbstractDataset`` to be
            used for all unregistered datasets.
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
            node_names = (n.name for n in remaining_nodes)
            resume_p = pipeline.only_nodes(*node_names)
            start_p = resume_p.only_nodes_with_inputs(*resume_p.inputs())

            # find the nearest persistent ancestors of the nodes in start_p
            start_p_persistent_ancestors = _find_persistent_ancestors(
                pipeline, start_p.nodes, catalog
            )

            start_node_names = (n.name for n in start_p_persistent_ancestors)
            postfix += f"  --from-nodes \"{','.join(start_node_names)}\""

        if not postfix:
            self._logger.warning(
                "No nodes ran. Repeat the previous command to attempt a new run."
            )
        else:
            self._logger.warning(
                "There are %d nodes that have not run.\n"
                "You can resume the pipeline run from the nearest nodes with "
                "persisted inputs by adding the following "
                "argument to your previous command:\n%s",
                len(remaining_nodes),
                postfix,
            )


def _find_persistent_ancestors(
    pipeline: Pipeline, children: Iterable[Node], catalog: DataCatalog
) -> set[Node]:
    """Breadth-first search approach to finding the complete set of
    persistent ancestors of an iterable of ``Node``s. Persistent
    ancestors exclusively have persisted ``Dataset``s as inputs.

    Args:
        pipeline: the ``Pipeline`` to find ancestors in.
        children: the iterable containing ``Node``s to find ancestors of.
        catalog: the ``DataCatalog`` of the run.

    Returns:
        A set containing first persistent ancestors of the given
        ``Node``s.

    """
    ancestor_nodes_to_run = set()
    queue, visited = deque(children), set(children)
    while queue:
        current_node = queue.popleft()
        if _has_persistent_inputs(current_node, catalog):
            ancestor_nodes_to_run.add(current_node)
            continue
        for parent in _enumerate_parents(pipeline, current_node):
            if parent in visited:
                continue
            visited.add(parent)
            queue.append(parent)
    return ancestor_nodes_to_run


def _enumerate_parents(pipeline: Pipeline, child: Node) -> list[Node]:
    """For a given ``Node``, returns a list containing the direct parents
    of that ``Node`` in the given ``Pipeline``.

    Args:
        pipeline: the ``Pipeline`` to search for direct parents in.
        child: the ``Node`` to find parents of.

    Returns:
        A list of all ``Node``s that are direct parents of ``child``.

    """
    parent_pipeline = pipeline.only_nodes_with_outputs(*child.inputs)
    return parent_pipeline.nodes


def _has_persistent_inputs(node: Node, catalog: DataCatalog) -> bool:
    """Check if a ``Node`` exclusively has persisted Datasets as inputs.
    If at least one input is a ``MemoryDataset``, return False.

    Args:
        node: the ``Node`` to check the inputs of.
        catalog: the ``DataCatalog`` of the run.

    Returns:
        True if the ``Node`` being checked exclusively has inputs that
        are not ``MemoryDataset``, else False.

    """
    for node_input in node.inputs:
        # noqa: protected-access
        if isinstance(catalog._datasets[node_input], MemoryDataset):
            return False
    return True


def run_node(
    node: Node,
    catalog: DataCatalog,
    hook_manager: PluginManager,
    is_async: bool = False,
    session_id: str = None,
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


def _collect_inputs_from_hook(  # noqa: too-many-arguments
    node: Node,
    catalog: DataCatalog,
    inputs: dict[str, Any],
    is_async: bool,
    hook_manager: PluginManager,
    session_id: str = None,
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


def _call_node_run(  # noqa: too-many-arguments
    node: Node,
    catalog: DataCatalog,
    inputs: dict[str, Any],
    is_async: bool,
    hook_manager: PluginManager,
    session_id: str = None,
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
    session_id: str = None,
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
    session_id: str = None,
) -> Node:
    def _synchronous_dataset_load(dataset_name: str):
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
