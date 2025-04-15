"""``kedro.pipeline`` provides functionality to define and execute
data-driven pipelines.
"""

from .node import Node, node
from .pipeline import Pipeline, pipeline

__all__ = ["node", "pipeline", "Node", "Pipeline"]
