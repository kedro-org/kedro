# Copyright 2020 QuantumBlack Visual Analytics Limited
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE, AND
# NONINFRINGEMENT. IN NO EVENT WILL THE LICENSOR OR OTHER CONTRIBUTORS
# BE LIABLE FOR ANY CLAIM, DAMAGES, OR OTHER LIABILITY, WHETHER IN AN
# ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF, OR IN
# CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#
# The QuantumBlack Visual Analytics Limited ("QuantumBlack") name and logo
# (either separately or in combination, "QuantumBlack Trademarks") are
# trademarks of QuantumBlack. The License does not grant you any right or
# license to the QuantumBlack Trademarks. You may not use the QuantumBlack
# Trademarks or any confusingly similar mark as a trademark for your product,
# or use the QuantumBlack Trademarks in any other manner that might cause
# confusion in the marketplace, including but not limited to in advertising,
# on websites, or on software.
#
# See the License for the specific language governing permissions and
# limitations under the License.

"""A module containing specifications for all callable hooks in the Kedro's execution timeline.
For more information about these specifications, please visit
[Pluggy's documentation](https://pluggy.readthedocs.io/en/stable/#specs)
"""
# pylint: disable=too-many-arguments
from typing import Any, Dict, Iterable, Optional

from kedro.config import ConfigLoader
from kedro.io import DataCatalog
from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.versioning import Journal

from .markers import hook_spec


class DataCatalogSpecs:
    """Namespace that defines all specifications for a data catalog's lifecycle hooks."""

    @hook_spec
    def after_catalog_created(
        self,
        catalog: DataCatalog,
        conf_catalog: Dict[str, Any],
        conf_creds: Dict[str, Any],
        feed_dict: Dict[str, Any],
        save_version: str,
        load_versions: Dict[str, str],
        run_id: str,
    ) -> None:
        """Hooks to be invoked after a data catalog is created.
        It receives the ``catalog`` as well as
        all the arguments for ``KedroContext._create_catalog``.

        Args:
            catalog: The catalog that was created.
            conf_catalog: The config from which the catalog was created.
            conf_creds: The credentials conf from which the catalog was created.
            feed_dict: The feed_dict that was added to the catalog after creation.
            save_version: The save_version used in ``save`` operations
                for all datasets in the catalog.
            load_versions: The load_versions used in ``load`` operations
                for each dataset in the catalog.
            run_id: The id of the run for which the catalog is loaded.
        """
        pass


