"""``SequentialRunner`` is an ``AbstractRunner`` implementation. It can be
used to run the ``Pipeline`` in a sequential manner using a topological sort
of provided nodes.
"""

from collections import Counter
from itertools import chain

from pluggy import PluginManager

from kedro.io import AbstractDataset, DataCatalog, MemoryDataset
from kedro.pipeline import Pipeline
from kedro.runner.runner import AbstractRunner, run_node


class SequentialRunner(AbstractRunner):
    """``SequentialRunner`` is an ``AbstractRunner`` implementation. It can
    be used to run the ``Pipeline`` in a sequential manner using a
    topological sort of provided nodes.
    """

    def __init__(self, is_async: bool = False):
        """Instantiates the runner classs.

        Args:
            is_async: If True, the node inputs and outputs are loaded and saved
                asynchronously with threads. Defaults to False.

        """
        super().__init__(is_async=is_async)

    def create_default_dataset(self, ds_name: str) -> AbstractDataset:
        """Factory method for creating the default data set for the runner.

        Args:
            ds_name: Name of the missing data set

        Returns:
            An instance of an implementation of AbstractDataset to be used
            for all unregistered data sets.

        """
        return MemoryDataset()

    def _run(
        self,
        pipeline: Pipeline,
        catalog: DataCatalog,
        hook_manager: PluginManager,
        session_id: str = None,
    ) -> None:
        """The method implementing sequential pipeline running.

        Args:
            pipeline: The ``Pipeline`` to run.
            catalog: The ``DataCatalog`` from which to fetch data.
            hook_manager: The ``PluginManager`` to activate hooks.
            session_id: The id of the session.

        Raises:
            Exception: in case of any downstream node failure.
        """
        nodes = pipeline.nodes
        done_nodes = set()

        load_counts = Counter(chain.from_iterable(n.inputs for n in nodes))

        for exec_index, node in enumerate(nodes):
            try:
                run_node(node, catalog, hook_manager, self._is_async, session_id)
                done_nodes.add(node)
            except Exception:
                self._suggest_resume_scenario(pipeline, done_nodes, catalog)
                raise

            # decrement load counts and release any data sets we've finished with
            for dataset in node.inputs:
                load_counts[dataset] -= 1
                if load_counts[dataset] < 1 and dataset not in pipeline.inputs():
                    catalog.release(dataset)
            for dataset in node.outputs:
                if load_counts[dataset] < 1 and dataset not in pipeline.outputs():
                    catalog.release(dataset)

            self._logger.info(
                "Completed %d out of %d tasks", exec_index + 1, len(nodes)
            )
