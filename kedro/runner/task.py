from __future__ import annotations

import inspect
import itertools as it
import multiprocessing
from collections.abc import Iterable, Iterator
from concurrent.futures import (
    ALL_COMPLETED,
    Future,
    ThreadPoolExecutor,
    as_completed,
    wait,
)
from typing import TYPE_CHECKING, Any

from more_itertools import interleave

from kedro.framework.hooks.manager import (
    _create_hook_manager,
    _register_hooks,
    _register_hooks_entry_points,
)
from kedro.framework.project import settings

if TYPE_CHECKING:
    from pluggy import PluginManager

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
        hook_manager: PluginManager | None = None,
        session_id: str | None = None,
        parallel: bool = False,
    ):
        self.node = node
        self.catalog = catalog
        self.hook_manager = hook_manager
        self.is_async = is_async
        self.session_id = session_id
        self.parallel = parallel

    def execute(self) -> Node:
        if self.is_async and inspect.isgeneratorfunction(self.node.func):
            raise ValueError(
                f"Async data loading and saving does not work with "
                f"nodes wrapping generator functions. Please make "
                f"sure you don't use `yield` anywhere "
                f"in node {self.node!s}."
            )

        if not self.hook_manager and not self.parallel:
            raise TaskError(
                "No hook_manager provided. This is only allowed when running a ``Task`` with ``ParallelRunner``."
            )

        if self.parallel:
            from kedro.framework.project import LOGGING, PACKAGE_NAME

            hook_manager = Task._run_node_synchronization(
                package_name=PACKAGE_NAME,
                logging_config=LOGGING,  # type: ignore[arg-type]
            )
            self.hook_manager = hook_manager
        if self.is_async:
            node = self._run_node_async(
                self.node,
                self.catalog,
                self.hook_manager,  # type: ignore[arg-type]
                self.session_id,
            )
        else:
            node = self._run_node_sequential(
                self.node,
                self.catalog,
                self.hook_manager,  # type: ignore[arg-type]
                self.session_id,
            )

        for name in node.confirms:
            self.catalog.confirm(name)

        return node

    def __call__(self) -> Node:
        """Make the class instance callable by ProcessPoolExecutor."""
        return self.execute()

    @staticmethod
    def _bootstrap_subprocess(
        package_name: str, logging_config: dict[str, Any] | None = None
    ) -> None:
        from kedro.framework.project import configure_logging, configure_project

        configure_project(package_name)
        if logging_config:
            configure_logging(logging_config)

    @staticmethod
    def _run_node_synchronization(
        package_name: str | None = None,
        logging_config: dict[str, Any] | None = None,
    ) -> Any:
        """Run a single `Node` with inputs from and outputs to the `catalog`.

        A ``PluginManager`` instance is created in each subprocess because the
        ``PluginManager`` can't be serialised.

        Args:
            package_name: The name of the project Python package.
            logging_config: A dictionary containing logging configuration.

        Returns:
            The node argument.

        """
        if multiprocessing.get_start_method() == "spawn" and package_name:
            Task._bootstrap_subprocess(package_name, logging_config)

        hook_manager = _create_hook_manager()
        _register_hooks(hook_manager, settings.HOOKS)
        _register_hooks_entry_points(hook_manager, settings.DISABLE_HOOKS_FOR_PLUGINS)

        return hook_manager

    def _run_node_sequential(
        self,
        node: Node,
        catalog: CatalogProtocol,
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

        additional_inputs = self._collect_inputs_from_hook(
            node, catalog, inputs, is_async, hook_manager, session_id=session_id
        )
        inputs.update(additional_inputs)

        outputs = self._call_node_run(
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
            hook_manager.hook.before_dataset_saved(
                dataset_name=name, data=data, node=node
            )
            catalog.save(name, data)
            hook_manager.hook.after_dataset_saved(
                dataset_name=name, data=data, node=node
            )
        return node

    def _run_node_async(
        self,
        node: Node,
        catalog: CatalogProtocol,
        hook_manager: PluginManager,  # type: ignore[arg-type]
        session_id: str | None = None,
    ) -> Node:
        with ThreadPoolExecutor() as pool:
            inputs: dict[str, Future] = {}

            for name in node.inputs:
                inputs[name] = pool.submit(
                    self._synchronous_dataset_load, name, node, catalog, hook_manager
                )

            wait(inputs.values(), return_when=ALL_COMPLETED)
            inputs = {key: value.result() for key, value in inputs.items()}
            is_async = True

            additional_inputs = self._collect_inputs_from_hook(
                node, catalog, inputs, is_async, hook_manager, session_id=session_id
            )
            inputs.update(additional_inputs)

            outputs = self._call_node_run(
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

    @staticmethod
    def _synchronous_dataset_load(
        dataset_name: str,
        node: Node,
        catalog: CatalogProtocol,
        hook_manager: PluginManager,
    ) -> Any:
        """Minimal wrapper to ensure Hooks are run synchronously
        within an asynchronous dataset load."""
        hook_manager.hook.before_dataset_loaded(dataset_name=dataset_name, node=node)
        return_ds = catalog.load(dataset_name)
        hook_manager.hook.after_dataset_loaded(
            dataset_name=dataset_name, data=return_ds, node=node
        )
        return return_ds

    @staticmethod
    def _collect_inputs_from_hook(  # noqa: PLR0913
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        is_async: bool,
        hook_manager: PluginManager,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        inputs = (
            inputs.copy()
        )  # shallow copy to prevent in-place modification by the hook
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

    @staticmethod
    def _call_node_run(  # noqa: PLR0913
        node: Node,
        catalog: CatalogProtocol,
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
