"""``LargestSubgraphScheduler`` class definition.
"""

from typing import List

from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.symphony.conductor import Conductor, DEFAULT_EXECUTOR
from kedro.symphony.scheduler.scheduler import AbstractScheduler


class LargestSubgraphScheduler(AbstractScheduler):
    """Subgraph scheduler that determines the largest possible subset that is entirely
    on one executor type at each iteration.
    """

    def __init__(self, pipeline: Pipeline):
        """Constructor.

        Args:
            pipeline: Pipeline object to schedule the execution of.
        """
        super().__init__(pipeline)

        self.node_dependencies = pipeline.node_dependencies
        self.todo_nodes = set(pipeline.node_dependencies.keys())
        self.done_nodes = set()

    def __next__(self) -> List[Node]:
        """Get the next subgraph of nodes.

        Raises:
            StopIteration when we're done iterating.

        Returns:
            List of Nodes in topologically sorted order.
        """
        if not self.todo_nodes:
            raise StopIteration

        ready = {
            n for n in self.todo_nodes if self.node_dependencies[n] <= self.done_nodes
        }

        executor_nodes_map = Conductor.allocate_nodes_to_executors(
            list(ready), DEFAULT_EXECUTOR
        )

        pipelines = []

        # Subset the full pipeline to only nodes with an executor tag. Then,
        # subset again to the connected pipeline that can be executed entirely
        # with one executor type.
        for executor_tag, ready_nodes in executor_nodes_map.items():
            executor_sub_pipeline = self.pipeline.only_nodes_with_tags(
                executor_tag
            ).from_nodes(*[n.name for n in ready_nodes])

            pipelines.append(executor_sub_pipeline)

        largest_sub_pipeline = max(pipelines, key=lambda x: len(x.nodes))

        self.todo_nodes = self.todo_nodes.difference(set(largest_sub_pipeline.nodes))
        self.done_nodes = self.done_nodes.union(set(largest_sub_pipeline.nodes))

        return largest_sub_pipeline.nodes  # Nodes property is sorted already.