class NodeSpecs:
    """Namespace that defines all specifications for a node's lifecycle hooks."""

    @hook_spec
    def before_node_run(
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Hook to be invoked before a node runs.
        The arguments received are the same as those used by ``kedro.runner.run_node``

        Args:
            node: The ``Node`` to run.
            catalog: A ``DataCatalog`` containing the node's inputs and outputs.
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
    def after_node_run(  # pylint: disable=too-many-arguments
        self,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        outputs: Dict[str, Any],
        is_async: bool,
        run_id: str,
    ) -> None:
        """Hook to be invoked after a node runs.
        The arguments received are the same as those used by ``kedro.runner.run_node``
        as well as the ``outputs`` of the node run.

        Args:
            node: The ``Node`` that ran.
            catalog: A ``DataCatalog`` containing the node's inputs and outputs.
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
    def on_node_error(
        self,
        error: Exception,
        node: Node,
        catalog: DataCatalog,
        inputs: Dict[str, Any],
        is_async: bool,
        run_id: str,
    ):
        """Hook to be invoked if a node run throws an uncaught error.
        The signature of this error hook should match the signature of ``before_node_run``
        along with the error that was raised.

        Args:
            error: The uncaught exception thrown during the node run.
            node: The ``Node`` to run.
            catalog: A ``DataCatalog`` containing the node's inputs and outputs.
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
        self, run_params: Dict[str, Any], pipeline: Pipeline, catalog: DataCatalog
    ) -> None:
        """Hook to be invoked before a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
                Should be identical to the data logged by Journal with the following schema::

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
                     "load_versions": Optional[List[str]],
                     "pipeline_name": str,
                     "extra_params": Optional[Dict[str, Any]]
                   }

            pipeline: The ``Pipeline`` that will be run.
            catalog: The ``DataCatalog`` to be used during the run.
        """
        pass

    @hook_spec
    def after_pipeline_run(
        self,
        run_params: Dict[str, Any],
        run_result: Dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ) -> None:
        """Hook to be invoked after a pipeline runs.

        Args:
            run_params: The params used to run the pipeline.
                Should be identical to the data logged by Journal with the following schema::

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
                     "load_versions": Optional[List[str]],
                     "pipeline_name": str,
                     "extra_params": Optional[Dict[str, Any]]
                   }

            run_result: The output of ``Pipeline`` run.
            pipeline: The ``Pipeline`` that was run.
            catalog: The ``DataCatalog`` used during the run.
        """
        pass

    @hook_spec
    def on_pipeline_error(
        self,
        error: Exception,
        run_params: Dict[str, Any],
        pipeline: Pipeline,
        catalog: DataCatalog,
    ):
        """Hook to be invoked if a pipeline run throws an uncaught Exception.
        The signature of this error hook should match the signature of ``before_pipeline_run``
        along with the error that was raised.

        Args:
            error: The uncaught exception thrown during the pipeline run.
            run_params: The params used to run the pipeline.
                Should be identical to the data logged by Journal with the following schema::

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
                     "load_versions": Optional[List[str]],
                     "pipeline_name": str,
                     "extra_params": Optional[Dict[str, Any]]
                   }
            pipeline: The ``Pipeline`` that will was run.
            catalog: The ``DataCatalog`` used during the run.
        """
        pass


class DatasetSpecs:
    """Namespace that defines all specifications for a dataset's lifecycle hooks."""

    @hook_spec
    def before_dataset_loaded(self, dataset_name: str) -> None:
        """Hook to be invoked before a dataset is loaded from the catalog.

           Args:
               dataset_name: name of the dataset to be loaded from the catalog.

        """
        pass

    @hook_spec
    def after_dataset_loaded(self, dataset_name: str, data: Any) -> None:
        """Hook to be invoked after a dataset is loaded from the catalog.

           Args:
               dataset_name: name of the dataset that was loaded from the catalog.
               data: the actual data that was loaded from the catalog.

        """
        pass

    @hook_spec
    def before_dataset_saved(self, dataset_name: str, data: Any) -> None:
        """Hook to be invoked before a dataset is saved to the catalog.

           Args:
               dataset_name: name of the dataset to be saved to the catalog.
               data: the actual data to be saved to the catalog.

        """
        pass

    @hook_spec
    def after_dataset_saved(self, dataset_name: str, data: Any) -> None:
        """Hook to be invoked after a dataset is saved in the catalog.

           Args:
               dataset_name: name of the dataset that was saved to the catalog.
               data: the actual data that was saved to the catalog.
        """
        pass


class RegistrationSpecs:
    """Namespace that defines all specifications for hooks registering
    library components with a Kedro project.
    """

    @hook_spec
    def register_pipelines(self) -> Dict[str, Pipeline]:
        """Hook to be invoked to register a project's pipelines.

        Returns:
            A mapping from a pipeline name to a ``Pipeline`` object.

        """
        pass

    @hook_spec(firstresult=True)
    def register_config_loader(self, conf_paths: Iterable[str]) -> ConfigLoader:
        """Hook to be invoked to register a project's config loader.

        Returns:
            An instance of a ``ConfigLoader``.
        """
        pass

    @hook_spec(firstresult=True)
    def register_catalog(
        self,
        catalog: Optional[Dict[str, Dict[str, Any]]],
        credentials: Dict[str, Dict[str, Any]],
        load_versions: Dict[str, str],
        save_version: str,
        journal: Journal,
    ) -> DataCatalog:
        """Hook to be invoked to register a project's data catalog.

        Returns:
            An instance of a ``DataCatalog``.
        """
        pass
