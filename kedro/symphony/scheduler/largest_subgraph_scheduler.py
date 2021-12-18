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

        # The largest connected subgraph for an executor consists of the
        # nodes that don't depend, directly or transitively, on any node
        # yet to be executed (i.e. excluding completed nodes) on another
        # executor.
        for executor_tag, ready_nodes in executor_nodes_map.items():
            only_nodes_without_executor_tag = (
                self.pipeline - self.pipeline.only_nodes_with_tags(executor_tag)
            )
            nodes_requiring_other_executors = self.pipeline.from_nodes(
                *[
                    n.name
                    for n in only_nodes_without_executor_tag.nodes
                    if n not in self.done_nodes
                ]
            )
            executable_subpipeline = (
                self.pipeline - nodes_requiring_other_executors
            ).from_nodes(
                *[
                    n.name
                    for n in ready_nodes
                    if n in (self.pipeline - nodes_requiring_other_executors).nodes
                ]
            )

            pipelines.append(executable_subpipeline)

        largest_subpipeline = max(pipelines, key=lambda x: len(x.nodes))

        self.todo_nodes = self.todo_nodes.difference(set(largest_subpipeline.nodes))
        self.done_nodes = self.done_nodes.union(set(largest_subpipeline.nodes))

        return largest_subpipeline.nodes  # Nodes property is sorted already.
