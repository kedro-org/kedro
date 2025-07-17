"""A module containing specifications for all callable hooks in the Kedro's execution timeline.
For more information about these specifications, please visit
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#specs)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .markers import hook_spec

if TYPE_CHECKING:
    from kedro.framework.context import KedroContext
    from kedro.io import CatalogProtocol
    from kedro.pipeline import Pipeline
    from kedro.pipeline.node import Node


class DataCatalogSpecs:
    """Namespace that defines all specifications for a data catalog's lifecycle hooks."""

    @hook_spec
    def after_catalog_created(  # noqa: PLR0913
        self,
        catalog: CatalogProtocol,
        conf_catalog: dict[str, Any],
        conf_creds: dict[str, Any],
        parameters: dict[str, Any],
        save_version: str,
        load_versions: dict[str, str],
    ) -> None:
        """Hooks to be invoked after a data catalog is created.
        It receives the ``catalog`` as well as
        all the arguments for ``KedroContext._create_catalog``.

        Args:
            catalog: The catalog that was created.
            conf_catalog: The config from which the catalog was created.
            conf_creds: The credentials conf from which the catalog was created.
            parameters: The parameters that are added to the catalog after creation.
            save_version: The save_version used in ``save`` operations
                for all datasets in the catalog.
            load_versions: The load_versions used in ``load`` operations
                for each dataset in the catalog.
        """
        pass


