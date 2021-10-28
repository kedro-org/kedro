"""Full pipeline scheduler class definition.
"""
from typing import List

from kedro.pipeline.node import Node
from kedro.pipeline.pipeline import Pipeline
from kedro.symphony.scheduler.scheduler import AbstractScheduler


class FullPipelineScheduler(AbstractScheduler):
    """Scheduler for that iterates once and returns the entire pipeline.
    """
    def __init__(self, pipeline: Pipeline):
        """Constructor.

        Args:
            pipeline: Pipeline object to schedule the execution of.
        """
        super().__init__(pipeline)

        self.next_called = False

    def __next__(self) -> List[Node]:
        """Get all the nodes in the pipeline.

        Raises:
            StopIteration when we're done iterating.

        Returns:
            List of Nodes.
        """
        if self.next_called:
            raise StopIteration

        else:
            self.next_called = True
            return self.pipeline.nodes
