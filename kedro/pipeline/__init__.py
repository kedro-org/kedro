"""``kedro.pipeline`` provides functionality to define and execute
data-driven pipelines.
"""

from .node import node
from .pipeline import Pipeline, pipeline

__all__ = ["node", "pipeline", "Pipeline"]
