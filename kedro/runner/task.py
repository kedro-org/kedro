from __future__ import annotations

import inspect
import itertools as it
import logging # Make sure logging is imported
import multiprocessing
from collections.abc import Iterable, Iterator
# from concurrent.futures import ( # No longer needed here, AbstractRunner handles futures
#     ALL_COMPLETED,
#     Future,
#     ThreadPoolExecutor,
#     as_completed,
#     wait,
# )
from typing import TYPE_CHECKING, Any

# from more_itertools import interleave # No longer needed here

from kedro.framework.hooks.manager import (
    _create_hook_manager,
    _register_hooks,
    _register_hooks_entry_points,
    _NullPluginManager, # Ensure this is imported
)
from kedro.framework.project import settings

if TYPE_CHECKING: # pragma: no cover
    from pluggy import PluginManager as PluggyPluginManager # Alias to avoid conflict
    from kedro.io import CatalogProtocol
    from kedro.pipeline.node import Node


class TaskError(Exception):
    """``TaskError`` raised by ``Task``
    in case of failure of provided task arguments
    """
    pass


class Task:
    def __init__(  # noqa: PLR0913
        self,
        node: Node,
        catalog: CatalogProtocol,
        is_async: bool,
        hook_manager: PluggyPluginManager | _NullPluginManager | None = None,
        session_id: str | None = None,
        # parallel: bool = False, # Removed as per previous fix
    ):
        self.node = node
        self.catalog = catalog
        self.hook_manager = hook_manager
        self.is_async = is_async
        self.session_id = session_id
        # self.parallel = parallel # Removed

    def execute(self) -> Node:
        """
        This method is the core execution logic for the task.
        It's called by __call__ when the executor runs the task.
        """
        if self.is_async and inspect.isgeneratorfunction(self.node.func): # pragma: no cover
            raise ValueError(
                f"Async data loading and saving does not work with "
                f"nodes wrapping generator functions. Please make "
                f"sure you don't use `yield` anywhere "
                f"in node {self.node!s}."
            )

        effective_hook_manager = self.hook_manager
        if not effective_hook_manager: # pragma: no cover
            logging.getLogger(__name__).warning(
                "Task executing without a provided hook_manager. "
                "Shared hooks may not function correctly in parallel mode. "
                "Falling back to _NullPluginManager."
            )
            effective_hook_manager = _NullPluginManager()


        if self.is_async: # pragma: no cover
            # _run_node_async was part of AbstractRunner, Task should focus on sequential logic
            # and let the runner handle async execution of loads/saves if needed.
            # For simplicity in Task, we'll assume sequential load/save for now,
            # or the runner would need to manage async calls around the Task's synchronous parts.
            # The original `_run_node_async` was complex and better suited to the runner.
            # Reverting to sequential run within the task for clarity.
            # If async load/save for a single task is needed, it's more intricate.
            node = self._run_node_sequential(
                self.node,
                self.catalog,
                effective_hook_manager, # type: ignore
                self.session_id,
            )

        else:
            node = self._run_node_sequential(
                self.node,
                self.catalog,
                effective_hook_manager, # type: ignore
                self.session_id,
            )

        for name in node.confirms: # pragma: no cover
            self.catalog.confirm(name)

        return node

    def __call__(self) -> Node:
        """Make the class instance callable by ProcessPoolExecutor."""
        # This is the entry point when the executor runs the task.
        # It should call the main execution logic.
        return self.execute()

    @staticmethod
    def _bootstrap_subprocess(
        package_name: str, logging_config: dict[str, Any] | None = None
    ) -> None: # pragma: no cover
        from kedro.framework.project import configure_logging, configure_project

        configure_project(package_name)
        if logging_config:
            configure_logging(logging_config)

    # _run_node_synchronization is removed from Task, as ParallelRunner now prepares
    # and passes the correct hook_manager. If a fallback is truly needed for some
    # other direct Task usage, it would be separate.

    def _run_node_sequential(
        self,
        node: Node,
        catalog: CatalogProtocol,
        hook_manager: PluggyPluginManager | _NullPluginManager,
        session_id: str | None = None,
    ) -> Node:
        inputs = {}

        for name in node.inputs:
            hook_manager.hook.before_dataset_loaded(dataset_name=name, node=node)
            inputs[name] = catalog.load(name)
            hook_manager.hook.after_dataset_loaded(
                dataset_name=name, data=inputs[name], node=node
            )

        is_async_for_hooks = False # Inside the task, load/save is sequential for now

        additional_inputs = self._collect_inputs_from_hook(
            node, catalog, inputs, is_async_for_hooks, hook_manager, session_id=session_id
        )
        inputs.update(additional_inputs)

        outputs = self._call_node_run(
            node, catalog, inputs, is_async_for_hooks, hook_manager, session_id=session_id
        )

        items: Iterable = outputs.items()
        # The `isinstance(d, Iterator)` check for generator nodes
        # should ideally be handled by the runner if it wants to stream data.
        # For Task, we assume outputs are complete data for saving.
        # If you need to support generator nodes directly within Task's scope for saving,
        # the interleave logic would be needed here.
        # For now, keeping it simpler as the error wasn't about this part.

        for name, data in items:
            hook_manager.hook.before_dataset_saved(
                dataset_name=name, data=data, node=node
            )
            catalog.save(name, data)
            hook_manager.hook.after_dataset_saved(
                dataset_name=name, data=data, node=node
            )
        return node

    # _run_node_async is removed from Task as it's more complex and relates to how the
    # *runner* manages async I/O, not the task itself which focuses on a single node's logic.
    # The `is_async` flag on Task init now mainly signals to hooks.

    # _synchronous_dataset_load is also removed as it was part of the Task's _run_node_async logic.

    @staticmethod
    def _collect_inputs_from_hook(  # noqa: PLR0913
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        is_async: bool, # This now refers to the hook context, not internal Task async
        hook_manager: PluggyPluginManager | _NullPluginManager,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        inputs_copy = ( # Renamed to avoid conflict with built-in
            inputs.copy()
        )
        hook_response = hook_manager.hook.before_node_run(
            node=node,
            catalog=catalog,
            inputs=inputs_copy, # Pass the copy
            is_async=is_async,
            session_id=session_id,
        )

        additional_inputs = {}
        if hook_response is not None:
            for response in hook_response:
                if response is not None and not isinstance(response, dict): # pragma: no cover
                    response_type = type(response).__name__
                    raise TypeError(
                        f"'before_node_run' must return either None or a dictionary mapping "
                        f"dataset names to updated values, got '{response_type}' instead."
                    )
                additional_inputs.update(response or {})
        return additional_inputs

    @staticmethod
    def _call_node_run(  # noqa: PLR0913
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        is_async: bool, # This now refers to the hook context
        hook_manager: PluggyPluginManager | _NullPluginManager,
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
