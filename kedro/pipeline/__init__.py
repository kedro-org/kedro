"""``kedro.pipeline`` provides functionality to define and execute
data-driven pipelines.
"""

from .node import node
from .pipeline import GroupedNode, Pipeline, pipeline

__all__ = ["node", "pipeline", "Pipeline", "GroupedNode"]
