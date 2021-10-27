"""``Conductor`` class definition.
"""
from collections import defaultdict
from typing import Dict, List, Set

from kedro.symphony.scheduler.scheduler import AbstractScheduler
from kedro.pipeline.node import Node
from kedro.utils import load_obj
from kedro.io.data_catalog import DataCatalog


_EXECUTOR_TAG_PREFIX = "executor:"


class Conductor:
    """
    Conductor orchestrates the behaviour between concrete implementations
    of `Scheduler` and `Executor`. While the user is encouraged to provide
    their own implementations of `Scheduler` and `Executor`, the `Conductor`
    is considered immutable.
    """

    def __init__(
        self,
        scheduler: AbstractScheduler,
        catalog: DataCatalog,
        default_executor: str = "executor:kedro.symphony.executor.sequential_executor.SequentialExecutor",
    ):
        self.scheduler = scheduler
        self.default_executor = default_executor
        self.catalog = catalog.shallow_copy()
        self.allocated_nodes = {}

    def run(self):
        # group all ready nodes on available executors
        for ready_nodes in self.scheduler:
            allocated_ready_nodes: Dict[
                str, List[Node]
            ] = self._allocate_nodes_to_executors(ready_nodes)
            for executor_name, nodes in allocated_ready_nodes.items():
                # this should be a singleton and not instantiated every time
                executor_class = load_obj(executor_name.split(_EXECUTOR_TAG_PREFIX)[1])
                executor = executor_class(nodes, False)
                executor.run(nodes=nodes, catalog=self.catalog)

    def _allocate_nodes_to_executors(
        self, ready_nodes: List[Node]
    ) -> Dict[str, List[Node]]:
        output = defaultdict(list)
        for node in ready_nodes:
            executor_tags: Set[str] = {
                x for x in node.tags if x.startswith(_EXECUTOR_TAG_PREFIX)
            }
            assert (
                len(executor_tags) <= 1
            )  # there should not be more than one executor tag
            try:
                executor_tag = next(iter(executor_tags))
            except StopIteration:
                executor_tag = self.default_executor

            output[executor_tag].append(node)  # this is where nodes will go

        return output
