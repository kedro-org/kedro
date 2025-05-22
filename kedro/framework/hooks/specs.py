"""A module containing specifications for all callable hooks in the Kedro's execution timeline.
For more information about these specifications, please visit
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#specs)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .markers import hook_spec

if TYPE_CHECKING: # pragma: no cover
    from kedro.framework.context import KedroContext
    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node
    from multiprocessing.managers import SyncManager


class DataCatalogSpecs:
    @hook_spec
    def after_catalog_created(  # noqa: PLR0913
        self,
        catalog: CatalogProtocol,
        conf_catalog: dict[str, Any],
        conf_creds: dict[str, Any],
        feed_dict: dict[str, Any],
        save_version: str,
        load_versions: dict[str, str],
    ) -> None:
        """Hooks to be invoked after a data catalog is created."""
        pass # pragma: no cover

class NodeSpecs:
    @hook_spec
    def before_node_run(
        self, node: Node, catalog: CatalogProtocol, inputs: dict[str, Any], is_async: bool, session_id: str,
    ) -> dict[str, Any] | None:
        """Hook to be invoked before a node runs."""
        pass # pragma: no cover
    @hook_spec
    def after_node_run(  # noqa: PLR0913
        self, node: Node, catalog: CatalogProtocol, inputs: dict[str, Any], outputs: dict[str, Any], is_async: bool, session_id: str,
    ) -> None:
        """Hook to be invoked after a node runs."""
        pass # pragma: no cover
    @hook_spec
    def on_node_error(  # noqa: PLR0913
        self, error: Exception, node: Node, catalog: CatalogProtocol, inputs: dict[str, Any], is_async: bool, session_id: str,
    ) -> None:
        """Hook to be invoked if a node run throws an uncaught error."""
        pass # pragma: no cover

class PipelineSpecs:
    @hook_spec
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol
    ) -> None:
        """Hook to be invoked before a pipeline runs."""
        pass # pragma: no cover
    @hook_spec
    def after_pipeline_run(
        self, run_params: dict[str, Any], run_result: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol,
    ) -> None:
        """Hook to be invoked after a pipeline runs."""
        pass # pragma: no cover
    @hook_spec
    def on_pipeline_error(
        self, error: Exception, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol,
    ) -> None:
        """Hook to be invoked if a pipeline run throws an uncaught Exception."""
        pass # pragma: no cover

class DatasetSpecs:
    @hook_spec
    def before_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        """Hook to be invoked before a dataset is loaded from the catalog."""
        pass # pragma: no cover
    @hook_spec
    def after_dataset_loaded(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked after a dataset is loaded from the catalog."""
        pass # pragma: no cover
    @hook_spec
    def before_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked before a dataset is saved to the catalog."""
        pass # pragma: no cover
    @hook_spec
    def after_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked after a dataset is saved in the catalog."""
        pass # pragma: no cover

class KedroContextSpecs:
    @hook_spec
    def after_context_created(self, context: KedroContext,) -> None:
        """Hooks to be invoked after a `KedroContext` is created."""
        pass # pragma: no cover

class RunnerSpecs:
    """Namespace that defines all specifications for a runner's lifecycle hooks."""

    @hook_spec
    def on_parallel_runner_start(self, manager: "SyncManager", catalog: "CatalogProtocol"): # type: ignore
        """
        Hook to be called by the ParallelRunner after its multiprocessing SyncManager is started
        and before it starts submitting tasks. Allows plugins to receive the manager for
        creating shared state, and the main catalog for reference.

        Args:
            manager: The multiprocessing.managers.SyncManager instance from the ParallelRunner.
            catalog: The main DataCatalog instance from the KedroSession.
        """
        pass # pragma: no cover

    @hook_spec
    def get_picklable_hook_implementations_for_subprocess(self) -> Iterable[Any] | None:
        """
        Allows hook providers to return picklable hook instances for ParallelRunner subprocesses.
        These instances will be registered with a new PluginManager in each subprocess.
        They should rely on shared state (e.g., via SyncManager) for coordination.

        Returns:
            An iterable of picklable hook implementation objects, or None.
        """
        pass # pragma: no cover