class NodeSpecs:
    """Namespace that defines all specifications for a node's lifecycle hooks."""

    @hook_spec
    def before_node_run(
        self,
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> dict[str, Any] | None:
        """Hook to be invoked before a node runs.

        Args:
            node: The ``Node`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` containing the node's inputs and outputs.
            inputs: The dictionary of inputs dataset.
                The keys are dataset names and the values are the actual loaded input data,
                not the dataset instance.
            is_async: Whether the node was run in ``async`` mode.
            run_id: The id of the run.

        Returns:
            Either None or a dictionary mapping dataset name(s) to new value(s).
                If returned, this dictionary will be used to update the node inputs,
                which allows to overwrite the node inputs.
        """
        pass

    @hook_spec
    def after_node_run(  # noqa: PLR0913
        self,
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        """Hook to be invoked after a node runs.

        Args:
            node: The ``Node`` that ran.
            catalog: An implemented instance of ``CatalogProtocol`` containing the node's inputs and outputs.
            inputs: The dictionary of inputs dataset.
                The keys are dataset names and the values are the actual loaded input data,
                not the dataset instance.
            outputs: The dictionary of outputs dataset.
                The keys are dataset names and the values are the actual computed output data,
                not the dataset instance.
            is_async: Whether the node was run in ``async`` mode.
            run_id: The id of the run.
        """
        pass

    @hook_spec
    def on_node_error(  # noqa: PLR0913
        self,
        error: Exception,
        node: Node,
        catalog: CatalogProtocol,
        inputs: dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        """Hook to be invoked if a node run throws an uncaught error.
        The signature of this error hook should match the signature of ``before_node_run``
        along with the error that was raised.

        Args:
            error: The uncaught exception thrown during the node run.
            node: The ``Node`` to run.
            catalog: An implemented instance of ``CatalogProtocol`` containing the node's inputs and outputs.
            inputs: The dictionary of inputs dataset.
                The keys are dataset names and the values are the actual loaded input data,
                not the dataset instance.
            is_async: Whether the node was run in ``async`` mode.
            run_id: The id of the run.
        """
        pass


class PipelineSpecs:
    """Namespace that defines all specifications for a pipeline's lifecycle hooks."""

    @hook_spec
    def before_pipeline_run(
        self, run_params: dict[str, Any], pipeline: Pipeline, catalog: CatalogProtocol
    ) -> None:
        """Hook to be invoked before a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
                Should have the following schema::

                   {
                     "run_id": str
                     "project_path": str,
                     "env": str,
                     "kedro_version": str,
                     "tags": Optional[List[str]],
                     "from_nodes": Optional[List[str]],
                     "to_nodes": Optional[List[str]],
                     "node_names": Optional[List[str]],
                     "from_inputs": Optional[List[str]],
                     "to_outputs": Optional[List[str]],
                     "load_versions": Optional[List[str]],
                     "runtime_params": Optional[Dict[str, Any]]
                     "pipeline_name": str,
                     "namespace": Optional[str],
                     "runner": str,
                   }

            pipeline: The ``Pipeline`` that will be run.
            catalog: An implemented instance of ``CatalogProtocol`` to be used during the run.
        """
        pass

    @hook_spec
    def after_pipeline_run(
        self,
        run_params: dict[str, Any],
        run_result: dict[str, Any],
        pipeline: Pipeline,
        catalog: CatalogProtocol,
    ) -> None:
        """Hook to be invoked after a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
                Should have the following schema::

                   {
                     "run_id": str
                     "project_path": str,
                     "env": str,
                     "kedro_version": str,
                     "tags": Optional[List[str]],
                     "from_nodes": Optional[List[str]],
                     "to_nodes": Optional[List[str]],
                     "node_names": Optional[List[str]],
                     "from_inputs": Optional[List[str]],
                     "to_outputs": Optional[List[str]],
                     "load_versions": Optional[List[str]],
                     "runtime_params": Optional[Dict[str, Any]]
                     "pipeline_name": str,
                     "namespace": Optional[str],
                     "runner": str,
                   }

            run_result: The output of ``Pipeline`` run.
            pipeline: The ``Pipeline`` that was run.
            catalog: An implemented instance of ``CatalogProtocol`` used during the run.
        """
        pass

    @hook_spec
    def on_pipeline_error(
        self,
        error: Exception,
        run_params: dict[str, Any],
        pipeline: Pipeline,
        catalog: CatalogProtocol,
    ) -> None:
        """Hook to be invoked if a pipeline run throws an uncaught Exception.
        The signature of this error hook should match the signature of ``before_pipeline_run``
        along with the error that was raised.

        Args:
            error: The uncaught exception thrown during the pipeline run.
            run_params: The params used to run the pipeline.
                Should have the following schema::

                   {
                     "run_id": str
                     "project_path": str,
                     "env": str,
                     "kedro_version": str,
                     "tags": Optional[List[str]],
                     "from_nodes": Optional[List[str]],
                     "to_nodes": Optional[List[str]],
                     "node_names": Optional[List[str]],
                     "from_inputs": Optional[List[str]],
                     "to_outputs": Optional[List[str]],
                     "load_versions": Optional[List[str]],
                     "runtime_params": Optional[Dict[str, Any]]
                     "pipeline_name": str,
                     "namespace": Optional[str],
                     "runner": str,
                   }

            pipeline: The ``Pipeline`` that will was run.
            catalog: An implemented instance of ``CatalogProtocol`` used during the run.
        """
        pass


class DatasetSpecs:
    """Namespace that defines all specifications for a dataset's lifecycle hooks."""

    @hook_spec
    def before_dataset_loaded(self, dataset_name: str, node: Node) -> None:
        """Hook to be invoked before a dataset is loaded from the catalog.

        Args:
            dataset_name: name of the dataset to be loaded from the catalog.
            node: The ``Node`` to run.
        """
        pass

    @hook_spec
    def after_dataset_loaded(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked after a dataset is loaded from the catalog.

        Args:
            dataset_name: name of the dataset that was loaded from the catalog.
            data: the actual data that was loaded from the catalog.
            node: The ``Node`` to run.
        """
        pass

    @hook_spec
    def before_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked before a dataset is saved to the catalog.

        Args:
            dataset_name: name of the dataset to be saved to the catalog.
            data: the actual data to be saved to the catalog.
            node: The ``Node`` that ran.
        """
        pass

    @hook_spec
    def after_dataset_saved(self, dataset_name: str, data: Any, node: Node) -> None:
        """Hook to be invoked after a dataset is saved in the catalog.

        Args:
            dataset_name: name of the dataset that was saved to the catalog.
            data: the actual data that was saved to the catalog.
            node: The ``Node`` that ran.
        """
        pass


class KedroContextSpecs:
    """Namespace that defines all specifications for a Kedro context's lifecycle hooks."""

    @hook_spec
    def after_context_created(
        self,
        context: KedroContext,
    ) -> None:
        """Hooks to be invoked after a `KedroContext` is created. This is the earliest
        hook triggered within a Kedro run. The `KedroContext` stores useful information
        such as `credentials`, `config_loader` and `env`.

        Args:
            context: The context that was created.
        """
