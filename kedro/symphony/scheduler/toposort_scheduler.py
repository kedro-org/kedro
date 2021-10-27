"""Topologically sorted scheduler definition.
"""

from typing import List

from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node
from kedro.symphony.scheduler.scheduler import AbstractScheduler


class ToposortScheduler(AbstractScheduler):
    """The most basic schedule.

    Returns the nodes that are next in the topologically sorted order.
    """

    def __init__(self, pipeline: Pipeline):
        """Constructor.

        Args:
            pipeline: Pipeline object to schedule the execution of.
        """
        super().__init__(pipeline)

        self.node_dependencies = pipeline.node_dependencies
        self.todo_nodes = set(self.node_dependencies.keys())
        self.done_nodes = set()

    def __next__(self) -> List[Node]:
        """Get the next list of nodes in topological order.

        Raises:
            StopIteration when we're done iterating.

        Returns:
            List of Nodes.
        """
        if not self.todo_nodes:
            raise StopIteration

        ready = {
            n for n in self.todo_nodes if self.node_dependencies[n] <= self.done_nodes
        }

        self.todo_nodes = self.todo_nodes.difference(ready)
        self.done_nodes = self.done_nodes.union(ready)

        return list(ready)
