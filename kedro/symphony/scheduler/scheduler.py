"""``AbstractScheduler`` class definition.
"""

import abc
from typing import List

from kedro.pipeline import Pipeline
from kedro.pipeline.node import Node


class AbstractScheduler(abc.ABC):
    """Base scheduler class.

    Schedulers are just iterators that return a list of nodes to execute at
    each iteration.
    """

    def __init__(self, pipeline: Pipeline):
        """Constructor.

        Args:
            pipeline: Pipeline object to schedule the execution of.
        """
        self.pipeline = pipeline

    def __iter__(self):
        """Iter dunder method.

        Returns:
            self.
        """
        return self

    @abc.abstractmethod
    def __next__(self) -> List[Node]:
        """List of nodes that are next to be executed.

        Raises:
            StopIteration when we're done iterating.

        Returns:
            List of nodes.
        """
